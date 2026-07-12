"""长期记忆相关性验证模块

使用 LLM 判断长期记忆中的历史答案是否与当前用户请求匹配
如果不匹配，则 fallback 到正常向量检索流程
"""
import logging
from typing import List, Dict

from app.llm import get_llm_client
from app.prompts.retriever import MEMORY_RELEVANCE_CHECK_SYSTEM_PROMPT, MEMORY_RELEVANCE_CHECK_USER_PROMPT_TEMPLATE


class MemoryRelevanceChecker:
    """长期记忆相关性验证模块
    
    使用 LLM 判断长期记忆中的历史答案是否与当前用户请求匹配
    如果不匹配，则 fallback 到正常向量检索流程
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None
    
    def get_client(self):
        if self.client is None:
            self.client = get_llm_client()
        return self.client
    
    async def check_relevance(self, query: str, memory_chunks: List[Dict]) -> bool:
        """
        检查长期记忆中的文档片段是否与当前查询相关
        
        Args:
            query: 当前用户查询
            memory_chunks: 长期记忆中的历史文档片段
            
        Returns:
            bool: True=相关，False=不相关（需要 fallback 到正常检索）
        """
        if not memory_chunks:
            self.logger.warning("记忆片段为空，判定为不相关")
            return False
        
        self.logger.info(f"验证长期记忆相关性：{query[:50]}...")
        
        # 构建上下文（记忆中的历史答案）
        context_parts = []
        for i, chunk in enumerate(memory_chunks[:5]):
            source = chunk.get('file_name', '未知文档')
            content = chunk.get('content', '')
            context_parts.append(f"[历史答案{i+1}] 来源：{source}\n{content}")
        
        context = "\n\n".join(context_parts)
        
        # 构建验证提示词
        system_prompt = MEMORY_RELEVANCE_CHECK_SYSTEM_PROMPT
        user_prompt = MEMORY_RELEVANCE_CHECK_USER_PROMPT_TEMPLATE.format(query=query, context=context)
        
        # 调用 LLM 判断
        client = self.get_client()
        try:
            response = await client.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # 低温度，确保判断稳定
                max_tokens=20
            )
            
            # 解析响应
            response = response.strip().lower()
            is_relevant = "相关" in response or "relevant" in response
            
            self.logger.info(f"长期记忆相关性判定：{'相关' if is_relevant else '不相关'} (LLM 响应：{response})")
            return is_relevant
            
        except Exception as e:
            self.logger.error(f"相关性验证失败：{e}，降级为相关")
            # 失败时默认相关，避免不必要的检索
            return True
