"""
文档生成模块

提供完整的文档创作和优化功能：
- 内容生成（基于 LLM）
- Markdown 转 Word（带格式排版）
- 本地图片插入
- 字体和段落格式设置
"""
from app.core.doc_generation.content_generator import ContentGenerator, get_generator
from app.core.doc_generation.markdown_converter import markdown_to_docx
from app.core.doc_generation.text_converter import create_docx_from_text
from app.core.doc_generation.config import (
    FONT_CHINESE_BODY,
    FONT_CHINESE_HEADING,
    FONT_ENGLISH,
    FONT_SIZE_BODY,
    FONT_SIZE_HEADING_1,
    FONT_SIZE_HEADING_2,
    FONT_SIZE_HEADING_3,
    FONT_SIZE_CAPTION,
    LINE_SPACING,
    SPACE_BEFORE,
    FIRST_LINE_INDENT,
    COLOR_BLACK,
)

__all__ = [
    # 生成器
    'ContentGenerator',
    'get_generator',
    
    # 格式转换
    'markdown_to_docx',
    'create_docx_from_text',
    
    # 配置常量
    'FONT_CHINESE_BODY',
    'FONT_CHINESE_HEADING',
    'FONT_ENGLISH',
    'FONT_SIZE_BODY',
    'FONT_SIZE_HEADING_1',
    'FONT_SIZE_HEADING_2',
    'FONT_SIZE_HEADING_3',
    'FONT_SIZE_CAPTION',
    'LINE_SPACING',
    'SPACE_BEFORE',
    'FIRST_LINE_INDENT',
    'COLOR_BLACK',
]
