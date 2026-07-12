# 文档生成模块

## 目录结构

```
app/core/doc_generation/
├── __init__.py              # 模块入口，导出公共 API
├── config.py                # 格式配置常量
├── formatter.py             # 格式化工具（字体、段落）
├── image_handler.py         # 图片处理（解析、插入）
├── markdown_parser.py       # Markdown 语法解析
├── markdown_converter.py    # Markdown 转 Word
├── text_converter.py        # 纯文本转 Word
└── content_generator.py     # LLM 内容生成
```

## 模块说明

### config.py - 配置常量

定义所有格式参数：

```python
# 字体
FONT_CHINESE_BODY = 'SimSun'      # 宋体
FONT_CHINESE_HEADING = 'SimHei'   # 黑体
FONT_ENGLISH = 'Times New Roman'

# 字号
FONT_SIZE_BODY = Pt(12)           # 小四号
FONT_SIZE_HEADING_1 = Pt(22)
FONT_SIZE_HEADING_2 = Pt(18)
FONT_SIZE_HEADING_3 = Pt(15)

# 段落格式
LINE_SPACING = 1.5                # 1.5 倍行距
SPACE_BEFORE = Pt(12)             # 段前 0.5 行
```

### formatter.py - 格式化工具

提供底层格式设置功能：

- `set_font(run, font_name, size, bold)` - 设置 run 字体
- `set_paragraph_font(paragraph, font_name, size, bold)` - 设置段落字体
- `set_paragraph_format(paragraph, line_spacing, space_before)` - 设置段落格式
- `setup_document_style(doc)` - 设置文档默认样式
- `add_formatted_heading(doc, text, level)` - 添加格式化标题
- `add_formatted_paragraph(doc, text, style, font_name, size, bold)` - 添加格式化段落

### image_handler.py - 图片处理

处理 Markdown 图片：

- `download_image(url)` - 读取本地图片（支持多目录查找）
- `parse_markdown_image(line)` - 解析 `![alt](url)` 语法
- `insert_image_to_doc(doc, image_url, alt_text, counter)` - 插入图片到 Word

图片查找顺序：
1. 当前目录
2. `data/`, `data/images/`, `data/pictures/`
3. `images/`, `assets/`

### markdown_parser.py - Markdown 解析

解析 Markdown 语法：

- `parse_inline_formatting(text)` - 解析粗体、斜体、代码、链接
- `parse_heading(line)` - 解析标题 (`#`, `##`, `###`)
- `parse_list_item(line)` - 解析列表项 (`-`, `*`, `1.`)

### markdown_converter.py - Markdown 转 Word

主转换函数：

```python
def markdown_to_docx(markdown_content: str, title: str = "文档") -> bytes:
    """
    将 Markdown 转换为 Word
    
    功能：
    1. 解析 Markdown 标题、列表、段落
    2. 插入本地图片
    3. 应用字体和段落格式
    """
```

### text_converter.py - 纯文本转 Word

简单转换函数：

```python
def create_docx_from_text(text_content: str, title: str = "文档") -> bytes:
    """
    将纯文本转换为 Word（按双换行分段）
    """
```

### content_generator.py - 内容生成

基于 LLM 的内容生成：

```python
class ContentGenerator:
    async def generate(context, requirement, creation_type, title, original_text):
        """流式生成内容"""
```

## 使用示例

### 导入模块

```python
from app.core.doc_generation import (
    ContentGenerator,
    get_generator,
    markdown_to_docx,
    create_docx_from_text,
    FONT_SIZE_BODY,
    LINE_SPACING,
)
```

### Markdown 转 Word

```python
md_content = """
# 报告标题

正文使用小四号字，1.5 倍行距。

![图示](data/images/figure1.png)

## 章节

- 列表项 1
- 列表项 2
"""

docx_bytes = markdown_to_docx(md_content, title="报告")
with open("output.docx", "wb") as f:
    f.write(docx_bytes)
```

### 内容生成 + 格式转换

```python
from app.core.doc_generation import get_generator, markdown_to_docx

# 生成内容
generator = get_generator()
md_content = ""
async for chunk in generator.generate(
    context="背景信息",
    requirement="创作要求",
    creation_type="article",
    title="我的文章",
):
    md_content += chunk

# 转换为 Word
docx_bytes = markdown_to_docx(md_content, title="我的文章")
```

## 格式规范

### 字体

| 元素 | 字体 | 字号 |
|------|------|------|
| 标题 | 黑体 | 22pt / 18pt / 15pt |
| 正文 | 宋体 | 12pt (小四号) |
| 英文 | Times New Roman | - |

### 段落

| 属性 | 值 |
|------|-----|
| 行距 | 1.5 倍 |
| 段前距 | 0.5 行 (12pt) |
| 段后距 | 0 |

### 图片

- 宽度：15cm（自动缩放）
- 对齐：居中
- 说明：`图 N: 说明文字`（五号字）

## 迁移说明

### 旧代码

```python
from app.core.optimizer import markdown_to_docx
from app.core.generator import ContentGenerator
```

### 新代码

```python
from app.core.doc_generation import markdown_to_docx, ContentGenerator
```

功能完全相同，只是模块位置变化。

## 设计原则

1. **单一职责**：每个文件专注于一个功能
2. **配置分离**：所有格式参数集中在 `config.py`
3. **工具函数**：通用功能提取到 `formatter.py`、`markdown_parser.py`
4. **易于扩展**：新增格式或解析规则只需修改对应文件

## 代码行数

| 文件 | 行数 | 说明 |
|------|------|------|
| config.py | ~40 | 配置常量 |
| formatter.py | ~150 | 格式化工具 |
| image_handler.py | ~130 | 图片处理 |
| markdown_parser.py | ~60 | Markdown 解析 |
| markdown_converter.py | ~120 | 主转换器 |
| text_converter.py | ~30 | 简单转换器 |
| content_generator.py | ~70 | LLM 生成 |

每个文件控制在 150 行以内，易于维护。
