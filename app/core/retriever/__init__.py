"""文档检索器模块
负责从知识库中检索相关文档，并进行重排序和相关性过滤

支持两种召回策略：
1. 知识问答：向量粗排 → Reranker 精排 → LLM 决策（仅召回 top 1 最相关知识）
2. 文档生成：直接使用向量粗排结果（全部召回，由 LLM 筛选使用）

集成记忆管理：
- 查询前：先查短期/长期记忆，命中则直接返回（加速相似请求）
- 查询后：存储召回结果到记忆（供后续相似请求使用）
"""
from typing import Optional
from .document_retriever import DocumentRetriever
from .rerank_client import RerankClient
from .decision_maker import DecisionMaker
from .memory_relevance_checker import MemoryRelevanceChecker

# 全局实例
_retriever: Optional[DocumentRetriever] = None
_decision_maker: Optional[DecisionMaker] = None


def get_retriever(top_k: int = 5) -> DocumentRetriever:
    """获取或创建检索器实例"""
    global _retriever
    if _retriever is None:
        _retriever = DocumentRetriever(top_k=top_k)
    return _retriever


def get_decision_maker() -> DecisionMaker:
    """获取或创建决策器实例"""
    global _decision_maker
    if _decision_maker is None:
        _decision_maker = DecisionMaker()
    return _decision_maker


__all__ = [
    "DocumentRetriever",
    "RerankClient",
    "DecisionMaker",
    "MemoryRelevanceChecker",
    "get_retriever",
    "get_decision_maker",
]
