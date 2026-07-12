"""
提示词工具函数
"""
from app.prompts.qa import QA_SYSTEM_PROMPT, QA_USER_PROMPT_TEMPLATE


def build_qa_messages(context: str, question: str) -> list:
    return [
        {"role": "system", "content": QA_SYSTEM_PROMPT},
        {"role": "user", "content": QA_USER_PROMPT_TEMPLATE.format(context=context, question=question)},
    ]


def build_context(chunks: list) -> str:
    if not chunks: return "（暂无相关素材）"
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"【素材 {i}】来源:《{chunk['file_name']}》\n{chunk['content']}")
    return "\n\n".join(context_parts)


def build_qa_context(chunks: list) -> str:
    if not chunks: return ""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"【文档片段 {i}】来源：《{chunk['file_name']}》\n{chunk['content']}")
    return "\n\n".join(context_parts)
