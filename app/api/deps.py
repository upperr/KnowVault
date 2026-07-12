"""
API 依赖注入模块
"""
from functools import lru_cache
from app.core.knowledge_base import get_knowledge_base, KnowledgeBase
from app.core.retriever import get_retriever, DocumentRetriever
from app.core.doc_generation import get_generator, ContentGenerator
from app.core.qa_engine import get_qa_engine, QAEngine


@lru_cache()
def get_kb_dependency() -> KnowledgeBase:
    """获取知识库依赖"""
    return get_knowledge_base()


@lru_cache()
def get_retriever_dependency() -> DocumentRetriever:
    """获取检索器依赖"""
    return get_retriever()


@lru_cache()
def get_generator_dependency() -> ContentGenerator:
    """获取生成器依赖"""
    return get_generator()


@lru_cache()
def get_qa_engine_dependency() -> QAEngine:
    """获取问答引擎依赖"""
    return get_qa_engine()
