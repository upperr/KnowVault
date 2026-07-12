"""
核心业务逻辑模块
"""
from app.core.knowledge_base import KnowledgeBase, get_knowledge_base
from app.core.retriever import DocumentRetriever, get_retriever
from app.core.doc_generation import (
    ContentGenerator,
    get_generator,
    markdown_to_docx,
    create_docx_from_text,
)
from app.core.qa_engine import QAEngine, get_qa_engine

__all__ = [
    # 知识库
    "KnowledgeBase",
    "get_knowledge_base",
    
    # 检索
    "DocumentRetriever",
    "get_retriever",
    
    # 文档生成
    "ContentGenerator",
    "get_generator",
    "markdown_to_docx",
    "create_docx_from_text",
    
    # QA
    "QAEngine",
    "get_qa_engine",
]
