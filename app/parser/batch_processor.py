"""
批量处理模块
使用 MinerU 批量 API 处理多个文档
自动处理 MinerU 不支持的格式（txt、md、csv 等）

超长文档处理流程：
1. 检测文档是否超限（大小/页数）
2. 超限文档分割到 data/data/output/split_files/ 目录
3. 对每个子文档进行 MinerU 批量 API 解析
4. 解析完成后删除子文档
5. 保留原始文件和解析后的 MD 文件
"""
import logging
from pathlib import Path
from typing import List, Dict

from app.parser.config import SUPPORTED_EXTENSIONS
from app.parser.detector import needs_split
from app.parser.splitter import split_file, cleanup_sub_files
from app.parser.mineru_client import MinerUClient, SUPPORTED_EXTENSIONS as MINERU_SUPPORTED_EXTENSIONS
from app.parser.content_extractor import ContentExtractor
from app.parser.local_parsers import (
    parse_pdf_basic, parse_docx, parse_pptx, parse_xlsx, parse_txt
)

logger = logging.getLogger(__name__)

# MinerU 不支持但需要导入知识库的格式（纯文本格式）
PLAINTEXT_EXTENSIONS = {'.txt', '.md', '.csv', '.rst', '.json', '.xml', '.yaml', '.yml'}


