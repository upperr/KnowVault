"""
文档格式配置常量

定义文档生成的所有格式参数：
- 字体配置（中英文）
- 字号配置（标题、正文）
- 段落格式（行距、间距）
- 颜色配置
"""
from docx.shared import Pt, Cm, RGBColor


# ==================== 字体配置 ====================

FONT_CHINESE_BODY = 'SimSun'      # 宋体 - 正文
FONT_CHINESE_HEADING = 'SimHei'   # 黑体 - 标题
FONT_ENGLISH = 'Times New Roman'  # 英文字体


# ==================== 字号配置 ====================

# 小四号 = 12pt
FONT_SIZE_BODY = Pt(12)        # 正文：小四号
FONT_SIZE_HEADING_1 = Pt(22)   # 一级标题
FONT_SIZE_HEADING_2 = Pt(18)   # 二级标题
FONT_SIZE_HEADING_3 = Pt(15)   # 三级标题
FONT_SIZE_CAPTION = Pt(10.5)   # 图片说明：五号


# ==================== 段落格式配置 ====================

LINE_SPACING = 1.5             # 1.5 倍行距
SPACE_BEFORE = Pt(12)          # 段前 0.5 行（基于小四号 12pt）
FIRST_LINE_INDENT = Cm(0.74)   # 首行缩进 2 字符（12pt * 2 ≈ 0.74cm）


# ==================== 图片配置 ====================

IMAGE_WIDTH = Cm(15)           # 图片最大宽度
IMAGE_SEARCH_PATHS = [         # 图片查找目录顺序
    '.',
    'data',
    'data/images',
    'data/pictures',
    'images',
    'assets',
]


# ==================== 颜色配置 ====================

COLOR_BLACK = RGBColor(0, 0, 0)  # 黑色
