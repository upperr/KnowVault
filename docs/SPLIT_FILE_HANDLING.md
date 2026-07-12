# 超长文档分割处理说明

## 概述

超长文档（>200 页或>200MB）会自动分割处理，确保 MinerU API 能够正常解析。

## 处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│  原始文件：document.pdf (500 页，超限)                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  1. 检测超限 (needs_split)               │
        │     - 文件大小 > 200 MB                  │
        │     - PDF 页数 > 200 页                   │
        │     - DOCX 页数 > 200 页                  │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  2. 分割文件 (split_file)                │
        │     原始文件 -> output/split_files/      │
        │     - document_part1.pdf (190 页)        │
        │     - document_part2.pdf (190 页)        │
        │     - document_part3.pdf (120 页)        │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  3. 解析每个子文件                       │
        │     - 使用 MinerU 批量 API                 │
        │     - 逐个解析子文件                     │
        │     - 合并所有结果                       │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  4. 删除子文件 (cleanup_sub_files)       │
        │     - 删除 output/split_files/ 中的子文件  │
        │     - 保留原始文件 document.pdf           │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  5. 保留结果                             │
        │     - 原始文件：document.pdf (未修改)     │
        │     - MD 文件：document.md (解析结果)     │
        └─────────────────────────────────────────┘
```

## 目录结构

```
code/
├── data/
│   └── documents/
│       ├── document.pdf          # 原始文件（保留）
│       └── document.md           # 解析结果（新生成）
├── output/
│   └── split_files/              # 子文件暂存目录
│       ├── document_part1.pdf    # 分割后的子文件（处理后删除）
│       ├── document_part2.pdf
│       └── document_part3.pdf
└── app/
    └── parser/
        ├── splitter.py           # 分割模块
        └── batch_processor.py    # 批量处理模块
```

## API 使用

### 分割文件

```python
from app.parser import split_file, cleanup_sub_files

# 分割文件（子文件保存到 output/split_files/）
sub_files = split_file("large_document.pdf")
print(f"分割为 {len(sub_files)} 个子文件")

# 处理子文件...

# 清理子文件
cleanup_sub_files(sub_files)
```

### 解析文件（自动处理分割）

```python
from app.parser import parse_file

# 自动检测并分割超限文件
result = parse_file("large_document.pdf")
print(f"解析完成：{len(result['full_text'])} 字符")
```

### 批量解析目录

```python
from app.parser import extract_all_documents

# 自动处理所有文件（包括超限文件）
documents = extract_all_documents("/path/to/documents")
```

## 配置说明

在 `app/parser/config.py` 中配置分割阈值：

```python
MAX_FILE_SIZE_MB = 200  # 最大文件大小（MB）
MAX_PAGES = 200         # 最大页数
```

## 子文件暂存目录

默认路径：`output/split_files/`

可以通过以下函数管理：

```python
from app.parser import get_output_dir, clear_output_dir

# 获取输出目录
output_dir = get_output_dir()
print(f"子文件暂存目录：{output_dir}")

# 清空输出目录（可选）
clear_output_dir()
```

## 日志示例

```
INFO - 文件超限，开始分割：large_document.pdf
INFO - 已分割 PDF: large_document_part1.pdf (第 1-190 页) -> output/split_files/...
INFO - 已分割 PDF: large_document_part2.pdf (第 191-380 页) -> output/split_files/...
INFO - 已分割 PDF: large_document_part3.pdf (第 381-500 页) -> output/split_files/...
INFO - PDF 分割完成：共 3 个子文件，暂存于：output/split_files
INFO - 分割完成：共 3 个子文件
INFO - [1/3] 正在解析子文件：large_document_part1.pdf
INFO - [1/3] 子文件解析完成
INFO - [2/3] 正在解析子文件：large_document_part2.pdf
INFO - [2/3] 子文件解析完成
INFO - [3/3] 正在解析子文件：large_document_part3.pdf
INFO - [3/3] 子文件解析完成
INFO - 分割解析完成：共 15 个文本块
INFO - 开始清理子文件...
INFO - 已删除文件：output/split_files/large_document_part1.pdf
INFO - 已删除文件：output/split_files/large_document_part2.pdf
INFO - 已删除文件：output/split_files/large_document_part3.pdf
INFO - 已清理 3/3 个子文件
INFO - 子文件已清理，原始文件保留：large_document.pdf
```

## 注意事项

1. **原始文件保留**：分割和解析过程不会修改或删除原始文件
2. **子文件自动清理**：解析完成后自动删除子文件
3. **异常处理**：解析失败时也会清理子文件
4. **暂存目录**：子文件保存在 `output/split_files/`，便于调试和排查问题
5. **手动清理**：如需手动清理，可调用 `clear_output_dir()`

## 错误处理

### 分割失败

```python
sub_files = split_file("corrupted.pdf")
if not sub_files:
    # 分割失败，使用备用解析方式
    result = parse_pdf_basic("corrupted.pdf")
```

### 解析失败

```python
try:
    result = parse_file("large_document.pdf")
except Exception as e:
    logger.error(f"解析失败：{e}")
    # 子文件已自动清理
```
