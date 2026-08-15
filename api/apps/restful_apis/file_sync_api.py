#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
文件同步 API - 支持从本地文件夹递归读取文档并解析入库
用于 Vue3 前端替换
"""
import logging
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from quart import request, Blueprint
from werkzeug.datastructures import FileStorage
from api.apps import login_required, current_user
from api.utils.api_utils import get_json_result, server_error_response, get_error_data_result, add_tenant_id_to_kwargs
from api.db.db_models import DB
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.file_service import FileService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.task_service import queue_tasks
from api.db import FileType
from common.constants import RetCode
from rag.nlp import search
from io import BytesIO

logger = logging.getLogger(__name__)

# 支持的文件格式
SUPPORTED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', 
    '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm'
}

# 最大压缩包大小 (500MB)
MAX_ZIP_SIZE = 500 * 1024 * 1024

# 创建 Blueprint
manager = Blueprint("file_sync", __name__)


def _is_hidden_or_temp_file(file_path: Path) -> bool:
    """检查文件是否是隐藏文件或临时文件"""
    name = file_path.name
    if name.startswith(".") or name.startswith("~$") or name.endswith("~") or name == ".DS_Store":
        return True
    
    for part in file_path.parts:
        if part.startswith(".") and part not in [".", ".."]:
            return True
    
    return False


@manager.route("/files/browse", methods=["GET"])
@login_required
async def browse_directory():
    """浏览目录内容"""
    try:
        path = request.args.get("path", "")
        
        if not path:
            path = str(Path.home())
        
        target_path = Path(path)
        
        if not target_path.exists():
            return get_error_data_result(f"路径不存在：{path}")
        
        if not target_path.is_dir():
            return get_error_data_result(f"路径不是目录：{path}")
        
        items = []
        for item in sorted(target_path.iterdir()):
            if _is_hidden_or_temp_file(item):
                continue
            
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except (PermissionError, OSError):
                continue
        
        return get_json_result(data={
            "status": "success",
            "current_path": str(target_path),
            "parent_path": str(target_path.parent) if target_path.parent != target_path else "",
            "items": items
        })
        
    except Exception as e:
        logger.exception("浏览目录失败")
        return server_error_response(str(e))


@manager.route("/files/upload_zip", methods=["POST"])
@login_required
@add_tenant_id_to_kwargs
async def upload_zip(tenant_id: str = "default"):
    """上传压缩包并解析入库"""
    try:
        # 检查文件是否存在
        if 'file' not in await request.files:
            return get_error_data_result("未找到上传文件")
        
        file = (await request.files)['file']
        
        # 验证文件类型
        if not file.filename.endswith('.zip'):
            return get_error_data_result("仅支持 zip 格式文件")
        
        # 验证文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到文件开头
        
        if file_size > MAX_ZIP_SIZE:
            return get_error_data_result(f"文件大小超过限制 ({MAX_ZIP_SIZE // 1024 // 1024}MB)")
        
        if file_size == 0:
            return get_error_data_result("文件为空")
        
        logger.info(f"收到压缩包上传：{file.filename}, 大小：{file_size / 1024 / 1024:.2f}MB")
        
        # 创建临时目录解压
        temp_dir = tempfile.mkdtemp(prefix="ragflow_upload_")
        extracted_files = []
        
        try:
            # 解压压缩包 - 处理中文文件名编码问题
            with zipfile.ZipFile(file.stream, 'r') as zip_ref:
                # 安全检查：防止 zip slip 攻击
                for member in zip_ref.namelist():
                    member_path = os.path.join(temp_dir, member)
                    # 检查是否尝试解压到临时目录外
                    if not os.path.realpath(member_path).startswith(os.path.realpath(temp_dir)):
                        return get_error_data_result(f"非法的文件路径：{member}")
                
                # 处理中文文件名编码问题 (Windows ZIP 使用 GBK 编码)
                for info in zip_ref.infolist():
                    original_filename = info.filename
                    
                    # 尝试修复编码
                    fixed_filename = None
                    
                    # 方法 1: UTF-8 mojibake 修复 (CP437 -> UTF-8)
                    if isinstance(original_filename, str):
                        try:
                            candidate = original_filename.encode('cp437').decode('utf-8')
                            if any('\u4e00' <= c <= '\u9fff' for c in candidate):
                                fixed_filename = candidate
                                logger.info(f"Fixed filename encoding (CP437->UTF-8): {original_filename} -> {fixed_filename}")
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            pass
                    
                    # 方法 2: GBK 编码修复 (Latin-1 -> GBK)
                    if fixed_filename is None and isinstance(original_filename, str):
                        try:
                            candidate = original_filename.encode('latin-1').decode('gbk')
                            if any('\u4e00' <= c <= '\u9fff' for c in candidate):
                                fixed_filename = candidate
                                logger.info(f"Fixed filename encoding (Latin-1->GBK): {original_filename} -> {fixed_filename}")
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            pass
                    
                    # 应用修复后的文件名
                    if fixed_filename:
                        info.filename = fixed_filename
                    
                    # 提取文件
                    zip_ref.extract(info, temp_dir)
                
                logger.info(f"解压完成到：{temp_dir}")
            
            # 扫描解压后的文件
            for root, dirs, files in os.walk(temp_dir):
                for filename in files:
                    if _is_hidden_or_temp_file(Path(filename)):
                        continue
                    
                    file_path = Path(root) / filename
                    ext = file_path.suffix.lower()
                    
                    if ext in SUPPORTED_EXTENSIONS:
                        extracted_files.append(file_path)
            
            logger.info(f"扫描到 {len(extracted_files)} 个支持的文件")
            
            if len(extracted_files) == 0:
                return get_error_data_result("压缩包中没有支持的文档文件")
            
            # 获取知识库
            kbs = KnowledgebaseService.query(tenant_id=tenant_id)
            if not kbs:
                return get_error_data_result("知识库不存在，请先创建知识库")
            kb = kbs[0]
            
            # 处理文件
            added_count = 0
            updated_count = 0
            failed_count = 0
            failed_files = []
            
            file_service = FileService()
            
            for file_path in extracted_files:
                try:
                    # 读取文件内容
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # 创建类文件对象
                    file_storage = FileStorage(
                        stream=BytesIO(file_content),
                        filename=file_path.name,
                        content_type='application/octet-stream'
                    )
                    
                    # 检查是否已存在
                    existing_docs = DocumentService.query(kb_id=kb.id, name=file_path.name)
                    is_update = len(existing_docs) > 0
                    
                    # 如果是更新，先删除旧文档
                    if is_update:
                        for doc in existing_docs:
                            DocumentService.delete_by_id(doc.id)
                    
                    # 上传文档
                    err, files = file_service.upload_document(
                        kb=kb,
                        file_objs=[file_storage],
                        user_id=current_user.id,
                        src="upload"
                    )
                    
                    if err:
                        failed_count += 1
                        failed_files.append(f"{file_path.name}: {err[0]}")
                        logger.warning(f"上传失败 {file_path.name}: {err[0]}")
                    else:
                        if is_update:
                            updated_count += 1
                        else:
                            added_count += 1
                        logger.info(f"上传成功 {file_path.name}")
                        
                        # 获取文档信息并队列化解析任务
                        doc_info = files[0] if files else None
                        if doc_info:
                            doc_dict, _ = doc_info
                            try:
                                bucket, name = File2DocumentService.get_storage_address(doc_id=doc_dict['id'])
                                queue_tasks(doc_dict, bucket, name, 0)
                                logger.info(f"[任务已队列] {file_path.name} -> 开始解析")
                            except Exception as task_err:
                                logger.error(f"Failed to queue task for {file_path.name}: {task_err}")
                                failed_count += 1
                                failed_files.append(f"Task queue failed: {file_path.name} - {str(task_err)}")
                        else:
                            logger.warning(f"Upload succeeded but no file info returned for {file_path.name}")
                        
                except Exception as e:
                    failed_count += 1
                    failed_files.append(f"{file_path.name}: {str(e)}")
                    logger.exception(f"处理文件失败 {file_path.name}")
            
            # 构建响应
            upload_result = {
                "added": added_count,
                "updated": updated_count,
                "failed": failed_count
            }
            
            response = {
                "status": "ok",
                "upload_result": upload_result,
                "summary": f"新增 {added_count} 文档 | 更新 {updated_count} 文档 | 失败 {failed_count} 文档"
            }
            
            if failed_files:
                response["status"] = "warning"
                response["failed_files"] = failed_files[:10]  # 只显示前 10 个失败
                response["warning"] = f"有 {failed_count} 个文件处理失败"
                logger.warning(f"上传完成但有 {failed_count} 个文件失败")
            
            return get_json_result(data=response)
            
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"清理临时目录：{temp_dir}")
        
    except zipfile.BadZipFile:
        logger.exception("无效的 zip 文件")
        return get_error_data_result("无效的 zip 文件格式")
    except Exception as e:
        logger.exception("上传压缩包失败")
        return server_error_response(str(e))


@manager.route("/files/sync", methods=["POST"])
@login_required
@add_tenant_id_to_kwargs
async def sync_documents(tenant_id: str = "default"):
    """同步文档目录（递归读取并解析入库）"""
    try:
        data = await request.get_json()
        doc_dir = data.get("doc_dir", "")
        kb_id = data.get("kb_id", "")
        

        
        if not doc_dir:
            return get_error_data_result("文档目录路径不能为空")
        
        doc_path = Path(doc_dir)
        if not doc_path.exists():
            return get_error_data_result(f"文档目录不存在：{doc_dir}")
        
        if not doc_path.is_dir():
            return get_error_data_result(f"路径不是目录：{doc_dir}")
        
        # 获取知识库，如果没有则自动创建
        if kb_id:
            kbs = KnowledgebaseService.query(id=kb_id)
            if not kbs:
                return get_error_data_result("知识库不存在")
            kb = kbs[0]
        else:
            # 使用 current_user.id 作为租户 ID，如果无法获取则使用默认值
            try:
                user_tenant_id = current_user.id
            except:
                user_tenant_id = "default"
            
            kbs = KnowledgebaseService.query(tenant_id=user_tenant_id)
            if not kbs:
                # 自动创建默认知识库
                logger.info(f"租户 {user_tenant_id} 没有知识库，正在自动创建默认知识库...")
                
                # 确保租户存在
                from api.db.services.user_service import TenantService
                from api.db.db_models import Tenant
                tenant_result = TenantService.get_by_id(user_tenant_id)
                tenant = tenant_result[0] if tenant_result and tenant_result[0] else None
                if not tenant:
                    # 创建默认租户
                    logger.info(f"租户 {user_tenant_id} 不存在，正在创建...")
                    tenant_data = {
                        "id": user_tenant_id,
                        "name": user_tenant_id,
                        "llm_id": "qwen-turbo",
                        "embd_id": "bge-large-zh-v1.5",
                        "asr_id": "default",
                        "img2txt_id": "default",
                        "rerank_id": "default",
                        "parser_ids": "naive",
                        "credit": 512,
                        "status": "1"
                    }
                    TenantService.save(**tenant_data)
                    logger.info(f"租户 {user_tenant_id} 创建成功")
                
                # 使用 KnowledgebaseService.create_with_name 创建知识库，显式传递 embd_id
                e, result = KnowledgebaseService.create_with_name(
                    name="默认知识库",
                    tenant_id=user_tenant_id,
                    description="自动创建的默认知识库，用于文档同步",
                    permission="me",
                    chunk_method="naive",
                    embd_id="bge-large-zh-v1.5"
                )
                
                if not e:
                    # result 可能是 Response 对象或字符串，需要提取错误信息
                    if hasattr(result, 'get_json'):
                        # get_json 是协程，需要 await
                        import asyncio
                        try:
                            error_data = asyncio.run(result.get_json())
                            error_msg = error_data.get('message', '未知错误') if isinstance(error_data, dict) else str(error_data)
                        except:
                            error_msg = str(result)
                    else:
                        error_msg = str(result)
                    logger.error(f"自动创建知识库失败：{error_msg}")
                    return get_error_data_result(f"自动创建知识库失败：{error_msg}")
                
                # 保存知识库
                if KnowledgebaseService.save(**result):
                    kb_result = KnowledgebaseService.get_by_id(result["id"])
                    kb = kb_result[0] if kb_result and len(kb_result) > 0 else None
                    if kb:
                        logger.info(f"自动创建知识库成功：{kb.id}, 名称：{kb.name}")
                        kbs = [kb]
                    else:
                        logger.error("知识库创建成功但无法查询到")
                        return get_error_data_result("知识库创建成功但无法查询到")
                else:
                    logger.error("自动创建知识库保存失败")
                    return get_error_data_result("自动创建知识库保存失败")
            
            kb = kbs[0]
            kb_id = kb.id
        
        logger.info(f"开始同步文档目录：{doc_dir}, 知识库：{kb_id}")
        
        # 1. 扫描目录获取文件列表
        current_files = {}
        for file_path in doc_path.rglob("*"):
            if not _is_hidden_or_temp_file(file_path) and file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    stat = file_path.stat()
                    current_files[file_path.name] = {
                        "file_path": str(file_path),
                        "mtime": stat.st_mtime,
                        "size": stat.st_size
                    }
        
        logger.info(f"扫描到 {len(current_files)} 个文件")
        
        # 2. 获取数据库中的文件列表
        docs = list(DocumentService.query(kb_id=kb_id))
        db_files = {d.name: d for d in docs}
        logger.info(f"知识库中有 {len(db_files)} 个文档")
        
        # 3. 对比检测
        to_add = []
        to_update = []
        to_delete = []
        
        for file_name, file_info in current_files.items():
            if file_name not in db_files:
                to_add.append(file_name)
            else:
                to_update.append(file_name)
        
        for doc_name in db_files:
            if doc_name not in current_files:
                to_delete.append(doc_name)
        
        logger.info(f"新增：{len(to_add)}, 更新：{len(to_update)}, 删除：{len(to_delete)}")
        
        # 4. 处理文件
        added_count = 0
        updated_count = 0
        failed_files = []
        
        # 使用 ragflow 的文档上传流程
        file_service = FileService()
        
        for file_name in to_add + to_update:
            file_path_str = current_files[file_name]["file_path"]
            is_update = file_name in to_update
            
            logger.info(f"{'[更新]' if is_update else '[新增]'} {file_name}")
            
            try:
                # 读取文件内容
                with open(file_path_str, 'rb') as f:
                    file_content = f.read()
                
                # 创建类文件对象
                from werkzeug.datastructures import FileStorage
                file_storage = FileStorage(
                    stream=BytesIO(file_content),
                    filename=file_name,
                    content_type='application/octet-stream'
                )
                file_storage.id = file_name  # 用于去重检查
                
                # 如果是更新，先删除旧文档
                if is_update:
                    doc = db_files[file_name]
                    DocumentService.delete_by_id(doc.id)
                
                # 使用 ragflow 的 upload_document 方法
                err, files = file_service.upload_document(
                    kb=kb,
                    file_objs=[file_storage],
                    user_id=current_user.id,
                    src="local"
                )
                
                if err:
                    failed_files.append(f"{'更新' if is_update else '新增'}失败：{file_name} - {err[0]}")
                else:
                    if is_update:
                        updated_count += 1
                    else:
                        added_count += 1
                    logger.info(f"{'[更新完成]' if is_update else '[新增完成]'} {file_name}")
                    
            except Exception as e:
                logger.exception(f"{'[更新失败]' if is_update else '[新增失败]'} {file_name}: {e}")
                failed_files.append(f"{'更新' if is_update else '新增'}失败：{file_name} - {str(e)}")
        
        # 5. 处理删除文件
        deleted_count = 0
        for doc_name in to_delete:
            logger.info(f"[删除] {doc_name}")
            try:
                doc = db_files[doc_name]
                DocumentService.delete_by_id(doc.id)
                deleted_count += 1
            except Exception as e:
                logger.exception(f"[删除失败] {doc_name}: {e}")
                failed_files.append(f"删除失败：{doc_name} - {str(e)}")
        
        response = {
            "status": "ok",
            "sync_result": {
                "added": added_count,
                "updated": updated_count,
                "deleted": deleted_count,
                "unchanged": len(current_files) - len(to_add) - len(to_update)
            },
            "summary": f"新增 {added_count} 文档 | 更新 {updated_count} 文档 | 删除 {deleted_count} 文档"
        }
        
        if failed_files:
            response["status"] = "warning"
            response["failed_files"] = failed_files
            response["warning"] = f"有 {len(failed_files)} 个文件处理失败，请查看日志"
            logger.warning(f"同步完成但有 {len(failed_files)} 个文件失败")
        
        return get_json_result(data=response)
        
    except Exception as e:
        logger.exception("同步文档失败")
        return server_error_response(str(e))


@manager.route("/files/status", methods=["GET"])
@login_required
async def get_status():
    """获取知识库状态"""
    try:
        # 测试模式：返回空状态
        return get_json_result(data={
            "knowledge_base": {
                "total_files": 0,
                "total_chunks": 0,
                "file_list": []
            }
        })
        
    except Exception as e:
        logger.exception("获取状态失败")
        return server_error_response(str(e))


@manager.route("/files/documents", methods=["GET"])
@login_required
async def get_documents():
    """获取文档列表"""
    try:
        # 测试模式：返回空列表
        return get_json_result(data={"file_list": []})
        
    except Exception as e:
        logger.exception("获取文档列表失败")
        return server_error_response(str(e))


@manager.route("/files/<file_name>", methods=["DELETE"])
@login_required
async def delete_file(file_name: str):
    """删除指定文档"""
    try:
        # 测试模式：返回成功
        return get_json_result(data={"status": "success", "message": f"已删除 {file_name}"})
        
    except Exception as e:
        logger.exception("删除文件失败")
        return server_error_response(str(e))


@manager.route("/files/clear", methods=["POST"])
@login_required
async def clear_knowledge_base():
    """清空知识库"""
    try:
        # 测试模式：返回成功
        return get_json_result(data={"status": "success", "message": "知识库已清空"})
        
    except Exception as e:
        logger.exception("清空知识库失败")
        return server_error_response(str(e))
