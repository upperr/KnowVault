-- PostgreSQL + pgvector 初始化脚本
-- 用于 RAG 知识库向量存储

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建文档块表 (向量维度 1024，适用于 BAAI/bge-large-zh-v1.5)
-- 如需其他维度，请修改 vector(1024) 为对应值:
-- - BAAI/bge-large-zh-v1.5: 1024
-- - text-embedding-3-small: 1536
-- - text-embedding-3-large: 3072
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    chunk_id TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    chunk_index INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建文件索引表
CREATE TABLE IF NOT EXISTS file_index (
    file_path TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    md5_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建向量索引 (余弦相似度)
-- lists 参数影响搜索速度和精度，建议设置为总记录数的 1/1000
CREATE INDEX IF NOT EXISTS idx_embedding 
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 创建文件路径索引 (加速按文件删除操作)
CREATE INDEX IF NOT EXISTS idx_file_path ON document_chunks (file_path);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_document_chunks_updated_at BEFORE UPDATE ON document_chunks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_index_updated_at BEFORE UPDATE ON file_index
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 显示创建的表
\dt

-- 显示扩展
\dx
