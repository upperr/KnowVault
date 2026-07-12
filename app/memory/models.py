"""
记忆管理数据模型
统一定义记忆条目数据结构
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


@dataclass
class MemoryEntry:
    """
    记忆条目数据类
    
    Attributes:
        query: 用户原始查询
        query_keywords: 提取的关键词列表
        query_embedding: 查询向量（用于语义匹配，可选）
        chunks: 召回的文档块列表
        pipeline_stages: 召回流水线统计信息
        timestamp: ISO 格式时间戳
        hit_count: 被命中次数
        decay_weight: 时间衰减权重（长期记忆专用）
    """
    query: str
    query_keywords: List[str]
    chunks: List[Dict]
    pipeline_stages: Dict
    timestamp: str
    query_embedding: Optional[List[float]] = None
    hit_count: int = 0
    decay_weight: float = 1.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        """从字典创建"""
        return cls(**data)
    
    def update_weight(self, weight: float):
        """更新衰减权重"""
        self.decay_weight = weight


@dataclass
class MatchResult:
    """
    记忆匹配结果数据类
    
    Attributes:
        entry: 匹配的记忆条目
        score: 综合得分
        semantic_score: 语义相似度
        decay_weight: 时间衰减权重
    """
    entry: MemoryEntry
    score: float = 0.0
    semantic_score: float = 0.0
    decay_weight: float = 1.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "entry": self.entry.to_dict(),
            "score": self.score,
            "semantic_score": self.semantic_score,
            "decay_weight": self.decay_weight,
        }
