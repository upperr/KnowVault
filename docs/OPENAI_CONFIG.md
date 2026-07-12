# OpenAI 兼容模式配置指南

本文档说明如何配置系统使用 OpenAI 兼容 API，以便调用本地模型或其他兼容服务。

## 快速开始

### 1. 安装依赖

```bash
cd /Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code
uv pip install -r requirements.txt
```

### 2. 配置本地模型服务

系统支持多种 OpenAI 兼容的模型服务：

#### 方案 A: vLLM (推荐用于生产环境)

```bash
# 启动 vLLM 服务
vllm serve Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto
```

配置：
- `OPENAI_BASE_URL=http://localhost:8000/v1`
- `LLM_MODEL=Qwen/Qwen2.5-7B-Instruct`

#### 方案 B: Ollama (推荐用于开发测试)

```bash
# 启动 Ollama 服务
ollama serve

# 拉取模型
ollama pull qwen2.5:7b
```

配置：
- `OPENAI_BASE_URL=http://localhost:11434/v1`
- `LLM_MODEL=qwen2.5:7b`

#### 方案 C: LM Studio (图形界面，适合新手)

1. 下载并安装 LM Studio
2. 下载模型（如 Qwen2.5-7B-Instruct）
3. 启动本地服务器（默认端口 1234）

配置：
- `OPENAI_BASE_URL=http://localhost:1234/v1`
- `LLM_MODEL=qwen2.5-7b-instruct`

#### 方案 D: 阿里云百炼 (兼容模式)

如果仍想使用阿里云但通过 OpenAI 兼容接口：

配置：
- `OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
- `OPENAI_API_KEY=sk-your-aliyun-key`
- `LLM_MODEL=qwen-turbo`

### 3. 配置嵌入模型

嵌入模型也需要支持 OpenAI 兼容 API：

#### 选项 A: 使用 BAAI/bge-large-zh-v1.5 (推荐中文)

```bash
# vLLM 启动嵌入模型
vllm serve BAAI/bge-large-zh-v1.5 \
    --host 0.0.0.0 \
    --port 8001 \
    --dtype auto
```

配置：
- `EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5`

#### 选项 B: 使用 text-embedding-3-small (OpenAI)

配置：
- `OPENAI_BASE_URL=https://api.openai.com/v1`
- `OPENAI_API_KEY=sk-your-openai-key`
- `EMBEDDING_MODEL=text-embedding-3-small`

### 4. 环境变量配置

可以通过环境变量或修改 `config.py` 进行配置：

```bash
# 示例：使用 Ollama + 本地嵌入服务
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_API_KEY="sk-no-key-required"
export LLM_MODEL="qwen2.5:7b"
export EMBEDDING_MODEL="BAAI/bge-large-zh-v1.5"
```

或者直接在 `config.py` 中修改默认值。

## 常见问题

### Q: 如何验证服务是否正常？

```bash
# 测试聊天 API
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "messages": [{"role": "user", "content": "你好"}]
  }'

# 测试嵌入 API
curl http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BAAI/bge-large-zh-v1.5",
    "input": ["你好世界"]
  }'
```

### Q: 为什么使用 OpenAI 兼容模式？

1. **本地部署**: 数据完全本地，保护隐私
2. **成本更低**: 无需支付 API 调用费用
3. **灵活切换**: 可轻松切换不同模型和服务
4. **离线使用**: 无需网络连接

### Q: 性能如何？

- **vLLM**: 生产级性能，支持并发请求
- **Ollama**: 开发友好，性能适中
- **LM Studio**: 适合个人使用

### Q: 模型推荐

| 用途 | 模型 | 显存需求 |
|------|------|----------|
| 问答/创作 | Qwen2.5-7B-Instruct | ~8GB |
| 问答/创作 | Qwen2.5-14B-Instruct | ~16GB |
| 嵌入 | BAAI/bge-large-zh-v1.5 | ~2GB |
| 嵌入 | text-embedding-3-small | API 调用 |

## 启动应用

配置完成后，启动应用：

```bash
cd /Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000 使用系统。
