"""LLM 最终决策模块

基于 Reranker 精排结果，使用 LLM 进行最终相关性判断和答案生成
"""
import logging
from typing import List, Dict, Tuple

from app.llm import get_llm_client
from app.prompts.qa import DECISION_MAKER_SYSTEM_PROMPT, DECISION_MAKER_USER_PROMPT_TEMPLATE


class DecisionMaker:
    """LLM 最终决策模块
    
    基于 Reranker 精排结果，使用 LLM 进行最终相关性判断和答案生成
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None
    
    def get_client(self):
        if self.client is None:
            self.client = get_llm_client()
        return self.client
    
    async def decide_and_generate(self, query: str, chunks: List[Dict]) -> Tuple[str, List[str]]:
        """基于召回知识进行最终决策并生成回复
        
        Args:
            query: 用户查询
            chunks: Reranker 精排后的文档片段
            
        Returns:
            (答案文本，来源列表)
        """
        self.logger.info(f"LLM 最终决策：基于 {len(chunks)} 个精排片段生成答案")
        
        if not chunks:
            return "未找到相关文档内容。", []
        
        # 构建上下文
        context_parts = []
        for i, chunk in enumerate(chunks[:5]):
            source = chunk.get('file_name', '未知文档')
            score = chunk.get('rerank_score', 0.0)
            content = chunk.get('content', '')
            context_parts.append(f"[文档{i+1}] 来源：{source} (相关性分数：{score:.3f})\n{content}")
        
        context = "\n\n".join(context_parts)
        
        # 构建提示词（从 prompts 模块导入）
        system_prompt = DECISION_MAKER_SYSTEM_PROMPT
        user_prompt = DECISION_MAKER_USER_PROMPT_TEMPLATE.format(context=context, query=query)
        
        # 调用 LLM 生成答案（使用非流式，速度更快更稳定）
        client = self.get_client()
        try:
            full_response = await client.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048
            )
        except Exception as e:
            self.logger.error(f"LLM 生成失败：{e}")
            full_response = f"生成答案时出错：{str(e)}"
        
        # 提取来源
        sources = list(set([chunk.get('file_name', '未知文档') for chunk in chunks[:5]]))
        
        return full_response, sources
