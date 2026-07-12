#!/bin/bash
# PostgreSQL + pgvector 初始化脚本
# 用于设置 RAG 知识库数据库

set -e

# 配置变量 (可通过环境变量覆盖)
DB_NAME=${POSTGRES_DB:-"rag_knowledge"}
DB_USER=${POSTGRES_USER:-"postgres"}
DB_PASSWORD=${POSTGRES_PASSWORD:-"postgres"}
DB_HOST=${POSTGRES_HOST:-"localhost"}
DB_PORT=${POSTGRES_PORT:-"5432"}

echo "=============================================="
echo "PostgreSQL + pgvector 初始化脚本"
echo "=============================================="
echo "数据库：$DB_NAME"
echo "用户：$DB_USER"
echo "主机：$DB_HOST:$DB_PORT"
echo ""

# 检查 PostgreSQL 是否安装
if ! command -v psql &> /dev/null; then
    echo "错误：未找到 psql 命令，请先安装 PostgreSQL"
    echo "macOS: brew install postgresql"
    echo "Ubuntu: sudo apt-get install postgresql"
    exit 1
fi

# 检查 pgvector 是否可用
echo "检查 pgvector 扩展..."
if ! PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "\dx" 2>/dev/null | grep -q vector; then
    echo "警告：pgvector 扩展可能未安装"
    echo ""
    echo "安装 pgvector:"
    echo "  macOS: brew install pgvector"
    echo "  Ubuntu: sudo apt-get install postgresql-15-pgvector"
    echo "  Docker: 使用已预装 pgvector 的镜像"
    echo ""
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 创建数据库
echo "创建数据库 $DB_NAME..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || {
    echo "数据库可能已存在，继续..."
}

# 启用 pgvector 扩展并创建表
echo "初始化数据库表结构..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<EOF
-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建文档块表 (向量维度 1024，适用于 BAAI/bge-large-zh-v1.5)
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
CREATE INDEX IF NOT EXISTS idx_embedding 
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 创建文件路径索引
CREATE INDEX IF NOT EXISTS idx_file_path ON document_chunks (file_path);

-- 显示表结构
\\dt
EOF

echo ""
echo "=============================================="
echo "数据库初始化完成!"
echo "=============================================="
echo ""
echo "环境变量配置 (添加到 ~/.zshrc 或 ~/.bash_profile):"
echo ""
echo "export POSTGRES_HOST=\"$DB_HOST\""
echo "export POSTGRES_PORT=\"$DB_PORT\""
echo "export POSTGRES_DB=\"$DB_NAME\""
echo "export POSTGRES_USER=\"$DB_USER\""
echo "export POSTGRES_PASSWORD=\"$DB_PASSWORD\""
echo "export VECTOR_DIMENSION=1024"
echo ""
echo "使用 Docker 快速启动 PostgreSQL + pgvector:"
echo ""
echo "docker run -d \\"
echo "  --name postgres-pgvector \\"
echo "  -e POSTGRES_PASSWORD=$DB_PASSWORD \\"
echo "  -e POSTGRES_DB=$DB_NAME \\"
echo "  -p 5432:5432 \\"
echo "  -v pgdata:/var/lib/postgresql/data \\"
echo "  pgvector/pgvector:pg16"
echo ""
