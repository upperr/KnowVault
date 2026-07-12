"""Reranker 模型客户端 - 使用阿里云 qwen3-rerank 模型"""
import logging
from typing import List, Dict, Any

from app.config import RERANK_MODEL, DASHSCOPE_API_KEY, RERANK_TOP_K
from app.prompts.retriever import RERANK_INSTRUCT


class RerankClient:
    """Reranker 模型客户端 - 使用阿里云 qwen3-rerank 模型"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = RERANK_MODEL or "qwen3-rerank"
        self.api_key = DASHSCOPE_API_KEY
        self.instruct = RERANK_INSTRUCT
    
    async def rerank(self, query: str, chunks: List[Dict], top_k: int) -> List[Dict]:
        """使用 Reranker 模型对文档片段进行重排序
        
        Args:
            query: 查询文本
            chunks: 待排序的文档片段列表
            top_k: 最终返回数量（使用 RERANK_TOP_K）
            
        Returns:
            重排序后的文档片段列表
        """
        self.logger.info(f"开始 Reranker 精排，输入 {len(chunks)} 个片段，目标 top_k={top_k}")
        
        try:
            import dashscope
            from http import HTTPStatus
            
            # 设置 API Key
            dashscope.api_key = self.api_key
            # 配置 API 地址
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
            
            # 准备文档列表
            documents = [chunk.get('content', '')[:2000] for chunk in chunks]  # 限制长度避免超出 token 限制
            
            self.logger.debug(f"调用 Reranker API: query={query[:50]}..., docs={len(documents)}")
            
            # 同步调用 Reranker API（dashscope 不支持异步）
            resp = dashscope.TextReRank.call(
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_k,  # 使用 RERANK_TOP_K
                return_documents=True,
                instruct=self.instruct
            )
            
            if resp.status_code == HTTPStatus.OK:
                self.logger.info(f"Reranker 调用成功")
                
                # 解析结果
                reranked_chunks = self._parse_rerank_result(resp, chunks)
                self.logger.info(f"Rerank 后保留 {len(reranked_chunks)} 个片段")
                return reranked_chunks
            else:
                self.logger.warning(f"Reranker 调用失败：{resp.status_code}, {resp}")
                # 降级返回原始结果
                return chunks[:top_k]
                
        except ImportError:
            self.logger.warning("dashscope 未安装，跳过 Rerank，返回原始结果")
            return chunks[:top_k]
        except Exception as e:
            self.logger.warning(f"Rerank 失败：{e}，返回原始结果")
            return chunks[:top_k]
    
    def _parse_rerank_result(self, resp: Any, original_chunks: List[Dict]) -> List[Dict]:
        """解析 Reranker 响应结果
        
        Args:
            resp: Reranker API 响应
            original_chunks: 原始文档片段
            
        Returns:
            重排序后的文档片段列表
        """
        try:
            # dashscope 返回格式：resp.output.results 包含排序结果
            results = resp.output.get('results', [])
            
            if not results:
                self.logger.warning("Reranker 返回空结果")
                return original_chunks[:5]
            
            # 根据 index 映射回原始 chunks
            reranked = []
            for result in results:
                index = result.get('index', 0)
                if 0 <= index < len(original_chunks):
                    chunk = original_chunks[index].copy()
                    # 添加 rerank 分数
                    chunk['rerank_score'] = result.get('relevance_score', 0.0)
                    reranked.append(chunk)
            
            # 按 rerank 分数降序排序
            reranked.sort(key=lambda x: x.get('rerank_score', 0.0), reverse=True)
            
            return reranked
            
        except Exception as e:
            self.logger.error(f"解析 Reranker 结果失败：{e}")
            return original_chunks[:5]
