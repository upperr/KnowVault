"""
内容生成器（流式输出）

基于 LLM 生成文档内容
"""
import logging
from typing import Optional

from app.prompts import build_creation_messages
from app.llm import get_llm_client

logger = logging.getLogger(__name__)


class ContentGenerator:
    """内容生成器（流式）"""

    def __init__(self):
        self.client = None

    def get_client(self):
        """获取 LLM 客户端"""
        if self.client is None:
            self.client = get_llm_client()
        return self.client

    async def generate(
        self,
        context: str,
        requirement: str,
        title: str = "",
        original_text: str = "",
    ):
        """
        生成内容（流式）
        
        Args:
            context: 上下文/背景信息（检索到的知识库文档）
            requirement: 创作要求
            title: 文档标题
            original_text: 原文（用于扩写/缩写/改写/结构化）
        
        Yields:
            生成的内容片段
        """
        messages = build_creation_messages(
            context=context,
            requirement=requirement,
            title=title,
            original_text=original_text,
        )

        client = self.get_client()
        full_response = ""
        async for chunk in client.stream_complete(
            prompt=messages[1]["content"],
            system_prompt=messages[0]["content"],
            temperature=0.7,
            max_tokens=4096,
        ):
            full_response += chunk
            yield chunk
        
        logger.info("内容生成完成")


# 全局单例
_generator: Optional[ContentGenerator] = None


def get_generator() -> ContentGenerator:
    """获取内容生成器单例"""
    global _generator
    if _generator is None:
        _generator = ContentGenerator()
    return _generator
