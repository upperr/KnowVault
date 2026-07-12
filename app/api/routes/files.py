"""
文件管理相关 API 路由
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict
from pathlib import Path
from app.core.knowledge_base import get_knowledge_base
from app.parser.batch_processor import BatchProcessor, parse_file
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_files(file: UploadFile = File(..., description="上传的文件")):
    """
    上传并解析文件（仅解析，不切片和向量化）
    用于文档优化功能
    
    支持格式：
    - PDF (.pdf)
    - Word (.doc, .docx)
    - Markdown (.md)
    - 文本 (.txt)
    
    处理流程：
    1. 使用 MinerU 解析文档
    2. 返回解析后的 Markdown 内容
    
    注意：此接口不会将文档添加到知识库
    """
    processor = BatchProcessor()
    
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        # 解析文档
        logger.info(f"开始解析文件：{file.filename}")
        result = processor.parse_file(tmp_path)
        md_content = result.get('full_text', '')
        
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        logger.info(f"解析完成，内容长度：{len(md_content)}")
        
        return {
            "status": "success",
            "file_name": file.filename,
            "content": md_content,
            "message": f"已解析 {file.filename}"
        }
        
    except Exception as e:
        logger.error(f"解析失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解析失败：{str(e)}")


@router.post("/export/docx")
async def export_to_docx(request: dict):
    """
    将内容导出为 Word 文档
    
    Args:
        content: Markdown 或纯文本内容
        title: 文档标题
        format: 内容格式 (markdown/text)
    """
    from app.core.doc_generation import markdown_to_docx, create_docx_from_text
    from fastapi.responses import Response
    from urllib.parse import quote
    
    content = request.get("content", "")
    title = request.get("title", "文档")
    format_type = request.get("format", "markdown")
    
    if format_type == "markdown":
        docx_bytes = markdown_to_docx(content, title)
    else:
        docx_bytes = create_docx_from_text(content, title)
    
    # 文件名 URL 编码，支持中文
    encoded_filename = quote(f"{title}.docx")
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )


def _is_hidden_or_temp_file(file_path: Path) -> bool:
    """
    检查文件是否是隐藏文件或临时文件
    
    检测规则：
    1. 文件名以 . 开头（Unix 隐藏文件）
    2. 文件名以 ~$ 开头（Office 临时文件）
    3. 文件名以 ~ 结尾（备份文件）
    4. 文件在隐藏目录中（路径中包含 /. 目录）
    5. 文件名包含 .DS_Store（macOS 元数据文件）
    """
    # 检查文件名
    name = file_path.name
    if name.startswith(".") or name.startswith("~$") or name.endswith("~") or name == ".DS_Store":
        return True
    
    # 检查路径中是否包含隐藏目录
    for part in file_path.parts:
        if part.startswith(".") and part not in [".", ".."]:
            return True
    
    return False


@router.delete("/{file_name}")
async def delete_file(file_name: str):
    kb = get_knowledge_base()
    kb.delete_by_file_name(file_name)
    return {"status": "success"}


@router.get("/stats")
async def get_stats():
    kb = get_knowledge_base()
    return kb.get_stats()


@router.post("/clear")
async def clear_knowledge_base():
    kb = get_knowledge_base()
    kb.clear()
    return {"status": "success"}


@router.get("/documents")
async def get_documents():
    """获取文档列表"""
    kb = get_knowledge_base()
    files = kb.get_all_files()
    return {"file_list": [f["file_name"] for f in files]}


@router.get("/status")
async def get_status():
    """获取系统状态（知识库 + 记忆）"""
    kb = get_knowledge_base()
    kb_stats = kb.get_stats()
    
    # 记忆状态（如果可用）
    memory_stats = {}
    try:
        from app.memory.manager import MemoryManager
        memory_mgr = MemoryManager()
        memory_stats = memory_mgr.get_stats()
    except Exception:
        memory_stats = {"short_term": {"size": 0}, "long_term": {"total_entries": 0}}
    
    return {
        "knowledge_base": kb_stats,
        "memory": memory_stats
    }


@router.post("/sync")
async def sync_documents(request: dict):
    """同步文档目录（智能检测新增、修改、删除）"""
    import logging
    import hashlib
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    doc_dir = request.get("doc_dir", "data/documents")
    doc_path = Path(doc_dir)
    
    if not doc_path.exists():
        return {"status": "error", "message": f"文档目录不存在：{doc_dir}"}
    
    try:
        kb = get_knowledge_base()
        processor = BatchProcessor()
        
        # 1. 扫描目录获取文件列表（包含修改时间）
        current_files = {}  # {file_name: {"file_path": str, "mtime": float, "size": int}}
        for file_path in doc_path.rglob("*"):
            # 跳过隐藏文件和临时文件
            if not _is_hidden_or_temp_file(file_path):
                ext = file_path.suffix.lower()
                # 只处理支持的格式
                if ext in ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.md', '.csv']:
                    stat = file_path.stat()
                    current_files[file_path.name] = {
                        "file_path": str(file_path),
                        "mtime": stat.st_mtime,
                        "size": stat.st_size
                    }
        
        logger.info(f"扫描到 {len(current_files)} 个文件")
        
        # 2. 获取数据库中的文件列表
        db_files = {f["file_name"]: f for f in kb.get_all_files()}
        logger.info(f"数据库中有 {len(db_files)} 个文件")
        
        # 3. 对比检测
        to_add = []      # 新增文件
        to_update = []   # 修改文件
        to_delete = []   # 删除文件
        
        for file_name, file_info in current_files.items():
            if file_name not in db_files:
                to_add.append(file_name)
            else:
                # 简单判断：如果文件名存在，就更新（可以改进为对比修改时间或内容哈希）
                to_update.append(file_name)
        
        for file_name in db_files:
            if file_name not in current_files:
                to_delete.append(file_name)
        
        logger.info(f"新增：{len(to_add)}, 更新：{len(to_update)}, 删除：{len(to_delete)}")
        
        # 4. 处理新增文件
        added_count = 0
        added_chunks = 0
        for file_name in to_add:
            file_path = current_files[file_name]["file_path"]
            logger.info(f"[新增] {file_name}")
            try:
                result = processor.parse_file(file_path)
                content = result.get("full_text", "")
                if content.strip():
                    # 使用分块功能（参数从 config 读取）
                    from app.parser.chunker import chunk_document
                    chunks = chunk_document(content, file_name)
                    
                    # 批量生成 embedding
                    chunk_texts = [chunk["content"] for chunk in chunks]
                    embeddings = kb._get_embedding_batch(chunk_texts)
                    
                    for i, chunk in enumerate(chunks):
                        doc_id = f"{file_name}_{chunk['chunk_index']}_{len(chunk['content'])}"
                        kb.add_document(
                            doc_id=doc_id,
                            content=chunk["content"],
                            metadata={
                                "file_name": file_name,
                                "file_path": file_path,
                                "chunk_index": chunk["chunk_index"],
                                "total_chunks": chunk["total_chunks"]
                            },
                            embedding=embeddings[i] if i < len(embeddings) and embeddings[i] is not None else None
                        )
                    
                    added_count += 1
                    added_chunks += len(chunks)
                    logger.info(f"[新增完成] {file_name}: {len(chunks)} 个 chunks")
            except Exception as e:
                logger.error(f"[新增失败] {file_name}: {e}")
        
        # 5. 处理更新文件（先删除再添加）
        updated_count = 0
        updated_chunks = 0
        for file_name in to_update:
            file_path = current_files[file_name]["file_path"]
            logger.info(f"[更新] {file_name}")
            try:
                # 先删除旧数据
                kb.delete_by_file_name(file_name)
                
                # 再添加新数据
                result = processor.parse_file(file_path)
                content = result.get("full_text", "")
                if content.strip():
                    # 使用分块功能（参数从 config 读取）
                    from app.parser.chunker import chunk_document
                    chunks = chunk_document(content, file_name)
                    
                    # 批量生成 embedding
                    chunk_texts = [chunk["content"] for chunk in chunks]
                    embeddings = kb._get_embedding_batch(chunk_texts)
                    
                    for i, chunk in enumerate(chunks):
                        doc_id = f"{file_name}_{chunk['chunk_index']}_{len(chunk['content'])}"
                        kb.add_document(
                            doc_id=doc_id,
                            content=chunk["content"],
                            metadata={
                                "file_name": file_name,
                                "file_path": file_path,
                                "chunk_index": chunk["chunk_index"],
                                "total_chunks": chunk["total_chunks"]
                            },
                            embedding=embeddings[i] if i < len(embeddings) and embeddings[i] is not None else None
                        )
                    
                    updated_count += 1
                    updated_chunks += len(chunks)
                    logger.info(f"[更新完成] {file_name}: {len(chunks)} 个 chunks")
            except Exception as e:
                logger.error(f"[更新失败] {file_name}: {e}")
        
        # 6. 处理删除文件
        deleted_count = 0
        for file_name in to_delete:
            logger.info(f"[删除] {file_name}")
            try:
                kb.delete_by_file_name(file_name)
                deleted_count += 1
            except Exception as e:
                logger.error(f"[删除失败] {file_name}: {e}")
        
        return {
            "status": "ok",
            "sync_result": {
                "added": added_count,
                "updated": updated_count,
                "deleted": deleted_count,
                "unchanged": len(current_files) - len(to_add) - len(to_update),
                "added_chunks": added_chunks,
                "updated_chunks": updated_chunks
            },
            "summary": f"新增 {added_count} 文档 ({added_chunks} chunks) | 更新 {updated_count} 文档 ({updated_chunks} chunks) | 删除 {deleted_count} 文档"
        }
        
    except Exception as e:
        logger.error(f"同步失败：{e}")
        return {"status": "error", "message": str(e)}
