"""
记忆管理模块
长短期记忆管理系统，用于加速相似请求的知识召回

包结构：
- models: 数据模型（MemoryEntry, MatchResult）
- utils: 工具函数（嵌入、相似度、时间衰减）
- short_term: 短期记忆（LRU 缓存）
- long_term: 长期记忆（语义匹配 + 时间衰减 + 去重）
- manager: 统一记忆管理器
"""

from app.memory.models import MemoryEntry, MatchResult
from app.memory.utils import EmbeddingUtils, SimilarityUtils, TimeDecayUtils
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory
from app.memory.manager import MemoryManager

__all__ = [
    # 数据模型
    "MemoryEntry",
    "MatchResult",
    # 工具类
    "EmbeddingUtils",
    "SimilarityUtils",
    "TimeDecayUtils",
    # 记忆类
    "ShortTermMemory",
    "LongTermMemory",
    "MemoryManager",
]
