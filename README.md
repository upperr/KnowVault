# 本地私有文档库智能问答与辅助创作工具

基于 RAG (检索增强生成) 的本地文档智能问答系统，支持 PostgreSQL + pgvector 向量存储。

## 目录结构

```
.
├── app/                      # 应用代码
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── prompt.py            # 提示词管理
│   ├── knowledge_base.py    # 知识库管理 (PostgreSQL + pgvector)
│   ├── qa_engine.py         # 问答引擎
│   ├── content_generator.py # 内容生成
│   └── document_parser.py   # 文档解析
├── data/                     # 数据目录
│   ├── documents/           # 原始文档 (PDF/Word/TXT)
│   └── uploads/             # 上传文件
├── scripts/                  # 脚本工具
│   ├── init_postgres.sh     # PostgreSQL 初始化脚本
│   └── init.sql             # 数据库表结构
├── docker/                   # Docker 配置
│   └── docker-compose.postgres.yml
├── configs/                  # 配置文件
│   └── .env.example         # 环境变量模板
├── docs/                     # 文档
│   ├── OPENAI_CONFIG.md     # OpenAI 兼容模式配置
│   └── POSTGRES_SETUP.md    # PostgreSQL 配置指南
├── webui/                    # 前端应用 (Vue 3)
│   ├── src/                 # 源代码
│   ├── package.json         # 依赖配置
│   └── vite.config.js       # Vite 配置
├── static/                   # 静态资源 (Web UI)
│   └── index.html
├── tests/                    # 测试用例
├── requirements.txt          # Python 依赖
├── pyproject.toml           # 项目配置
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd /Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code
uv pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp configs/.env.example configs/.env
# 编辑 configs/.env 根据你的环境修改配置
```

### 3. 启动 PostgreSQL + pgvector

**方式 A: Docker (推荐)**

```bash
docker-compose -f docker/docker-compose.postgres.yml up -d
```

**方式 B: 本地安装**

```bash
chmod +x scripts/init_postgres.sh
./scripts/init_postgres.sh
```

### 4. 准备文档

将 PDF/Word/TXT 文档放入 `data/documents/` 目录。

### 5. 启动应用

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000 使用系统。

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_BASE_URL` | OpenAI 兼容 API 地址 | `http://localhost:8000/v1` |
| `OPENAI_API_KEY` | API Key | `sk-no-key-required` |
| `EMBEDDING_MODEL` | 嵌入模型 | `BAAI/bge-large-zh-v1.5` |
| `LLM_MODEL` | LLM 模型 | `qwen2.5:7b` |
| `POSTGRES_HOST` | PostgreSQL 主机 | `localhost` |
| `POSTGRES_PORT` | PostgreSQL 端口 | `5432` |
| `POSTGRES_DB` | 数据库名 | `rag_knowledge` |
| `POSTGRES_USER` | 数据库用户 | `postgres` |
| `POSTGRES_PASSWORD` | 数据库密码 | `postgres` |
| `VECTOR_DIMENSION` | 向量维度 | `1024` |

### 模型配置

**嵌入模型推荐：**
- `BAAI/bge-large-zh-v1.5` (1024 维，中文优秀)
- `text-embedding-3-small` (1536 维，OpenAI)

**LLM 模型推荐：**
- `qwen2.5:7b` (Ollama)
- `Qwen/Qwen2.5-7B-Instruct` (vLLM)
- `qwen-turbo` (阿里云百炼)

## API 接口

### 同步文档
```bash
POST /api/sync
```

### 智能问答
```bash
POST /api/ask
{
  "question": "你的问题",
  "use_history": true
}
```

### 文档创作
```bash
POST /api/create
{
  "creation_type": "report",
  "requirement": "撰写一份项目总结报告",
  "title": "项目总结报告"
}
```

### 获取状态
```bash
GET /api/status
```

## 开发

### 运行测试
```bash
pytest tests/
```

### 代码格式化
```bash
black app/
ruff check app/
```

## 文档

- [OpenAI 兼容模式配置](docs/OPENAI_CONFIG.md)
- [PostgreSQL 配置指南](docs/POSTGRES_SETUP.md)

## License

MIT