class BatchProcessor:
    """批量文档处理器（仅使用批量 API）"""
    
    # 调试配置：是否导出 MD 文件
    EXPORT_MD_FOR_DEBUG = True
    MD_OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "output" / "md"
    
    def __init__(self, export_md: bool = None):
        """
        初始化批量处理器
        
        Args:
            export_md: 是否导出 MD 文件用于调试（默认使用 EXPORT_MD_FOR_DEBUG 配置）
        """
        self.mineru_client = MinerUClient()
        self.content_extractor = ContentExtractor()
        self.export_md = export_md if export_md is not None else self.EXPORT_MD_FOR_DEBUG
        
        # 创建 MD 输出目录
        if self.export_md:
            self.MD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def parse_file(self, file_path: str) -> Dict:
        """
        解析单个文件（自动检测并分割大文件）
        
        Args:
            file_path: 文件路径
        
        Returns:
            解析结果字典
        """
        ext = Path(file_path).suffix.lower()
        file_type = SUPPORTED_EXTENSIONS.get(ext)
        
        # 纯文本格式，直接解析
        if ext in PLAINTEXT_EXTENSIONS:
            return parse_txt(file_path)
        
        # 检查是否需要分割（仅 PDF 和 DOCX）
        if file_type in ["pdf", "docx"] and needs_split(file_path):
            logger.info(f"文件超限，开始分割：{file_path}")
            return self._parse_split_file(file_path, file_type)
        
        # 不需要分割，使用批量 API 解析
        return self._parse_with_mineru(file_path, file_type)
    
    def _parse_split_file(self, file_path: str, file_type: str) -> Dict:
        """
        解析需要分割的文件
        
        流程：
        1. 分割文件到 data/output/split_files/ 目录
        2. 对每个子文件进行 MinerU 解析
        3. 合并所有子文件的解析结果
        4. 删除子文件
        5. 保留原始文件
        """
        # 1. 分割文件
        sub_files = split_file(file_path)
        
        if not sub_files:
            logger.error(f"文件分割失败：{file_path}")
            return self._parse_with_mineru(file_path, file_type)
        
        logger.info(f"分割完成：共{len(sub_files)}个子文件")
        logger.info(f"子文件列表：{sub_files}")
        
        try:
            # 2. 对每个子文件进行 MinerU 解析
            all_text_blocks = []
            all_images = []
            all_tables = []
            
            for idx, sub_file in enumerate(sub_files, 1):
                logger.info(f"[{idx}/{len(sub_files)}] 正在解析子文件：{Path(sub_file).name}")
                
                # 使用批量 API 解析子文件
                result = self._parse_with_mineru(sub_file, file_type)
                
                all_text_blocks.extend(result["text_blocks"])
                all_images.extend(result["images"])
                all_tables.extend(result["tables"])
                
                logger.info(f"[{idx}/{len(sub_files)}] 子文件解析完成")
            
            # 3. 合并结果
            full_text = self.content_extractor._merge_content(
                all_text_blocks, all_images, all_tables
            )
            
            logger.info(f"分割解析完成：共{len(all_text_blocks)}个文本块")
            
            result = {
                "text_blocks": all_text_blocks,
                "images": all_images,
                "tables": all_tables,
                "full_text": full_text
            }
            
            # 4. 删除子文件（保留原始文件）
            logger.info("开始清理子文件...")
            cleanup_sub_files(sub_files)
            logger.info(f"子文件已清理，原始文件保留：{file_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"分割解析失败：{e}")
            # 清理剩余子文件
            cleanup_sub_files(sub_files)
            raise
    
    def _parse_with_mineru(self, file_path: str, file_type: str) -> Dict:
        """使用 MinerU 批量 API 解析文件"""
        # 单个文件也使用批量 API 处理
        results = self.mineru_client.parse_files_batch(
            file_paths=[file_path],
            wait_complete=True,
            poll_interval=30,
            is_ocr=False,
            max_batch_size=50
        )
        
        if file_path in results and results[file_path]:
            md_content = results[file_path]
            
            # 导出 MD 文件用于调试
            if self.export_md:
                self._export_md_file(file_path, md_content)
            
            return {
                "text_blocks": [{"content": md_content, "page": 0}],
                "images": [],
                "tables": [],
                "full_text": md_content
            }
        else:
            # API 调用失败，回退到本地解析
            logger.info(f"MinerU API 解析失败，使用本地解析器：{file_path}")
            if file_type == "pdf":
                return parse_pdf_basic(file_path)
            elif file_type == "docx":
                return parse_docx(file_path)
            elif file_type == "pptx":
                return parse_pptx(file_path)
            elif file_type == "xlsx":
                return parse_xlsx(file_path)
            else:
                return {"text_blocks": [], "images": [], "tables": [], "full_text": ""}
    
    def _export_md_file(self, file_path: str, md_content: str):
        """
        导出 MD 文件用于调试
        
        Args:
            file_path: 原始文件路径
            md_content: Markdown 内容
        """
        try:
            # 生成输出文件名
            original_name = Path(file_path).stem
            output_filename = f"{original_name}.md"
            output_path = self.MD_OUTPUT_DIR / output_filename
            
            # 写入 MD 文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"MD 文件已导出：{output_path} ({len(md_content)} 字符)")
            
        except Exception as e:
            logger.warning(f"导出 MD 文件失败：{e}")
    
    def extract_all_documents(self, doc_dir: str) -> List[Dict]:
        """
        批量解析目录下所有文档
        
        处理流程：
        1. 扫描目录下所有文件
        2. 按格式分类（MinerU 支持格式 / 纯文本格式）
        3. 对 MinerU 支持格式检测是否需要分割
        4. 超限文件单独分割处理
        5. 普通文件批量 API 处理
        6. 纯文本格式直接读取
        
        Args:
            doc_dir: 文档目录路径
        
        Returns:
            文档列表：[{"file_name": str, "file_path": str, "content": str}, ...]
        """
        doc_path = Path(doc_dir)
        
        if not doc_path.exists():
            logger.warning(f"文档目录不存在：{doc_dir}")
            return []
        
        # 收集所有支持的文件
        mineru_files = []  # MinerU 支持的格式
        split_files = []   # 需要分割的文件
        plaintext_files = []  # MinerU 不支持的纯文本格式
        
        for file_path in doc_path.rglob("*"):
            # 跳过隐藏文件和临时文件
            if file_path.name.startswith(".") or file_path.name.startswith("~$"):
                logger.debug(f"跳过临时/隐藏文件：{file_path.name}")
                continue
            
            if file_path.is_file():
                ext = file_path.suffix.lower()
                
                if ext in PLAINTEXT_EXTENSIONS:
                    plaintext_files.append(file_path)
                elif ext in MINERU_SUPPORTED_EXTENSIONS:
                    # 检查是否需要分割（仅 PDF 和 DOCX）
                    try:
                        if ext in [".pdf", ".docx", ".doc"] and needs_split(str(file_path)):
                            split_files.append(file_path)
                        else:
                            mineru_files.append(file_path)
                    except Exception as e:
                        logger.warning(f"文件检测失败 {file_path.name}: {e}，跳过此文件")
                        continue
        
        if not mineru_files and not split_files and not plaintext_files:
            logger.warning(f"文档目录中未找到支持的文件：{doc_dir}")
            return []
        
        logger.info(f"找到 {len(mineru_files)} 个普通文件，{len(split_files)} 个超限文件，{len(plaintext_files)} 个纯文本文件")
        
        documents = []
        
        # 1. 处理超限文件（先分割再解析）
        if split_files:
            logger.info(f"开始解析 {len(split_files)} 个超限文件（需要分割）...")
            for file_path in split_files:
                logger.info(f"处理超限文件：{file_path.name}")
                try:
                    file_type = SUPPORTED_EXTENSIONS.get(file_path.suffix.lower())
                    result = self._parse_split_file(str(file_path), file_type)
                    content = result.get("full_text", "")
                    
                    if content.strip():
                        documents.append({
                            "file_name": file_path.name,
                            "file_path": str(file_path),
                            "content": content,
                        })
                        logger.info(f"超限文件解析完成：{file_path.name} ({len(content)} 字符)")
                except Exception as e:
                    logger.error(f"超限文件解析失败 {file_path.name}: {e}")
        
        # 2. 处理普通 MinerU 支持格式（批量 API）
        if mineru_files:
            logger.info(f"开始解析 {len(mineru_files)} 个普通文件（MinerU 批量 API）...")
            documents.extend(self._extract_with_mineru_batch(mineru_files))
        
        # 3. 处理纯文本格式（直接读取）
        if plaintext_files:
            logger.info(f"开始解析 {len(plaintext_files)} 个纯文本文件...")
            documents.extend(self._extract_plaintext_files(plaintext_files))
        
        logger.info(
            f"批量解析完成：成功 {len(documents)}/{len(mineru_files) + len(split_files) + len(plaintext_files)} 个文档"
        )
        
        return documents
    
    def _extract_with_mineru_batch(self, mineru_files: List[Path]) -> List[Dict]:
        """使用 MinerU 批量 API 解析文件"""
        file_paths = [str(f) for f in mineru_files]
        
        # 调用批量解析
        results = self.mineru_client.parse_files_batch(
            file_paths=file_paths,
            wait_complete=True,
            poll_interval=30,
            is_ocr=False,
            max_batch_size=50
        )
        
        documents = []
        for file_path, md_content in results.items():
            if md_content and md_content.strip():
                documents.append({
                    "file_name": Path(file_path).name,
                    "file_path": file_path,
                    "content": md_content,
                })
                logger.info(f"解析完成：{Path(file_path).name} ({len(md_content)} 字符)")
                
                # 导出 MD 文件用于调试
                if self.export_md:
                    self._export_md_file(file_path, md_content)
            else:
                logger.warning(f"解析内容为空：{file_path}")
        
        return documents
    
    def _extract_plaintext_files(self, plaintext_files: List[Path]) -> List[Dict]:
        """解析纯文本文件（txt、md、csv 等）"""
        documents = []
        
        for idx, file_path in enumerate(plaintext_files, 1):
            logger.info(f"[{idx}/{len(plaintext_files)}] 正在解析：{file_path.name}")
            
            try:
                result = parse_txt(str(file_path))
                content = result.get("full_text", "")
                
                if content.strip():
                    documents.append({
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "content": content,
                    })
                    logger.info(
                        f"[{idx}/{len(plaintext_files)}] 解析完成："
                        f"{file_path.name} ({len(content)} 字符)"
                    )
                else:
                    logger.warning(
                        f"[{idx}/{len(plaintext_files)}] 解析内容为空："
                        f"{file_path.name}"
                    )
                    
            except Exception as e:
                logger.error(
                    f"[{idx}/{len(plaintext_files)}] 解析失败 "
                    f"{file_path.name}: {e}"
                )
        
        return documents


# 全局处理器实例
_processor = None


def _get_processor() -> BatchProcessor:
    """获取全局处理器实例"""
    global _processor
    if _processor is None:
        _processor = BatchProcessor()
    return _processor


def parse_file(file_path: str) -> Dict:
    """便捷函数：解析单个文件"""
    return _get_processor().parse_file(file_path)


def extract_all_documents(doc_dir: str) -> List[Dict]:
    """便捷函数：批量解析目录"""
    return _get_processor().extract_all_documents(doc_dir)
