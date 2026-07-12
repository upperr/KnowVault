"""
Parser 模块配置
定义文档解析相关的配置常量
"""

# MinerU 限制配置
MAX_FILE_SIZE_MB = 200  # 最大文件大小（MB）
MAX_PAGES = 200         # 最大页数

# 支持的文件格式
SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
    ".txt": "txt",
    ".md": "txt",
    ".csv": "txt",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
}
