# MinerU URL 方式调用 & 批量处理说明

## 修改内容

### 1. API 调用方式改为 URL 方式

参考 `mineru_api_singlefile.py`，将原来的文件上传方式改为 URL 方式：

**修改前（文件上传）：**
```python
with open(file_path, "rb") as f:
    files = {"files": f}
    data = {"return_md": "true"}
    response = requests.post(
        f"{self.base_url}/file_parse",
        files=files,
        data=data,
        ...
    )
```

**修改后（URL 方式）：**
```python
data = {
    "url": file_url,
    "model_version": "vlm"  # 使用 VLM 模型进行版面分析
}
response = requests.post(
    f"{self.base_url}/api/v4/extract/task",
    json=data,
    headers=self.headers,
    ...
)
```

### 2. Token 配置

从 `configs/.env` 中的 `MINERU_TOKEN` 字段获取：

```python
from app.config import MINERU_TOKEN

headers = {
    "Authorization": f"Bearer {MINERU_TOKEN}"
}
```

### 3. 本地文件 URL 转换

支持两种 URL 格式：

1. **HTTP/HTTPS URL**：直接使用
   ```python
   if file_path.startswith(("http://", "https://")):
       return self._parse_file_sync(file_path)
   ```

2. **本地文件**：转换为 `file://` 协议
   ```python
   file_url = f"file://{os.path.abspath(file_path)}"
   ```

### 4. 批量循环处理

`extract_all_documents()` 函数现在支持：

1. 遍历目录下所有支持的文件
2. 对每个文件循环调用 MinerU API
3. 自动检测文件大小和页数，超限则分割
4. 显示处理进度：`[1/5] 正在解析：xxx.pdf`
5. 错误处理和日志记录

```python
# 循环调用 MinerU API 处理每个文档
for idx, file_path in enumerate(supported_files, 1):
    logger.info(f"[{idx}/{len(supported_files)}] 正在解析：{file_path.name}")
    
    result = parser.parse_file(str(file_path))
    # ...
```

## 使用示例

### 单个文件解析

```python
from app.document_parser import parse_file

# 解析单个文件（自动检测并分割大文件）
result = parse_file("/path/to/document.pdf")
content = result["full_text"]
```

### 批量解析目录

```python
from app.document_parser import extract_all_documents

# 批量解析目录下所有文档
documents = extract_all_documents("/path/to/documents")

for doc in documents:
    print(f"文件名：{doc['file_name']}")
    print(f"内容长度：{len(doc['content'])} 字符")
```

## 配置说明

在 `configs/.env` 中配置 MinerU 相关参数：

```bash
# MinerU API 配置
MINERU_BASE_URL=http://0.0.0.0:8070
MINERU_TOKEN=eyJ0eXBlIj...s-eQ
MINERU_TIMEOUT=300
```

## 限制阈值

```python
MAX_FILE_SIZE_MB = 200  # 最大文件大小（MB）
MAX_PAGES = 200         # 最大页数
```

超过限制的文件会自动分割后逐个调用 MinerU API 处理。

## 日志输出示例

```
INFO - 找到 5 个文档，开始批量解析...
INFO - [1/5] 正在解析：标书.docx
INFO - 文件大小超限：21.56MB > 200MB
INFO - 文件超限，开始分割：标书.docx
INFO - 已分割 DOCX: 标书_part1.docx (元素 1-50)
INFO - 已分割 DOCX: 标书_part2.docx (元素 51-100)
...
INFO - [1/5] 解析完成：标书.docx (125000 字符)
INFO - [2/5] 正在解析：变电检修.pdf
INFO - [2/5] 解析完成：变电检修.pdf (8500 字符)
INFO - 批量解析完成：成功 5/5 个文档
```

## 注意事项

1. **MinerU 服务必须运行**：确保 MinerU 服务在配置的地址上运行
2. **文件访问权限**：MinerU 服务需要能访问 `file://` 路径指向的文件
3. **Token 有效性**：确保 `MINERU_TOKEN` 有效且未过期
4. **超时设置**：大文件解析可能需要较长时间，适当调整 `MINERU_TIMEOUT`

## 测试

运行测试脚本验证功能：

```bash
cd /path/to/project
.venv/bin/python test_mineru_url.py
```
