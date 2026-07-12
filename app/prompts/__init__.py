"""提示词管理模块
统一管理所有 LLM 提示词，按功能分类组织
"""

# ============================================================
# 检索器相关提示词
# ============================================================
from app.prompts.retriever import (
    # Reranker 模型 instruct
    RERANK_INSTRUCT,
    
    # 记忆相关性验证
    MEMORY_RELEVANCE_CHECK_SYSTEM_PROMPT,
    MEMORY_RELEVANCE_CHECK_USER_PROMPT_TEMPLATE,
)

# ============================================================
# 问答相关提示词
# ============================================================
from app.prompts.qa import (
    # Reranker 相关性判断（已废弃，保留兼容）
    RELEVANCE_CHECK_SYSTEM_PROMPT,
    RELEVANCE_CHECK_USER_PROMPT_TEMPLATE,
    
    # LLM 答案生成
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT_TEMPLATE,
    QUICK_QA_SYSTEM_PROMPT,
    QUICK_QA_USER_PROMPT_TEMPLATE,
    DECISION_MAKER_SYSTEM_PROMPT,
    DECISION_MAKER_USER_PROMPT_TEMPLATE,
)

# ============================================================
# 文档创作相关提示词（仅流式输出）
# ============================================================
from app.prompts.creation import (
    CREATION_STREAM_SYSTEM_PROMPT,
    CREATION_STREAM_USER_PROMPT,
    build_creation_messages,
)

# ============================================================
# 文档优化相关提示词
# ============================================================
from app.prompts.optimize import (
    OPTIMIZE_SYSTEM_PROMPT,
    OPTIMIZE_PROMPT_WITH_INSTRUCTION,
    build_optimize_messages,
)

# ============================================================
# 文档解析相关提示词
# ============================================================
from app.prompts.parser import (
    OCR_SYSTEM_PROMPT,
    TABLE_TO_MARKDOWN_PROMPT,
)

# ============================================================
# 工具函数
# ============================================================
from app.prompts.utils import (
    build_qa_messages,
    build_context,
    build_qa_context,
)

__all__ = [
    # 检索器相关
    "RERANK_INSTRUCT",
    "MEMORY_RELEVANCE_CHECK_SYSTEM_PROMPT",
    "MEMORY_RELEVANCE_CHECK_USER_PROMPT_TEMPLATE",
    
    # 问答相关
    "RELEVANCE_CHECK_SYSTEM_PROMPT",
    "RELEVANCE_CHECK_USER_PROMPT_TEMPLATE",
    "QA_SYSTEM_PROMPT",
    "QA_USER_PROMPT_TEMPLATE",
    "QUICK_QA_SYSTEM_PROMPT",
    "QUICK_QA_USER_PROMPT_TEMPLATE",
    "DECISION_MAKER_SYSTEM_PROMPT",
    "DECISION_MAKER_USER_PROMPT_TEMPLATE",
    
    # 创作相关（仅流式）
    "CREATION_STREAM_SYSTEM_PROMPT",
    "CREATION_STREAM_USER_PROMPT",
    "build_creation_messages",
    
    # 优化相关
    "OPTIMIZE_SYSTEM_PROMPT",
    "OPTIMIZE_PROMPT_WITH_INSTRUCTION",
    "build_optimize_messages",
    
    # 解析相关
    "OCR_SYSTEM_PROMPT",
    "TABLE_TO_MARKDOWN_PROMPT",
    
    # 工具函数
    "build_qa_messages",
    "build_context",
    "build_qa_context",
]
