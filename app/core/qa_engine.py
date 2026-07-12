"""
问答引擎模块
"""
import logging
from typing import List, Dict, Optional
from app.prompts import build_qa_messages, build_qa_context
from app.llm import get_llm_client

logger = logging.getLogger(__name__)


class QAEngine:
    """智能问答引擎"""

    def __init__(self):
        self.client = None

    def get_client(self):
        if self.client is None:
            self.client = get_llm_client()
        return self.client

    async def answer(self, question: str, chunks: List[Dict]) -> str:
        context = build_qa_context(chunks)
        messages = build_qa_messages(context, question)
        
        client = self.get_client()
        full_response = ""
        async for chunk in client.stream_complete(
            prompt=messages[1]["content"],
            system_prompt=messages[0]["content"],
            temperature=0.3,
            max_tokens=2048,
        ):
            full_response += chunk
        
        return full_response


_qa_engine: Optional[QAEngine] = None


def get_qa_engine() -> QAEngine:
    global _qa_engine
    if _qa_engine is None:
        _qa_engine = QAEngine()
    return _qa_engine
