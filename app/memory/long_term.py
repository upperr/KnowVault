"""
长期记忆模块（优化版）
支持语义相似度匹配、时间衰减机制、记忆聚合去重
"""
import logging
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from app.config import (
    MEMORY_LONG_TERM_ENABLED,
    MEMORY_LONG_TERM_LOG_PATH,
    MEMORY_KEYWORD_THRESHOLD,
    MEMORY_HIGH_FREQ_THRESHOLD,
    MEMORY_SEMANTIC_SIMILARITY_THRESHOLD,
    MEMORY_TIME_DECAY_HALF_LIFE,
    MEMORY_DEDUPLICATION_THRESHOLD,
    MEMORY_MAX_ENTRIES_PER_KEYWORD,
    OPENAI_BASE_URL,
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
)
from app.memory.models import MemoryEntry, MatchResult
from app.memory.utils import EmbeddingUtils, SimilarityUtils, TimeDecayUtils

logger = logging.getLogger(__name__)


class LongTermMemory:
    """
    长期记忆（优化版）
    
    优化特性：
    1. 语义相似度匹配：使用向量化关键词，捕捉语义而非字面匹配
    2. 时间衰减机制：近期请求权重更高，自动遗忘旧记忆
    3. 记忆聚合去重：相似请求合并，避免冗余存储
    """
    
    def __init__(
        self,
        log_path: str = MEMORY_LONG_TERM_LOG_PATH,
        keyword_threshold: int = MEMORY_KEYWORD_THRESHOLD,
        high_freq_threshold: int = MEMORY_HIGH_FREQ_THRESHOLD,
        semantic_threshold: float = MEMORY_SEMANTIC_SIMILARITY_THRESHOLD,
        time_decay_half_life: int = MEMORY_TIME_DECAY_HALF_LIFE,
        dedup_threshold: float = MEMORY_DEDUPLICATION_THRESHOLD,
        max_entries_per_keyword: int = MEMORY_MAX_ENTRIES_PER_KEYWORD,
        enabled: bool = MEMORY_LONG_TERM_ENABLED,
    ):
        self.enabled = enabled
        self.log_path = Path(log_path)
        self.keyword_threshold = keyword_threshold
        self.high_freq_threshold = high_freq_threshold
        self.semantic_threshold = semantic_threshold
        self.time_decay_half_life = time_decay_half_life
        self.dedup_threshold = dedup_threshold
        self.max_entries_per_keyword = max_entries_per_keyword
        
        # 用户偏好关键词
        self.preference_keywords: List[str] = []
        # 关键词 -> 历史请求映射
        self.keyword_to_entries: Dict[str, List[Dict]] = {}
        # 关键词向量缓存
        self.keyword_embeddings: Dict[str, List[float]] = {}
        
        # 嵌入工具（延迟初始化）
        self.embed_utils = EmbeddingUtils(OPENAI_BASE_URL, OPENAI_API_KEY, EMBEDDING_MODEL)
        
        # 确保日志目录存在
        if self.enabled:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        # 注意：_load_preferences() 改为手动调用，避免初始化时阻塞
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        从查询中提取关键词
        
        支持：
        - 中文 2-4 字短语
        - 英文单词（包括连字符）
        - 字母 + 数字组合（如 G800, v1.0）
        """
        chinese_pattern = re.compile(r'[\u4e00-\u9fa5]{2,4}')
        english_pattern = re.compile(r'\b[a-zA-Z][a-zA-Z-]{2,}\b')
        alphanum_pattern = re.compile(r'\b[a-zA-Z]+\d+[a-zA-Z]*\b')
        
        chinese_keywords = chinese_pattern.findall(query)
        english_keywords = english_pattern.findall(query)
        alphanum_keywords = alphanum_pattern.findall(query)
        
        return list(set(chinese_keywords + english_keywords + alphanum_keywords))
    
    def _generate_query_hash(self, query: str) -> str:
        """生成查询的语义哈希（用于去重）"""
        embedding = self.embed_utils.get_embedding(query)
        if embedding:
            # 将向量量化为二进制哈希
            hash_bits = ''.join('1' if x > 0 else '0' for x in embedding[:64])
            return hex(int(hash_bits, 2))[2:]
        # 降级：使用文本哈希
        import hashlib
        return hashlib.md5(query.strip().lower().encode()).hexdigest()
    
    def _is_duplicate(
        self,
        query: str,
        existing_entries: List[Dict]
    ) -> Tuple[bool, Optional[Dict]]:
        """
        检查新查询是否与现有条目重复
        
        Returns:
            (是否重复，最相似的现有条目)
        """
        if not existing_entries:
            return False, None
        
        # 获取新查询的向量
        query_embedding = self.embed_utils.get_embedding(query)
        
        best_match = None
        best_score = 0.0
        
        for entry in existing_entries:
            entry_embedding = entry.get("query_embedding")
            if entry_embedding:
                similarity = SimilarityUtils.cosine_similarity(query_embedding, entry_embedding)
                if similarity > best_score:
                    best_score = similarity
                    best_match = entry
        
        if best_score >= self.dedup_threshold:
            logger.info(f"检测到重复请求：'{query}' 与 '{best_match.get('query', '')}' 相似度={best_score:.3f}")
            return True, best_match
        
        return False, None
    
    def _log_request(self, query: str, keywords: List[str], entry: MemoryEntry):
        """记录请求到日志文件"""
        if not self.enabled:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "keywords": keywords,
            "query_embedding": entry.query_embedding,
            "chunk_count": len(entry.chunks),
            "decay_weight": entry.decay_weight,
        }
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"记录长期记忆日志失败：{e}")
    
    def _load_preferences(self):
        """从日志文件加载并分析用户偏好（带时间衰减）"""
        if not self.log_path.exists():
            return
        
        keyword_counter: Dict[str, float] = {}
        entries_by_keyword: Dict[str, List[Dict]] = {}
        keyword_embeddings: Dict[str, List[float]] = {}
        
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        keywords = entry.get("keywords", [])
                        timestamp = entry.get("timestamp", "")
                        
                        # 计算时间衰减权重
                        decay_weight = TimeDecayUtils.compute_decay(
                            timestamp, self.time_decay_half_life
                        ) if timestamp else 1.0
                        
                        for kw in keywords:
                            # 使用衰减后的权重计数
                            keyword_counter[kw] = keyword_counter.get(kw, 0) + decay_weight
                            
                            if kw not in entries_by_keyword:
                                entries_by_keyword[kw] = []
                            entries_by_keyword[kw].append(entry)
                            
                            # 缓存关键词向量
                            if kw not in keyword_embeddings:
                                keyword_embeddings[kw] = self.embed_utils.get_embedding(kw)
                    except json.JSONDecodeError:
                        continue
            
            # 提取高频词作为偏好关键词（基于衰减后的权重）
            self.preference_keywords = [
                kw for kw, weight in keyword_counter.items()
                if weight >= self.high_freq_threshold
            ]
            
            # 构建关键词到历史条目的映射（应用去重和数量限制）
            for kw, entries in entries_by_keyword.items():
                if keyword_counter[kw] >= self.keyword_threshold:
                    # 去重：只保留不重复的条目
                    unique_entries = []
                    seen_hashes = set()
                    
                    for entry in entries:
                        query_hash = self._generate_query_hash(entry.get("query", ""))
                        if query_hash not in seen_hashes:
                            seen_hashes.add(query_hash)
                            unique_entries.append(entry)
                    
                    # 限制数量
                    self.keyword_to_entries[kw] = unique_entries[:self.max_entries_per_keyword]
            
            # 保存关键词向量缓存
            self.keyword_embeddings = keyword_embeddings
            
            logger.info(
                f"长期记忆偏好加载完成：{len(self.preference_keywords)} 个高频词，"
                f"{len(self.keyword_to_entries)} 个关键词有历史记录"
            )
            
        except Exception as e:
            logger.warning(f"加载长期记忆偏好失败：{e}")
    
    def refresh_preferences(self):
        """刷新用户偏好（重新分析日志）"""
        self._load_preferences()
    
    def match(self, query: str) -> Tuple[bool, List[str], List[Dict]]:
        """
        匹配查询与长期记忆（语义相似度 + 时间衰减）
        
        Args:
            query: 用户查询
        
        Returns:
            (是否命中，匹配的关键词，历史召回结果)
        """
        if not self.enabled:
            return False, [], []
        
        keywords = self._extract_keywords(query)
        if not keywords:
            return False, [], []
        
        # 获取查询向量
        query_embedding = self.embed_utils.get_embedding(query)
        
        matched_keywords = []
        matched_results: List[MatchResult] = []
        
        for kw in keywords:
            if kw in self.keyword_to_entries:
                entries = self.keyword_to_entries[kw]
                
                for entry in entries:
                    # 语义相似度
                    entry_embedding = entry.get("query_embedding")
                    semantic_score = SimilarityUtils.cosine_similarity(
                        query_embedding, entry_embedding
                    ) if entry_embedding else 0.0
                    
                    # 时间衰减权重
                    decay_weight = TimeDecayUtils.compute_decay(
                        entry.get("timestamp", ""), self.time_decay_half_life
                    )
                    
                    # 综合得分
                    combined_score = semantic_score * decay_weight
                    
                    # 如果语义相似度超过阈值，认为匹配
                    if semantic_score >= self.semantic_threshold:
                        if kw not in matched_keywords:
                            matched_keywords.append(kw)
                        
                        matched_results.append(MatchResult(
                            entry=MemoryEntry.from_dict(entry),
                            score=combined_score,
                            semantic_score=semantic_score,
                            decay_weight=decay_weight,
                        ))
        
        if matched_keywords:
            # 按综合得分排序，取 top 5
            matched_results.sort(key=lambda x: x.score, reverse=True)
            top_entries = [r.entry.to_dict() for r in matched_results[:5]]
            
            logger.info(
                f"长期记忆语义命中：{matched_keywords}, "
                f"最高分={matched_results[0].score:.3f} "
                f"(语义={matched_results[0].semantic_score:.3f}, "
                f"衰减={matched_results[0].decay_weight:.3f})"
            )
            
            return True, matched_keywords, top_entries
        
        return False, [], []
    
    def record(self, query: str, entry: MemoryEntry):
        """
        记录新的请求到长期记忆（带聚合去重）
        
        Args:
            query: 用户查询
            entry: 召回结果条目
        """
        if not self.enabled:
            return
        
        keywords = self._extract_keywords(query)
        
        # 获取查询向量
        entry.query_embedding = self.embed_utils.get_embedding(query)
        
        # 计算初始时间衰减权重
        entry.decay_weight = TimeDecayUtils.compute_decay(
            entry.timestamp, self.time_decay_half_life
        )
        
        # 检查是否与现有条目重复
        for kw in keywords:
            if kw in self.keyword_to_entries:
                is_dup, similar_entry = self._is_duplicate(query, self.keyword_to_entries[kw])
                if is_dup:
                    # 聚合：更新现有条目的命中次数
                    similar_entry["hit_count"] = similar_entry.get("hit_count", 0) + 1
                    logger.info(f"请求已聚合到现有条目：'{query}' -> '{similar_entry.get('query', '')}'")
                    return
        
        # 不重复则新增
        self._log_request(query, keywords, entry)
        
        # 更新内存中的映射
        for kw in keywords:
            if kw not in self.keyword_to_entries:
                self.keyword_to_entries[kw] = []
            self.keyword_to_entries[kw].append(entry.to_dict())
        
        # 限制每个关键词的条目数量
        for kw in keywords:
            if len(self.keyword_to_entries[kw]) > self.max_entries_per_keyword:
                self.keyword_to_entries[kw] = self.keyword_to_entries[kw][-self.max_entries_per_keyword:]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_weight = 0.0
        entry_count = 0
        
        for entries in self.keyword_to_entries.values():
            for entry in entries:
                total_weight += entry.get("decay_weight", 1.0)
                entry_count += 1
        
        avg_decay = total_weight / entry_count if entry_count > 0 else 1.0
        
        return {
            "enabled": self.enabled,
            "preference_keywords": self.preference_keywords,
            "keyword_count": len(self.keyword_to_entries),
            "total_entries": entry_count,
            "avg_decay_weight": round(avg_decay, 4),
            "log_path": str(self.log_path),
            "semantic_threshold": self.semantic_threshold,
            "time_decay_half_life_hours": self.time_decay_half_life,
            "dedup_threshold": self.dedup_threshold,
        }
    
    def clear(self):
        """清空长期记忆"""
        if self.log_path.exists():
            self.log_path.unlink()
        self.preference_keywords = []
        self.keyword_to_entries.clear()
        self.keyword_embeddings.clear()
        logger.info("长期记忆已清空")
    
    def cleanup_old_entries(self, max_age_hours: int = 720):
        """
        清理过期的记忆条目
        
        Args:
            max_age_hours: 最大保留时间（小时），默认 30 天
        """
        if not self.log_path.exists():
            return
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        try:
            valid_entries = []
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                        if entry_time >= cutoff_time:
                            valid_entries.append(line)
                        else:
                            cleaned_count += 1
                    except (json.JSONDecodeError, ValueError):
                        cleaned_count += 1
            
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.writelines(valid_entries)
            
            self._load_preferences()
            logger.info(f"清理完成：删除 {cleaned_count} 条过期记录")
            
        except Exception as e:
            logger.warning(f"清理过期记录失败：{e}")
