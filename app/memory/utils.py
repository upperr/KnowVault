"""
记忆管理工具函数
提供嵌入向量、相似度计算、时间衰减等通用工具
"""
import hashlib
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from openai import OpenAI

logger = logging.getLogger(__name__)


class EmbeddingUtils:
    """嵌入向量工具类（延迟初始化）"""
    
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=5.0,  # 5 秒超时
            )
        return self._client
    
    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入向量
        
        Args:
            text: 输入文本
        
        Returns:
            嵌入向量，API 失败时返回伪向量
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"嵌入 API 调用失败：{e}，使用伪向量降级")
            return self._text_to_pseudo_embedding(text)
    
    def _text_to_pseudo_embedding(self, text: str) -> List[float]:
        """
        将文本转换为伪向量（降级方案）
        使用 MD5 哈希生成 128 维向量
        """
        hash_bytes = hashlib.md5(text.encode()).digest()
        return [(b - 128) / 128 for b in hash_bytes]


class SimilarityUtils:
    """相似度计算工具类"""
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量 1
            vec2: 向量 2
        
        Returns:
            余弦相似度值 [-1, 1]
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    @staticmethod
    def jaccard_similarity(set1: set, set2: set) -> float:
        """
        计算 Jaccard 相似度（字符集）
        """
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def text_similarity(text1: str, text2: str) -> float:
        """
        计算文本相似度（基于字符集 Jaccard）
        """
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        return SimilarityUtils.jaccard_similarity(set1, set2)


class TimeDecayUtils:
    """时间衰减工具类"""
    
    @staticmethod
    def compute_decay(timestamp: str, half_life_hours: int = 24) -> float:
        """
        计算时间衰减权重
        
        公式：weight = 0.5^(hours_elapsed / half_life)
        """
        entry_time = datetime.fromisoformat(timestamp)
        hours_elapsed = (datetime.now() - entry_time).total_seconds() / 3600
        
        return 0.5 ** (hours_elapsed / half_life_hours)
    
    @staticmethod
    def is_expired(timestamp: str, ttl_seconds: int) -> bool:
        """检查是否过期"""
        entry_time = datetime.fromisoformat(timestamp)
        return datetime.now() - entry_time > timedelta(seconds=ttl_seconds)
