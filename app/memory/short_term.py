"""
短期记忆模块
LRU 缓存最近 N 次请求，基于字符相似度判断
"""
import logging
import hashlib
from typing import Dict, List, Optional
from collections import OrderedDict

from app.config import MEMORY_SHORT_TERM_SIZE, MEMORY_SHORT_TERM_TTL_SECONDS, OPENAI_BASE_URL, OPENAI_API_KEY
from app.memory.models import MemoryEntry
from app.memory.utils import SimilarityUtils, TimeDecayUtils

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    短期记忆：LRU 缓存最近 N 次请求
    
    特性：
    - 基于 LRU 策略管理缓存
    - 支持精确匹配和相似度匹配
    - 自动过期清理
    """
    
    def __init__(
        self,
        max_size: int = MEMORY_SHORT_TERM_SIZE,
        ttl_seconds: int = MEMORY_SHORT_TERM_TTL_SECONDS,
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, MemoryEntry] = OrderedDict()
        self.hash_to_key: Dict[str, str] = {}
    
    def _generate_key(self, query: str) -> str:
        """生成查询的唯一键（MD5 哈希）"""
        return hashlib.md5(query.strip().lower().encode()).hexdigest()
    
    def _is_expired(self, entry: MemoryEntry) -> bool:
        """检查条目是否过期"""
        return TimeDecayUtils.is_expired(entry.timestamp, self.ttl_seconds)
    
    def _cleanup_expired(self):
        """清理过期条目"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if self._is_expired(entry)
        ]
        for key in expired_keys:
            del self.cache[key]
            if key in self.hash_to_key:
                del self.hash_to_key[key]
        
        if expired_keys:
            logger.info(f"清理 {len(expired_keys)} 条过期短期记忆")
    
    def get(self, query: str, similarity_threshold: float = 0.7) -> Optional[MemoryEntry]:
        """
        获取相似查询的缓存结果
        
        Args:
            query: 当前查询
            similarity_threshold: 相似度阈值
        
        Returns:
            匹配的缓存条目，若无则返回 None
        """
        # 先清理过期条目
        self._cleanup_expired()
        
        # 精确匹配
        key = self._generate_key(query)
        if key in self.cache:
            entry = self.cache[key]
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            entry.hit_count += 1
            logger.info(f"短期记忆精确命中：{query[:50]}...")
            return entry
        
        # 相似度匹配
        best_match = None
        best_score = 0.0
        best_key = None
        
        for key, entry in list(self.cache.items()):
            score = SimilarityUtils.text_similarity(query, entry.query)
            if score > best_score and score >= similarity_threshold:
                best_score = score
                best_match = entry
                best_key = key
        
        if best_match:
            self.cache.move_to_end(best_key)
            best_match.hit_count += 1
            logger.info(f"短期记忆相似命中：{query[:50]}... (相似度={best_score:.2f})")
            return best_match
        
        return None
    
    def put(self, query: str, entry: MemoryEntry):
        """
        添加新的记忆条目
        
        Args:
            query: 用户查询
            entry: 召回结果条目
        """
        key = self._generate_key(query)
        
        # 如果已满，删除最旧的
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            if oldest_key in self.hash_to_key:
                del self.hash_to_key[oldest_key]
            logger.debug(f"LRU 淘汰：{oldest_key}")
        
        self.cache[key] = entry
        self.hash_to_key[key] = key
        logger.info(f"短期记忆已存储：{query[:50]}... (缓存大小={len(self.cache)}/{self.max_size})")
    
    def clear(self):
        """清空短期记忆"""
        self.cache.clear()
        self.hash_to_key.clear()
        logger.info("短期记忆已清空")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_hits = sum(e.hit_count for e in self.cache.values())
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "ttl_seconds": self.ttl_seconds,
        }
