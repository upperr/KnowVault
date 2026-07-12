"""
记忆管理器
统一长短期记忆接口，提供完整的记忆管理功能
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from app.memory.models import MemoryEntry
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    记忆管理器：统一长短期记忆接口
    
    查询优先级：短期记忆 > 长期记忆
    """
    
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
    
    def query(
        self,
        query: str,
        similarity_threshold: float = 0.7
    ) -> Tuple[bool, str, Optional[MemoryEntry]]:
        """
        查询记忆
        
        Args:
            query: 用户查询
            similarity_threshold: 短期记忆相似度阈值
        
        Returns:
            (是否命中，命中类型，记忆条目)
            命中类型："short_term" | "long_term" | None
        """
        # 1. 先查短期记忆
        short_entry = self.short_term.get(query, similarity_threshold=similarity_threshold)
        if short_entry:
            return True, "short_term", short_entry
        
        # 2. 再查长期记忆（语义匹配 + 时间衰减）
        matched, keywords, entries = self.long_term.match(query)
        if matched and entries:
            best_entry = entries[0]
            logger.info(f"长期记忆命中关键词：{keywords}")
            
            return True, "long_term", MemoryEntry(
                query=query,
                query_keywords=keywords,
                chunks=best_entry.get("chunks", []),
                pipeline_stages={"source": "long_term_memory", "semantic_match": True},
                timestamp=datetime.now().isoformat(),
            )
        
        return False, None, None
    
    def store(self, query: str, chunks: List[Dict], pipeline_stages: Dict):
        """
        存储召回结果到记忆
        
        Args:
            query: 用户查询
            chunks: 召回的文档块
            pipeline_stages: 流水线统计
        """
        keywords = self.long_term._extract_keywords(query)
        
        entry = MemoryEntry(
            query=query,
            query_keywords=keywords,
            chunks=chunks,
            pipeline_stages=pipeline_stages,
            timestamp=datetime.now().isoformat(),
        )
        
        # 存储到短期记忆
        self.short_term.put(query, entry)
        
        # 记录到长期记忆（带语义向量化、时间衰减、去重）
        self.long_term.record(query, entry)
    
    def get_stats(self) -> Dict:
        """获取记忆系统统计信息"""
        return {
            "short_term": self.short_term.get_stats(),
            "long_term": self.long_term.get_stats(),
        }
    
    def clear(self, short_term: bool = True, long_term: bool = True):
        """
        清空记忆
        
        Args:
            short_term: 是否清空短期记忆
            long_term: 是否清空长期记忆
        """
        if short_term:
            self.short_term.clear()
        if long_term:
            self.long_term.clear()
    
    def clear_short_term(self):
        """清空短期记忆"""
        self.short_term.clear()
    
    def clear_long_term(self):
        """清空长期记忆"""
        self.long_term.clear()
    
    def cleanup_long_term(self, max_age_hours: int = 720):
        """
        清理长期记忆中过期的条目
        
        Args:
            max_age_hours: 最大保留时间（小时），默认 30 天
        """
        self.long_term.cleanup_old_entries(max_age_hours)
    
    def refresh_long_term_preferences(self):
        """刷新长期记忆用户偏好"""
        self.long_term.refresh_preferences()
