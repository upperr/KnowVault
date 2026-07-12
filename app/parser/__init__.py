"""
Parser 模块 - 文档解析功能

功能：
1. 文档检测：检测文件大小和页数
2. 文档分割：超限文件自动分割到 output/split_files/
3. MinerU 批量 API 调用：仅支持批量上传方式
4. 纯文本解析：txt、md、csv 等格式直接解析
5. 内容提取：从 API 结果提取文本、图片、表格
6. 子文件清理：解析完成后删除临时子文件

超长文档处理流程：
    原始文件 -> 分割 -> output/split_files/ -> 解析 -> 删除子文件 -> 保留原文件和 MD

使用示例：
    from app.parser import parse_file, extract_all_documents
    
    # 解析单个文件（超限自动分割）
    result = parse_file("/path/to/document.pdf")
    
    # 批量解析目录（混合格式：PDF + txt + md）
    documents = extract_all_documents("/path/to/documents")
"""

from app.parser.batch_processor import parse_file, extract_all_documents, BatchProcessor, PLAINTEXT_EXTENSIONS
from app.parser.config import (
    MAX_FILE_SIZE_MB,
    MAX_PAGES,
    SUPPORTED_EXTENSIONS,
)
from app.parser.detector import (
    get_file_size_mb,
    get_pdf_page_count,
    get_docx_page_count,
    needs_split,
)
from app.parser.splitter import (
    split_pdf,
    split_docx,
    split_file,
    delete_file,
    cleanup_sub_files,
    get_output_dir,
    clear_output_dir,
)
from app.parser.mineru_client import MinerUClient, SUPPORTED_EXTENSIONS as MINERU_SUPPORTED_EXTENSIONS
from app.parser.content_extractor import ContentExtractor
from app.parser.local_parsers import (
    parse_pdf_basic,
    parse_docx,
    parse_pptx,
    parse_xlsx,
    parse_txt,
)

__all__ = [
    # 配置
    "MAX_FILE_SIZE_MB",
    "MAX_PAGES",
    "SUPPORTED_EXTENSIONS",
    "MINERU_SUPPORTED_EXTENSIONS",
    "PLAINTEXT_EXTENSIONS",
    
    # 检测
    "get_file_size_mb",
    "get_pdf_page_count",
    "get_docx_page_count",
    "needs_split",
    
    # 分割
    "split_pdf",
    "split_docx",
    "split_file",
    "delete_file",
    "cleanup_sub_files",
    "get_output_dir",
    "clear_output_dir",
    
    # 客户端
    "MinerUClient",
    "ContentExtractor",
    "BatchProcessor",
    
    # 本地解析器
    "parse_pdf_basic",
    "parse_docx",
    "parse_pptx",
    "parse_xlsx",
    "parse_txt",
    
    # 公共接口
    "parse_file",
    "extract_all_documents",
]
