# MinerU 批量 API 整合文档

## 概述

本整合将 `scripts/mineru_batch_parse.py` 中的批量 API 处理逻辑融入到 `app/` 目录下的主程序中。**仅支持批量上传方式**，单个文件上传代码已全部移除。

系统自动识别并处理两种格式：
- **MinerU 支持格式**（PDF、Office、图片）：使用批量 API 解析
- **纯文本格式**（txt、md、csv 等）：直接读取

## 文件格式分类

### 1. MinerU 批量 API 支持的格式

| 格式 | 扩展名 |
|------|--------|
| PDF | .pdf |
| Word | .doc, .docx |
| PowerPoint | .ppt, .pptx |
| Excel | .xls, .xlsx |
| 图片 | .png, .jpg, .jpeg, .bmp, .tif, .tiff |

### 2. 纯文本格式（直接读取）

| 格式 | 扩展名 |
|------|--------|
| 纯文本 | .txt |
| Markdown | .md |
| CSV | .csv |
| reStructuredText | .rst |
| JSON | .json |
| XML | .xml |
| YAML | .yaml, .yml |

## 修改的文件

### 1. `app/parser/mineru_client.py`

**仅保留批量 API 方法：**
- `get_upload_urls()` - 申请批量上传链接
- `upload_file()` - 上传单个文件（批量流程的一部分）
- `check_batch_status()` - 检查批量任务状态
- `download_md_content()` - 下载并提取 Markdown 内容
- `parse_files_batch()` - 批量解析文件（核心方法）

**已删除：**
- ~~`parse_url()`~~ - 单个文件 URL 解析
- ~~`parse_local_file()`~~ - 单个本地文件解析
- ~~`check_health()`~~ - 健康检查

### 2. `app/parser/batch_processor.py`

**功能：**
- `PLAINTEXT_EXTENSIONS` 常量 - 定义纯文本格式
- `_extract_with_mineru_batch()` - 使用批量 API 解析
- `_extract_plaintext_files()` - 解析纯文本文件
- `parse_file()` - 解析单个文件（内部使用批量 API）
- `extract_all_documents()` - 批量解析目录

### 3. `app/parser/__init__.py`

**导出：**
- `BatchProcessor` 类
- `PLAINTEXT_EXTENSIONS` 常量
- `MINERU_SUPPORTED_EXTENSIONS` 常量

### 4. `app/main.py`

**API 端点：**
- `/api/sync` - 同步文档目录（自动使用批量 API）

## 使用方式

### 方式 1: Web API 调用

```bash
# 混合格式解析（PDF + txt + md 等）
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"doc_dir": "/path/to/documents"}'
```

### 方式 2: Python 代码调用

```python
from app.parser import extract_all_documents
from app.knowledge_base import KnowledgeBase

# 批量解析目录（自动处理混合格式）
documents = extract_all_documents("/path/to/documents")

# 导入知识库
kb = KnowledgeBase()
result = kb.sync_directory("/path/to/documents", documents)
```

### 方式 3: 测试脚本

```bash
cd /Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+ 微创新/创客营/code

# 运行完整测试
python test_batch_integration.py

# 测试格式识别
python test_batch_integration.py --test format

# 测试批量解析
python test_batch_integration.py --test parsing
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    extract_all_documents()                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │      扫描目录下所有文件                  │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │         按格式分类                       │
        └─────────────────────────────────────────┘
                    ↓                    ↓
    ┌─────────────────────────┐  ┌─────────────────────────┐
    │  MinerU 支持格式         │  │  纯文本格式             │
    │  PDF, DOCX, PPTX, XLSX  │  │  TXT, MD, CSV, JSON...  │
    │  图片格式                │  │                        │
    └─────────────────────────┘  └─────────────────────────┘
                    ↓                    ↓
    ┌─────────────────────────┐  ┌─────────────────────────┐
    │  MinerU 批量 API         │  │  直接读取              │
    │  - 批量上传              │  │  - UTF-8 编码           │
    │  - 轮询状态              │  │  - 保留原始格式         │
    │  - 下载 MD               │  │                        │
    └─────────────────────────┘  └─────────────────────────┘
                    ↓                    ↓
        ┌─────────────────────────────────────────┐
        │         合并所有解析结果                 │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │      知识库导入                         │
        │    - 文本切片                           │
        │    - 向量化                             │
        │    - PostgreSQL + pgvector 存储         │
        └─────────────────────────────────────────┘
```

## 配置说明

在 `configs/.env` 中配置 MinerU API：

```bash
# MinerU API 配置
MINERU_BASE_URL=https://mineru.net
MINERU_TOKEN=your_token_here
MINERU_TIMEOUT=300
```

## 批量 API 参数

```python
def parse_files_batch(
    self,
    file_paths: List[str],
    wait_complete: bool = True,      # 是否等待完成
    poll_interval: int = 30,         # 轮询间隔（秒）
    is_ocr: bool = False,            # 是否启用 OCR
    max_batch_size: int = 50         # 每批最多 50 个文件
) -> Dict[str, Optional[str]]:
```

## 错误处理

### 常见问题

1. **上传失败**
   - 检查网络连接
   - 验证 Token 是否有效
   - 确认文件大小不超过限制

2. **解析超时**
   - 增加 `MINERU_TIMEOUT` 值
   - 分割大文件

3. **下载失败**
   - 检查 `full_zip_url` 是否有效
   - 确认压缩包中包含 `full.md` 文件

## 性能优化建议

1. **批量处理** - 所有文件使用批量 API，减少 HTTP 请求
2. **混合格式自动处理** - 无需手动分类
3. **调整批次大小** - 根据网络情况调整 `max_batch_size`
4. **缓存结果** - 避免重复解析相同文件

## 测试验证

运行测试脚本验证整合效果：

```bash
python test_batch_integration.py
```

## 代码清理说明

**已移除的代码：**
- `MinerUClient.parse_url()` - 单个文件 URL 解析
- `MinerUClient.parse_local_file()` - 单个本地文件解析
- `MinerUClient.check_health()` - 健康检查
- `BatchProcessor._extract_with_single_api()` - 单个文件 API 解析
- `BatchProcessor.use_batch_api` 参数 - 已固化使用批量 API

**原因：**
- MinerU 批量 API 效率更高
- 减少代码重复
- 简化维护成本
- 统一处理逻辑
