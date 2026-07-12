"""
文本到 Word 转换器

将纯文本转换为 Word 文档
"""
import io
from docx import Document

from .config import FONT_CHINESE_BODY, FONT_CHINESE_HEADING, FONT_SIZE_BODY, FONT_SIZE_HEADING_1
from .formatter import setup_document_style, add_formatted_heading, add_formatted_paragraph


def create_docx_from_text(text_content: str, title: str = "文档") -> bytes:
    """
    从纯文本创建 Word 文档
    
    Args:
        text_content: 纯文本内容
        title: 文档标题
    
    Returns:
        Word 文档的二进制数据
    """
    doc = Document()
    
    # 设置文档默认样式（小四号、1.5 倍行距）
    setup_document_style(doc)
    
    # 添加标题
    add_formatted_heading(doc, title, level=0)
    doc.add_paragraph()

    # 添加段落
    for paragraph_text in text_content.split('\n\n'):
        if paragraph_text.strip():
            add_formatted_paragraph(doc, paragraph_text.strip())

    # 保存文档
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
