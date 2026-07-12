# MinerU 文档解析功能（API 调用方式）

## 功能概述

基于 MinerU HTTP API 的智能文档解析系统，支持版面分析，区分文本、图片和表格三类数据：

- **文本**：直接提取
- **图片**：使用 OCR 模型（qwen-vl-plus）识别文字
- **表格**：转换为图片后用多模态大模型解析为 Markdown 格式

## 架构说明

```
┌─────────────┐                         ┌──────────────────┐
│  RAG 系统    │  POST /file_parse      │  MinerU 服务     │
│  (本应用)    │ ──────────────────────→│  (0.0.0.0:8070)  │
│             │ ←──────────────────────│                  │
└─────────────┘   返回解析结果 JSON     └──────────────────┘
       ↓
┌─────────────┐                         ┌──────────────────┐
│  OCR/表格   │  多模态 API 调用         │  通义千问 VL     │
│  解析       │ ──────────────────────→│  (qwen-vl-plus)  │
└─────────────┘   返回识别文本         └──────────────────┘
```

## 支持的文档格式

| 格式 | 扩展名 | 解析方式 |
|------|--------|----------|
| PDF | .pdf | MinerU API 版面分析 + OCR/表格识别 |
| Word | .docx | 原生解析 + 表格转 Markdown |
| PowerPoint | .pptx | 原生解析 + 表格转 Markdown |
| Excel | .xlsx | pandas 读取转 Markdown |
| 纯文本 | .txt, .md, .csv | 直接读取 |
| 图片 | .jpg, .jpeg, .png | OCR 识别 |

## MinerU API 端点

### 同步解析（推荐使用）

```bash
POST http://0.0.0.0:8070/file_parse
Content-Type: multipart/form-data

参数：
- files: 文件（支持 PDF/DOCX/PPTX/XLSX/图片）
- return_md: true（返回 Markdown 格式）
- response_format_zip: false（不返回 zip）
- return_original_file: false（不返回原文件）
```

### 异步解析（大文件）

```bash
# 提交任务
POST http://0.0.0.0:8070/tasks
-F "files=@document.pdf"
-F "return_md=true"

返回：{"task_id": "xxx", "queued_ahead": 0}

# 查询状态
GET http://0.0.0.0:8070/tasks/{task_id}

# 获取结果
GET http://0.0.0.0:8070/tasks/{task_id}/result
```

### 健康检查

```bash
GET http://0.0.0.0:8070/health

返回：{
  "protocol_version": 1,
  "processing_window_size": 10,
  "max_concurrent_requests": 5,
  "task_stats": {...}
}
```

## 配置说明

### 配置文件：`configs/.env`

```bash
# ============================================================
# MinerU API 配置
# ============================================================
# MinerU 文档解析服务地址
MINERU_BASE_URL=http://0.0.0.0:8070

# MinerU API Key（如服务需要认证）
# MINERU_API_KEY=your-api-key

# 解析超时时间（秒），默认 300 秒
MINERU_TIMEOUT=300

# ============================================================
# OCR 和表格解析配置（使用多模态大模型）
# ============================================================
# OCR 模型（用于图片文字识别）
OCR_MODEL=qwen-vl-plus

# 表格解析模型（用于表格图片转 Markdown）
TABLE_MODEL=qwen-vl-plus

# 注：OCR_API_KEY、OCR_BASE_URL、TABLE_API_KEY、TABLE_BASE_URL
# 默认复用 OPENAI_API_KEY 和 OPENAI_BASE_URL
```

## 使用方式

### 1. Web UI 同步

访问 `http://localhost:8000`，点击"同步文档"按钮。

### 2. API 调用

```bash
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"doc_dir": "/path/to/documents"}'
```

### 3. 编程方式

