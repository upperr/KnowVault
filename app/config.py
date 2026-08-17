"""
配置管理模块
支持 OpenAI 兼容 API（可用于本地模型如 vLLM、Ollama、LM Studio 等）
从环境变量或 .env 文件加载配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件 (从 configs 目录)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / "configs" / ".env"
load_dotenv(ENV_FILE)

# 项目根目录
ROOT_DIR = BASE_DIR

# 数据目录
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
UPLOADS_DIR = DATA_DIR / "uploads"

# 默认文档目录 (向后兼容)
DEFAULT_DOC_DIR = DOCUMENTS_DIR

# ============== OpenAI 兼容 API 配置 ==============
# API Base URL - 本地模型服务地址
# vLLM: http://localhost:8000/v1
# Ollama: http://localhost:11434/v1
# LM Studio: http://localhost:1234/v1
# 阿里云百炼 (OpenAI 兼容): https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_BASE_URL = os.environ.get(
    "OPENAI_BASE_URL",
    "http://localhost:8000/v1"  # 默认本地 vLLM 服务
)

# API Key - 本地模型通常不需要，但某些服务需要
OPENAI_API_KEY = os.environ.get(
    "OPENAI_API_KEY",
    "your-api-key"  # 本地模型可随意填写
)

# 嵌入模型 (用于向量化文档)
# BAAI/bge-large-zh-v1.5, text-embedding-3-small
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")

# LLM 模型 (用于问答和创作)
# qwen2.5:7b, llama3:8b, Qwen/Qwen2.5-7B-Instruct
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:7b")

# ============== MinerU API 配置 ==============
# MinerU 文档解析服务地址
MINERU_BASE_URL = os.environ.get("MINERU_BASE_URL", "http://localhost:8070")
MINERU_TOKEN = os.environ.get("MINERU_TOKEN", "your-mineru-token")
MINERU_TIMEOUT = int(os.environ.get("MINERU_TIMEOUT", "300"))  # 解析超时时间（秒）

# ============== OCR 和表格解析配置 ==============
# OCR 模型 (用于图片文字识别，使用 OpenAI 兼容 API)
# 支持多模态的模型：qwen-vl-plus, qwen-vl-max, gpt-4o, claude-3-5-sonnet 等
OCR_MODEL = os.environ.get("OCR_MODEL", "qwen-vl-plus")
OCR_API_KEY = os.environ.get(
    "OCR_API_KEY",
    OPENAI_API_KEY  # 默认复用主 API Key
)
OCR_BASE_URL = os.environ.get(
    "OCR_BASE_URL",
    OPENAI_BASE_URL  # 默认复用主 API 地址
)

# 表格解析模型 (使用多模态大模型，OpenAI 兼容 API)
TABLE_MODEL = os.environ.get("TABLE_MODEL", "qwen-vl-plus")
TABLE_API_KEY = os.environ.get(
    "TABLE_API_KEY",
    OPENAI_API_KEY  # 默认复用主 API Key
)
TABLE_BASE_URL = os.environ.get(
    "TABLE_BASE_URL",
    OPENAI_BASE_URL  # 默认复用主 API 地址
)

# ============== PostgreSQL + pgvector 配置 ==============
# 向量维度 (根据嵌入模型调整)
# BAAI/bge-large-zh-v1.5: 1024
# text-embedding-3-small: 1536
# text-embedding-3-large: 3072
VECTOR_DIMENSION = int(os.environ.get("VECTOR_DIMENSION", "1024"))

# PostgreSQL 数据库配置
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ.get("POSTGRES_DB", "rag_knowledge")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")

# ============== Web 服务配置 ==============
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# ============== 文档处理配置 ==============
# 嵌入批量大小（最大 25，阿里云 API 限制）
EMBEDDING_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "25"))

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "50"))
TOP_K = int(os.environ.get("TOP_K", "5"))

# ============== 增强召回流水线配置 ==============
# 向量粗召回数量 (设大一些给 rerank 留出筛选空间)
RETRIEVE_TOP_N = int(os.environ.get("RETRIEVE_TOP_N", "20"))

# Rerank 模型配置 (使用 OpenAI 兼容 API)
# 支持 rerank 的模型：gte-rerank, bge-reranker, 或任何支持 /rankings 端点的服务
RERANK_MODEL = os.environ.get("RERANK_MODEL", "gte-rerank")
RERANK_BASE_URL = os.environ.get(
    "RERANK_BASE_URL",
    OPENAI_BASE_URL  # 默认复用主 API 地址
)
RERANK_API_KEY = os.environ.get(
    "RERANK_API_KEY",
    OPENAI_API_KEY  # 默认复用主 API Key
)
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "5"))
RERANK_THRESHOLD = float(os.environ.get("RERANK_THRESHOLD", "0.0"))

# LLM 相关性决策配置
LLM_RELEVANCE_CHECK = os.environ.get("LLM_RELEVANCE_CHECK", "true").lower() == "true"

# ============== 记忆管理配置 ==============
# 短期记忆：LRU 缓存大小
MEMORY_SHORT_TERM_SIZE = int(os.environ.get("MEMORY_SHORT_TERM_SIZE", "10"))
# 短期记忆：TTL（秒），默认 1 小时
MEMORY_SHORT_TERM_TTL_SECONDS = int(os.environ.get("MEMORY_SHORT_TERM_TTL_SECONDS", "3600"))

# 长期记忆：是否启用
MEMORY_LONG_TERM_ENABLED = os.environ.get("MEMORY_LONG_TERM_ENABLED", "true").lower() == "true"
# 长期记忆：日志文件路径
MEMORY_LONG_TERM_LOG_PATH = os.environ.get(
    "MEMORY_LONG_TERM_LOG_PATH",
    str(BASE_DIR / "data" / "memory" / "request_log.jsonl")
)
# 长期记忆：关键词最少出现次数（低于此值不纳入历史记录）
MEMORY_KEYWORD_THRESHOLD = int(os.environ.get("MEMORY_KEYWORD_THRESHOLD", "1"))
# 长期记忆：高频词判定阈值（达到此值视为用户偏好）
MEMORY_HIGH_FREQ_THRESHOLD = int(os.environ.get("MEMORY_HIGH_FREQ_THRESHOLD", "3"))

# 长期记忆优化：语义相似度阈值（0-1，越高越严格）
MEMORY_SEMANTIC_SIMILARITY_THRESHOLD = float(os.environ.get("MEMORY_SEMANTIC_SIMILARITY_THRESHOLD", "0.75"))
# 长期记忆优化：时间衰减半衰期（小时），默认 24 小时
MEMORY_TIME_DECAY_HALF_LIFE = int(os.environ.get("MEMORY_TIME_DECAY_HALF_LIFE", "24"))
# 长期记忆优化：去重相似度阈值（0-1，越高去重越严格）
MEMORY_DEDUPLICATION_THRESHOLD = float(os.environ.get("MEMORY_DEDUPLICATION_THRESHOLD", "0.9"))
# 长期记忆优化：每个关键词最大保留条目数
MEMORY_MAX_ENTRIES_PER_KEYWORD = int(os.environ.get("MEMORY_MAX_ENTRIES_PER_KEYWORD", "10"))

# ============== 向后兼容 ==============
# 兼容旧代码中可能使用的 DASHSCOPE_API_KEY
DASHSCOPE_API_KEY = OPENAI_API_KEY
