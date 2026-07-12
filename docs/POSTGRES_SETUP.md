# PostgreSQL + pgvector 配置指南

本文档说明如何配置和使用 PostgreSQL + pgvector 作为向量存储。

## 快速开始

### 方案 A: 使用 Docker (推荐)

最简单的方式是使用 Docker Compose 启动预配置的 PostgreSQL + pgvector：

```bash
cd /Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code

# 启动 PostgreSQL + pgvector
docker-compose -f docker-compose.postgres.yml up -d

# 查看日志
docker-compose -f docker-compose.postgres.yml logs -f

# 停止服务
docker-compose -f docker-compose.postgres.yml down
```

### 方案 B: 本地安装 PostgreSQL + pgvector

#### macOS

```bash
# 安装 PostgreSQL 和 pgvector
brew install postgresql
brew install pgvector

# 初始化数据库 (首次安装)
initdb /usr/local/var/postgres

# 启动 PostgreSQL
brew services start postgresql

# 运行初始化脚本
chmod +x init_postgres.sh
./init_postgres.sh
```

#### Ubuntu/Debian

```bash
# 安装 PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# 安装 pgvector
sudo apt-get install postgresql-15-pgvector

# 编辑 postgresql.conf 添加共享预加载库
echo "shared_preload_libraries = 'vector'" | sudo tee -a /etc/postgresql/15/main/postgresql.conf

# 重启 PostgreSQL
sudo systemctl restart postgresql

# 运行初始化脚本
chmod +x init_postgres.sh
./init_postgres.sh
```

### 方案 C: 使用云数据库

#### 阿里云 RDS PostgreSQL

1. 创建 RDS PostgreSQL 实例 (版本 15+)
2. 在控制台启用 pgvector 扩展
3. 配置白名单允许访问
4. 设置环境变量连接

## 环境变量配置

将以下配置添加到 `~/.zshrc` 或 `~/.bash_profile`：

```bash
# PostgreSQL 连接配置
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="rag_knowledge"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="postgres"

# 向量维度 (根据嵌入模型调整)
# BAAI/bge-large-zh-v1.5: 1024
# text-embedding-3-small: 1536
# text-embedding-3-large: 3072
export VECTOR_DIMENSION="1024"
```

使配置生效：

```bash
source ~/.zshrc
```

## 验证连接

```bash
# 使用 psql 连接
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -d rag_knowledge

# 检查表结构
\dt

# 检查 pgvector 扩展
\dx

# 测试向量搜索
SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector AS distance;
```

## 向量维度配置

根据使用的嵌入模型调整向量维度：

| 嵌入模型 | 维度 | 配置 |
|---------|------|------|
| BAAI/bge-large-zh-v1.5 | 1024 | `VECTOR_DIMENSION=1024` |
| BAAI/bge-base-zh-v1.5 | 768 | `VECTOR_DIMENSION=768` |
| text-embedding-3-small | 1536 | `VECTOR_DIMENSION=1536` |
| text-embedding-3-large | 3072 | `VECTOR_DIMENSION=3072` |

修改后需要重新初始化数据库：

```bash
# Docker 方式 (删除旧数据)
docker-compose -f docker-compose.postgres.yml down -v
docker-compose -f docker-compose.postgres.yml up -d

# 本地方式
psql -h localhost -U postgres -d rag_knowledge -c "DROP TABLE document_chunks;"
psql -h localhost -U postgres -d rag_knowledge -f init.sql
```

## 性能优化

### 调整 ivfflat 索引参数

`lists` 参数影响搜索速度和精度：
- 较小值 (如 50)：搜索更快，精度略低
- 较大值 (如 200)：搜索更慢，精度更高

建议设置为总记录数的 1/1000：

```sql
-- 重建索引
DROP INDEX IF EXISTS idx_embedding;
CREATE INDEX idx_embedding 
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### 调整搜索精度

```sql
-- 设置搜索时检查的列表数量 (默认 lists * 1)
SET ivfflat.probes = 10;
```

在 Python 代码中：

```python
cur.execute("SET ivfflat.probes = 10;")
```

## 备份与恢复

### 备份

```bash
# 备份整个数据库
pg_dump -h localhost -U postgres rag_knowledge > backup.sql

# 只备份数据 (不含表结构)
pg_dump -h localhost -U postgres -a rag_knowledge > backup_data.sql
```

### 恢复

```bash
# 恢复数据库
psql -h localhost -U postgres -d rag_knowledge < backup.sql
```

## 常见问题

### Q: 连接被拒绝

检查 PostgreSQL 是否运行：
```bash
# macOS
brew services list

# 手动启动
pg_ctl -D /usr/local/var/postgres start
```

### Q: pgvector 扩展找不到

确保 pgvector 已正确安装并加载：
```sql
-- 检查扩展
\dx

-- 手动创建
CREATE EXTENSION vector;
```

### Q: 向量维度不匹配

错误信息：`cannot cast type double precision[] to vector`

解决方法：确保 `VECTOR_DIMENSION` 与嵌入模型匹配，并重新初始化数据库。

### Q: 搜索速度慢

1. 确认已创建 ivfflat 索引
2. 调整 `lists` 参数
3. 增加 `work_mem`：
   ```sql
   SET work_mem = '256MB';
   ```

## 迁移从 ChromaDB

如果之前使用 ChromaDB，需要：

1. 导出 ChromaDB 数据
2. 安装新依赖：`uv pip install psycopg2-binary`
3. 启动 PostgreSQL + pgvector
4. 运行应用，重新导入文档

数据会自动迁移到 PostgreSQL。
