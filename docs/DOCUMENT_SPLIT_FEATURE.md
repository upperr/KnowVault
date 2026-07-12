# 文档自动分割功能说明

## 功能概述

在 MinerU 版面分析之前，自动检测文档大小和页数，如果超过限制则自动分割文档，解析完成后删除原始文件和临时子文件。

## 限制阈值

在 `app/document_parser.py` 中定义：

```python
MAX_FILE_SIZE_MB = 200  # 最大文件大小（MB）
MAX_PAGES = 200         # 最大页数
```

## 支持的文档格式

- **PDF**: 支持精确页数检测，自动分割
- **DOCX/DOC**: 支持页数估算（优先使用 LibreOffice 转换获取准确页数），自动分割
- 其他格式（TXT、PPTX、XLSX 等）：仅检测文件大小，不检测页数

## 工作流程

```
1. 解析文件前检查
   ├── 检查文件大小 > 200MB？
   └── 检查页数 > 200 页？
   
2. 如果需要分割
   ├── PDF: 使用 pypdf 按页数分割
   ├── DOCX: 按段落和表格分割
   └── 生成子文件：filename_part1.ext, filename_part2.ext, ...
   
3. 解析所有子文件
   └── 合并所有子文件的解析结果
   
4. 清理
   ├── 删除所有子文件
   └── 删除原始文件
```

## DOCX 页数检测方法

### 方法 1: LibreOffice 转换（推荐，最准确）
如果系统安装了 LibreOffice，会自动将 DOCX 转换为 PDF 后获取准确页数。

安装 LibreOffice:
```bash
# macOS
brew install libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# CentOS/RHEL
sudo yum install libreoffice
```

### 方法 2: 估算法（备用）
如果未安装 LibreOffice，使用基于文档内容的估算法：
- 分析段落、表格等内容元素
- 考虑中文字符密度和页面布局
- 误差约 10-15%

## 依赖安装

```bash
# 新增依赖
pypdf>=4.0.0  # PDF 分割

# 已有依赖
pdfplumber>=0.10.3    # PDF 页数检测
python-docx>=1.1.0    # DOCX 处理
```

安装命令：
```bash
cd /path/to/project
uv pip install -r requirements.txt
```

## 使用示例

功能已集成到现有流程中，无需修改调用代码：

```python
from app.document_parser import parse_file, extract_all_documents

# 解析单个文件（自动检测并分割）
result = parse_file("/path/to/large_document.pdf")

# 批量解析目录（每个文件都会自动检测）
documents = extract_all_documents("/path/to/documents")
```

## 日志输出

```
INFO - 文件大小超限：250.50MB > 200MB
INFO - 文件超限，开始分割：/path/to/large_doc.pdf
INFO - 已分割 PDF: large_doc_part1.pdf (第 1-190 页)
INFO - 已分割 PDF: large_doc_part2.pdf (第 191-350 页)
INFO - PDF 分割完成：共 2 个子文件
INFO - 解析子文件：/path/to/large_doc_part1.pdf
INFO - 解析子文件：/path/to/large_doc_part2.pdf
INFO - 已删除子文件：/path/to/large_doc_part1.pdf
INFO - 已删除子文件：/path/to/large_doc_part2.pdf
INFO - 已删除原始文件：/path/to/large_doc.pdf
INFO - 分割解析完成：共 156 个文本块
```

## 测试

运行测试脚本验证功能：

```bash
cd /path/to/project
.venv/bin/python test_document_split.py
```

## 注意事项

1. **分割后的文件名**: 子文件命名为 `原文件名_partN.扩展名`
2. **临时文件清理**: 解析完成后自动删除所有子文件和原始文件
3. **内存占用**: 大文件分割后逐个解析，降低单次内存占用
4. **页数估算误差**: DOCX 页数估算存在约 10-15% 误差，建议安装 LibreOffice 获取准确页数
5. **不支持的格式**: 纯文本、图片等格式不进行页数检测，仅检测文件大小
