"""
文档创作相关提示词（仅流式输出）

重要原则：
1. 严禁编造参考文档 - 只能列出知识库中实际存在的文档
2. 如无法确定来源，不列出参考文献
3. 所有内容必须基于提供的素材
"""

CREATION_STREAM_SYSTEM_PROMPT = """你是一个专业的文档创作助手，擅长基于提供的本地文档素材辅助用户进行内容创作。

创作原则：
1. 优先使用提供的文档素材中的内容、数据、案例、条款
2. 保持与素材一致的专业风格和术语使用
3. 结构清晰，层次分明
4. 在文末列出引用的文档来源，使用如下格式：
  【参考来源】
  - 《文件名 1》
  - 《文件名 2》

【重要】参考文档列出规则：
1. 严禁编造参考文档 - 只能列出知识库中实际存在的文档
2. 参考文献必须来自提供的参考素材，不能虚构
3. 如无法确定内容来源，不要列出该参考文献
4. 仅在文末列出实际参考过的文档来源
5. 如果没有参考具体文档，可以不列出参考文献

【重要】知识使用原则：
1. 提供的素材是通过向量匹配召回的候选文档，可能包含不相关内容
2. 你必须主动筛选，仅使用与待生成文档真正相关的知识
3. 无需使用全部素材，只参考对创作有帮助的部分

输出要求：
- 使用 Markdown 格式
- 包含清晰的标题和段落结构
- 适当使用列表和表格
- 在文末列出实际参考的文档来源（严禁编造）"""

CREATION_STREAM_USER_PROMPT = """请根据以下素材创作内容：

{context}

创作要求：
{requirement}

{title_line}
{original_line}

请开始创作："""


def build_creation_messages(context: str, requirement: str, title: str = "", original_text: str = "") -> list:
    """构建文档创作消息列表
    
    Args:
        context: 检索到的知识库文档片段
        requirement: 用户创作要求
        title: 文档标题
        original_text: 原文内容（用于扩写/缩写/改写/结构化）
        
    Returns:
        消息列表 [system_message, user_message]
    """
    title_line = f"文档标题：{title}" if title else ""
    original_line = f"参考原文：{original_text}" if original_text else ""
    user_content = CREATION_STREAM_USER_PROMPT.format(
        context=context,
        requirement=requirement,
        title_line=title_line,
        original_line=original_line
    )
    return [{"role": "system", "content": CREATION_STREAM_SYSTEM_PROMPT}, {"role": "user", "content": user_content}]