```python
from app.document_parser import MinerUAPIParser, extract_all_documents

# 初始化解析器
parser = MinerUAPIParser(
    base_url="http://0.0.0.0:8070",
    api_key="",  # 可选
    timeout=300
)

# 解析单个文件
result = parser.parse_file("document.pdf")

# result 结构：
# {
#     "text_blocks": [{"content": "...", "page": 1}, ...],
#     "images": [{"image_data": "...", "ocr_text": "...", "page": 1}, ...],
#     "tables": [{"markdown": "...", "page": 1}, ...],
#     "full_text": "合并后的完整文本"
# }

# 解析整个目录
documents = extract_all_documents("/path/to/documents")
```

## 工作流程

```
用户上传文档
    ↓
调用 MinerU API POST /file_parse
    ↓
MinerU 返回解析结果（JSON）
    ↓
┌──────────┬──────────┬──────────┐
│   文本   │   图片   │   表格   │
│   直接   │  调用    │  调用    │
│   使用   │  OCR     │  多模态  │
└──────────┴──────────┴──────────┘
    ↓           ↓           ↓
┌─────────────────────────────────┐
│      合并为完整文本内容          │
└─────────────────────────────────┘
    ↓
文本分块 + 向量化
    ↓
存入 PostgreSQL + pgvector
```

## 日志输出示例

```
2026-07-01 16:07:15 - app.document_parser - INFO - MinerU API 解析器已初始化，地址：http://0.0.0.0:8070
2026-07-01 16:07:16 - app.document_parser - INFO - 正在调用 MinerU API 同步解析：document.pdf
2026-07-01 16:07:20 - app.document_parser - INFO - MinerU API 同步解析成功：document.pdf
2026-07-01 16:07:21 - app.document_parser - INFO - 正在 OCR 识别图片（base64 数据）
2026-07-01 16:07:23 - app.document_parser - INFO - OCR 识别完成，共 1250 字符
2026-07-01 16:07:24 - app.document_parser - INFO - 正在解析表格（base64 数据）
2026-07-01 16:07:26 - app.document_parser - INFO - 表格解析完成
2026-07-01 16:07:27 - app.document_parser - INFO - PDF 解析完成：15 文本块，3 图片，2 表格
2026-07-01 16:07:27 - app.document_parser - INFO - 已解析：document.pdf (8500 字符)
```

## 降级处理

如果 MinerU API 不可用（超时/错误），系统会自动降级到基础解析器：

- PDF：使用 pdfplumber 提取文本（无版面分析）
- Office：使用 python-docx / python-pptx / pandas
- 图片：仍使用 OCR 识别

## 故障排查

### MinerU API 连接失败

```
ERROR - MinerU API 请求失败 document.pdf: Connection refused
```

**解决方案**：
1. 确认 MinerU 服务已启动
2. 检查服务健康状态：`curl http://0.0.0.0:8070/health`
3. 检查防火墙/网络配置
4. 确认 `MINERU_BASE_URL` 配置正确

### MinerU API 超时

```
ERROR - MinerU API 解析超时 document.pdf (>300s)
```

**解决方案**：
1. 增加 `MINERU_TIMEOUT` 配置
2. 检查 MinerU 服务性能
3. 大文档建议使用异步解析

### OCR 识别失败

```
ERROR - OCR 识别失败：API connection error
```

**检查项**：
1. 确认 `OPENAI_BASE_URL` 配置正确
2. 确认 `OPENAI_API_KEY` 有效
3. 确认模型 `qwen-vl-plus` 支持多模态

## 性能优化建议

1. **同步 vs 异步**：小文件使用同步解析（`/file_parse`），大文件使用异步（`/tasks`）
2. **超时设置**：根据文档大小调整 `MINERU_TIMEOUT`
3. **并发控制**：MinerU 服务有并发限制，注意控制请求频率
4. **缓存结果**：解析后的结果会存入数据库，避免重复解析

## 相关文件

- `app/document_parser.py` - MinerU API 解析器实现
- `app/config.py` - 配置管理（MinerU/OCR/TABLE 配置）
- `app/prompt.py` - 提示词管理（OCR/TABLE 解析提示词）
- `configs/.env` - 环境变量配置

## 参考链接

- MinerU API 文档：http://0.0.0.0:8070/docs
- 健康检查：http://0.0.0.0:8070/health
