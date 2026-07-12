"""
知识库核心模块
基于 PostgreSQL + pgvector 的向量存储和检索
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import psycopg2
from psycopg2.extras import Json
from app.config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    VECTOR_DIMENSION,
)


class KnowledgeBase:
    """知识库类 - 使用 PostgreSQL + pgvector 进行向量存储和检索"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.conn = None
        self._initialized = False
        
        # 数据库连接参数
        self.db_config = {
            'host': POSTGRES_HOST,
            'port': POSTGRES_PORT,
            'database': POSTGRES_DB,
            'user': POSTGRES_USER,
            'password': POSTGRES_PASSWORD,
        }
    
    def _get_connection(self):
        """获取数据库连接"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
        return self.conn
    
    def initialize(self):
        """初始化数据库连接"""
        if self._initialized:
            return
        
        self.logger.info(f"初始化 PostgreSQL 连接：{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # 验证 pgvector 扩展已安装
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            if not cur.fetchone():
                raise RuntimeError("pgvector 扩展未安装，请先运行 init.sql 初始化脚本")
            
            # 获取向量维度
            cur.execute("""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = 'document_chunks'::regclass 
                AND attname = 'embedding'
            """)
            result = cur.fetchone()
            if result:
                actual_dim = result[0]
                if actual_dim != VECTOR_DIMENSION:
                    self.logger.warning(
                        f"配置的向量维度 ({VECTOR_DIMENSION}) 与数据库实际维度 ({actual_dim}) 不一致"
                    )
            
            cur.close()
            self._initialized = True
            self.logger.info("PostgreSQL 初始化完成")
            
        except Exception as e:
            self.logger.error(f"PostgreSQL 初始化失败：{e}")
            raise
    
    def _execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        """执行 SQL 查询"""
        if not self._initialized:
            self.initialize()
        
        conn = self._get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute(query, params or ())
            if fetch:
                result = cur.fetchall()
            else:
                conn.commit()
                result = None
            return result
        except Exception as e:
            conn.rollback()
            self.logger.error(f"SQL 执行失败：{e}")
            raise
        finally:
            cur.close()
    
    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any], embedding: List[float] = None):
        """
        添加文档到知识库
        
        Args:
            doc_id: 文档 ID (将存储在 chunk_id 字段)
            content: 文档内容
            metadata: 元数据（包含 file_name 等）
            embedding: 向量（可选，如果提供则直接存储，否则设为 NULL）
        """
        if not self._initialized:
            self.initialize()
        
        query = """
            INSERT INTO document_chunks (chunk_id, content, embedding, file_name, file_path, chunk_index, total_chunks, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                file_name = EXCLUDED.file_name,
                file_path = EXCLUDED.file_path,
                chunk_index = EXCLUDED.chunk_index,
                total_chunks = EXCLUDED.total_chunks,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
        """
        
        file_name = metadata.get('file_name', '未知文档')
        file_path = metadata.get('file_path', file_name)
        chunk_index = metadata.get('chunk_index', 0)
        total_chunks = metadata.get('total_chunks', 1)  # 默认 1 个分块
        
        # 将 embedding 转为 pgvector 格式
        embedding_str = f"[{','.join(map(str, embedding))}]" if embedding else None
        
        self._execute_query(query, (
            doc_id,
            content,
            embedding_str,
            file_name,
            file_path,
            chunk_index,
            total_chunks,
            Json(metadata)
        ))
        
        self.logger.debug(f"文档已添加：{doc_id}")
    
    def add_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]] = None):
        """
        批量添加文档
        
        Args:
            documents: 文档列表，每个文档包含 id, content, metadata
            embeddings: 可选的向量列表，与 documents 一一对应
        """
        if not documents:
            return
        
        if not self._initialized:
            self.initialize()
        
        conn = self._get_connection()
        cur = conn.cursor()
        
        query = """
            INSERT INTO document_chunks (chunk_id, content, embedding, file_name, file_path, chunk_index, total_chunks, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                file_name = EXCLUDED.file_name,
                file_path = EXCLUDED.file_path,
                chunk_index = EXCLUDED.chunk_index,
                total_chunks = EXCLUDED.total_chunks,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            for i, doc in enumerate(documents):
                embedding = embeddings[i] if embeddings and i < len(embeddings) else None
                embedding_str = f"[{','.join(map(str, embedding))}]" if embedding else None
                
                file_name = doc.get('metadata', {}).get('file_name', '未知文档')
                file_path = doc.get('metadata', {}).get('file_path', file_name)
                chunk_index = doc.get('metadata', {}).get('chunk_index', 0)
                total_chunks = doc.get('metadata', {}).get('total_chunks', 1)
                
                cur.execute(query, (
                    doc['id'],
                    doc['content'],
                    embedding_str,
                    file_name,
                    file_path,
                    chunk_index,
                    total_chunks,
                    Json(doc.get('metadata', {}))
                ))
            
            conn.commit()
            self.logger.info(f"批量添加 {len(documents)} 个文档")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"批量添加失败：{e}")
            raise
        finally:
            cur.close()
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        调用嵌入 API 生成文本向量（使用 OpenAI 兼容 API）
        
        Args:
            text: 要向量化的文本
            
        Returns:
            向量列表，失败时返回 None
        """
        try:
            import httpx
            from app.config import EMBEDDING_MODEL, OPENAI_BASE_URL, OPENAI_API_KEY
            
            # 确保 base_url 以 /v1 结尾
            base_url = OPENAI_BASE_URL.rstrip('/')
            if not base_url.endswith('/v1'):
                base_url = f"{base_url}/v1"
            
            url = f"{base_url}/embeddings"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            payload = {
                "model": EMBEDDING_MODEL,
                "input": text,
                "encoding_format": "float"
            }
            
            self.logger.debug(f"调用嵌入 API: {url}, 模型：{EMBEDDING_MODEL}")
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if "data" in data and len(data["data"]) > 0:
                    embedding = data["data"][0]["embedding"]
                    self.logger.debug(f"生成向量成功，维度：{len(embedding)}")
                    return embedding
                else:
                    self.logger.error(f"嵌入 API 返回空结果：{data}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"生成嵌入向量失败：{e}")
            return None
    
    def _get_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量调用嵌入 API 生成文本向量（使用 OpenAI 兼容 API）
        
        Args:
            texts: 要向量化的文本列表
            
        Returns:
            向量列表，失败位置返回 None
        """
        try:
            import httpx
            from app.config import EMBEDDING_MODEL, OPENAI_BASE_URL, OPENAI_API_KEY, EMBEDDING_BATCH_SIZE
            
            # 确保 base_url 以 /v1 结尾
            base_url = OPENAI_BASE_URL.rstrip('/')
            if not base_url.endswith('/v1'):
                base_url = f"{base_url}/v1"
            
            url = f"{base_url}/embeddings"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            # 分批处理，避免超过 API 限制
            all_embeddings = []
            for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                batch = texts[i:i + EMBEDDING_BATCH_SIZE]
                payload = {
                    "model": EMBEDDING_MODEL,
                    "input": batch,
                    "encoding_format": "float"
                }
                
                self.logger.debug(f"批量调用嵌入 API 批次 {i // EMBEDDING_BATCH_SIZE + 1}: {len(batch)} 个文本")
                
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    if "data" in data and len(data["data"]) > 0:
                        # 按索引排序确保顺序正确
                        sorted_data = sorted(data["data"], key=lambda x: x["index"])
                        batch_embeddings = [item["embedding"] for item in sorted_data]
                        all_embeddings.extend(batch_embeddings)
                        self.logger.debug(f"批次 {i // EMBEDDING_BATCH_SIZE + 1} 成功，返回 {len(batch_embeddings)} 个向量")
                    else:
                        self.logger.error(f"嵌入 API 返回空结果：{data}")
                        # 填充 None 保持长度一致
                        all_embeddings.extend([None] * len(batch))
            
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"批量生成嵌入向量失败：{e}")
            return [None] * len(texts)
    
    def query(self, query_text: str, top_k: int = 5, filter_metadata: Dict = None, 
              query_embedding: List[float] = None) -> List[Dict]:
        """
        查询相似文档
        
        Args:
            query_text: 查询文本
            top_k: 返回数量
            filter_metadata: 过滤条件（如 file_name）
            query_embedding: 查询向量（可选，如果不提供则自动调用嵌入 API 生成）
        
        Returns:
            文档列表，包含 content, file_name, chunk_id, similarity 等
        """
        if not self._initialized:
            self.initialize()
        
        # 如果没有提供 embedding，自动调用嵌入 API 生成
        if query_embedding is None:
            query_embedding = self._get_embedding(query_text)
            if query_embedding is None:
                self.logger.error("无法生成查询向量")
                return []
        
        # 构建 WHERE 子句
        where_clause = ""
        params = []
        
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                conditions.append(f"metadata->>%s = %s")
                params.extend([key, str(value)])
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
        
        # 添加 embedding 参数
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        params.append(embedding_str)
        params.append(top_k)
        
        # 使用余弦相似度查询（1 - cosine_distance）
        query = f"""
            SELECT chunk_id, content, file_name, metadata,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM document_chunks
            {where_clause}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        
        # 重新构建参数
        final_params = [embedding_str]
        if filter_metadata:
            for key, value in filter_metadata.items():
                final_params.extend([key, str(value)])
        final_params.extend([embedding_str, top_k])
        
        results = self._execute_query(query, tuple(final_params), fetch=True)
        
        chunks = []
        for row in results:
            chunk = {
                'content': row[1],
                'file_name': row[2],
                'chunk_id': row[0],
                'similarity': float(row[4]) if row[4] else 0.0,
                'metadata': row[3] if isinstance(row[3], dict) else {},
            }
            chunks.append(chunk)
        
        return chunks
    
    def delete_by_file_name(self, file_name: str):
        """根据文件名删除文档"""
        if not self._initialized:
            self.initialize()
        
        query = "DELETE FROM document_chunks WHERE file_name = %s"
        self._execute_query(query, (file_name,))
        
        self.logger.info(f"已删除文件 {file_name} 的所有分块")
    
    def delete_by_id(self, doc_id: str):
        """根据 ID 删除文档"""
        if not self._initialized:
            self.initialize()
        
        query = "DELETE FROM document_chunks WHERE chunk_id = %s"
        self._execute_query(query, (doc_id,))
        
        self.logger.debug(f"文档已删除：{doc_id}")
    
    def clear(self):
        """清空知识库"""
        if not self._initialized:
            self.initialize()
        
        query = "TRUNCATE TABLE document_chunks"
        self._execute_query(query)
        
        self.logger.warning("知识库已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if not self._initialized:
            self.initialize()
        
        query = """
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(DISTINCT file_name) as total_files,
                pg_size_pretty(pg_total_relation_size('document_chunks')) as table_size
            FROM document_chunks
        """
        
        results = self._execute_query(query, fetch=True)
        
        if results and results[0]:
            return {
                "total_chunks": results[0][0],
                "total_files": results[0][1],
                "table_size": results[0][2],
                "database": POSTGRES_DB,
                "host": POSTGRES_HOST,
            }
        return {"total_chunks": 0, "total_files": 0}
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """获取数据库中所有文件的信息"""
        if not self._initialized:
            self.initialize()
        
        query = """
            SELECT DISTINCT file_name, file_path
            FROM document_chunks
            ORDER BY file_name
        """
        
        results = self._execute_query(query, fetch=True)
        
        files = []
        for row in results:
            files.append({
                "file_name": row[0],
                "file_path": row[1] or row[0]
            })
        
        return files
    
    def close(self):
        """关闭数据库连接"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.logger.info("数据库连接已关闭")


# 全局实例
_kb: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """获取或创建知识库实例"""
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def close_knowledge_base():
    """关闭知识库连接"""
    global _kb
    if _kb:
        _kb.close()
        _kb = None
