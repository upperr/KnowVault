"""文档检索器模块
负责从知识库中检索相关文档，并进行重排序和相关性过滤

支持两种召回策略：
1. 知识问答：向量粗排 → Reranker 精排 → LLM 决策（仅召回 top 1 最相关知识）
2. 文档生成：直接使用向量粗排结果（全部召回，由 LLM 筛选使用）

集成记忆管理：
- 查询前：先查短期/长期记忆，命中则直接返回（加速相似请求）
- 查询后：存储召回结果到记忆（供后续相似请求使用）
"""
import logging
from typing import List, Dict, Any, Optional

from app.core.knowledge_base import get_knowledge_base
from app.llm import get_llm_client
from app.config import RETRIEVE_TOP_N, RERANK_TOP_K
from app.memory.manager import MemoryManager
from .rerank_client import RerankClient
from .memory_relevance_checker import MemoryRelevanceChecker


class DocumentRetriever:
    """文档检索器"""
    
    def __init__(self, top_k: int = 5):
        self.logger = logging.getLogger(__name__)
        self.top_k = top_k
        self.kb = None
        self.client = None
        self.rerank_client = None
        self.memory_mgr = MemoryManager()
        self.relevance_checker = MemoryRelevanceChecker()
    
    def get_kb(self):
        if self.kb is None:
            self.kb = get_knowledge_base()
        return self.kb
    
    def get_client(self):
        if self.client is None:
            self.client = get_llm_client()
        return self.client
    
    def get_rerank_client(self):
        """获取或创建 Reranker 客户端"""
        if self.rerank_client is None:
            self.rerank_client = RerankClient()
        return self.rerank_client
    
    async def retrieve(self, query: str, top_k: int = None, use_rerank: bool = True, mode: str = "qa") -> List[Dict]:
        """检索相关文档（异步方法）
        
        集成记忆管理：
        1. 先查短期/长期记忆
        2. 短期记忆命中：直接返回（高置信度）
        3. 长期记忆命中：交给大模型决策是否匹配
        4. 未命中：正常检索并存储结果到记忆
        
        支持两种召回策略：
        
        1. 知识问答模式 (mode="qa")：
           - 向量相似度粗排 → Reranker 模型精排 → LLM 最终决策
           - 至多召回 1 条最相关知识（top_k=1），因为问答一般只需回答一个具体知识点
           - 适用于：/api/qa/stream 接口
        
        2. 文档生成模式 (mode="generation")：
           - 直接使用基于向量匹配的粗排召回结果
           - 全部交给大模型用于文档生成，由 LLM 筛选使用相关知识
           - 适用于：/api/creation/stream 接口
        
        Args:
            query: 查询文本
            top_k: 返回数量（可选，默认：qa 模式=1, generation 模式=RETRIEVE_TOP_N）
            use_rerank: 是否使用 rerank 精排（仅 qa 模式有效）
            mode: 召回模式，"qa" 或 "generation"
            
        Returns:
            检索到的文档片段列表
        """
        # ========== 记忆查询：先查短期/长期记忆 ==========
        # 注意：文档生成模式不使用记忆（每次生成需求可能不同）
        if mode == "qa":
            hit, hit_type, entry = self.memory_mgr.query(query, similarity_threshold=0.7)
            if hit:
                if hit_type == "short_term":
                    # 短期记忆命中：直接返回（高置信度，最近请求）
                    self.logger.info(f"短期记忆命中，直接返回：{query[:50]}...")
                    chunks = entry.chunks
                    if entry.pipeline_stages:
                        entry.pipeline_stages["memory_hit"] = hit_type
                    self.logger.info(f"从短期记忆直接返回 {len(chunks)} 个文档片段")
                    return chunks
                elif hit_type == "long_term":
                    # 长期记忆命中：跳过低级检索（粗排 + 精排），但需要 LLM 验证相关性
                    self.logger.info(f"长期记忆语义命中：{query[:50]}...，进行相关性验证")
                    memory_chunks = entry.chunks
                    
                    # 使用 LLM 验证长期记忆的相关性
                    is_relevant = await self.relevance_checker.check_relevance(query, memory_chunks)
                    
                    if is_relevant:
                        # 相关性验证通过，返回记忆结果
                        self.logger.info(f"长期记忆相关性验证通过，返回 {len(memory_chunks)} 个文档片段")
                        if entry.pipeline_stages:
                            entry.pipeline_stages["memory_hit"] = hit_type
                            entry.pipeline_stages["relevance_checked"] = True
                        return memory_chunks
                    else:
                        # 相关性验证失败，fallback 到正常向量检索
                        self.logger.info(f"长期记忆相关性验证失败，fallback 到正常检索流程")
                        # 继续执行下方的正常检索逻辑
        
        # 根据模式设置默认 top_k
        if mode == "qa":
            # 知识问答：仅召回 top 1 最相关知识
            top_k = 1 if top_k is None else min(top_k, 1)
            use_rerank = use_rerank  # qa 模式默认启用 rerank
        else:
            # 文档生成：使用粗排全部结果，不设上限
            top_k = RETRIEVE_TOP_N if top_k is None else top_k
            use_rerank = False  # generation 模式不使用 rerank
        
        kb = self.get_kb()
        
        self.logger.info(f"检索查询：{query} (mode={mode}, 粗排={RETRIEVE_TOP_N if use_rerank else top_k}, 精排 top_k={top_k}, use_rerank={use_rerank})")
        
        # 1. 向量相似度粗排
        if mode == "generation":
            # 文档生成：直接使用粗排结果
            chunks = kb.query(query, top_k=top_k)
            if not chunks:
                self.logger.warning("未检索到相关文档")
                return []
            self.logger.info(f"粗排召回 {len(chunks)} 个文档片段，全部用于文档生成")
            return chunks
        else:
            # 知识问答：粗排 + 精排
            chunks = kb.query(query, top_k=RETRIEVE_TOP_N if use_rerank else top_k)
            
            if not chunks:
                self.logger.warning("未检索到相关文档")
                return []
            
            self.logger.info(f"初步检索到 {len(chunks)} 个文档片段（粗排）")
            
            if use_rerank:
                # 2. Reranker 模型精排
                rerank_client = self.get_rerank_client()
                chunks = await rerank_client.rerank(query, chunks, top_k)
            
            self.logger.info(f"最终返回 {len(chunks)} 个文档片段（精排后 top_k={top_k}）")
            
            # ========== 记忆存储：存储召回结果到记忆 ==========
            pipeline_stages = {
                "source": "vector_search",
                "use_rerank": use_rerank,
                "initial_count": RETRIEVE_TOP_N if use_rerank else top_k,
                "final_count": len(chunks),
            }
            self.memory_mgr.store(query, chunks, pipeline_stages)
            self.logger.info(f"召回结果已存储到记忆（短期 + 长期）")
            
            return chunks[:top_k]
