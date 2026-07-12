"""
Markdown 解析工具

提供 Markdown 语法解析功能
"""
import re


def parse_inline_formatting(text: str) -> str:
    """
    解析 Markdown 内联格式（粗体、斜体、代码、链接）
    
    Args:
        text: 包含 Markdown 格式的文本
    
    Returns:
        移除格式后的纯文本
    """
    # 移除粗体 **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # 移除斜体 *text*
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # 移除行内代码 `text`
    text = re.sub(r'`(.+?)`', r'\1', text)
    # 移除链接 [text](url)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    # 移除图片 ![alt](url)
    text = re.sub(r'!\[(.+?)\]\(.+?\)', r'\1', text)
    return text


def parse_heading(line: str) -> tuple:
    """
    解析 Markdown 标题
    
    Args:
        line: 文本行
    
    Returns:
        (level, text) 如果没有标题返回 (None, None)
    """
    if line.startswith('### '):
        return 3, line[4:]
    elif line.startswith('## '):
        return 2, line[3:]
    elif line.startswith('# '):
        return 1, line[2:]
    return None, None


def parse_list_item(line: str) -> tuple:
    """
    解析 Markdown 列表项
    
    Args:
        line: 文本行
    
    Returns:
        (is_list, text, list_type) 
        is_list: 是否是列表项
        text: 列表项内容
        list_type: 'bullet' 或 'numbered'
    """
    # 无序列表
    if line.startswith('- ') or line.startswith('* ') or line.startswith('+ '):
        return True, line[2:], 'bullet'
    
    # 有序列表
    match = re.match(r'^(\d+)\. ', line)
    if match:
        text = re.sub(r'^\d+\. ', '', line)
        return True, text, 'numbered'
    
    return False, None, None
