#!/usr/bin/env python3
"""
PDF 转 TXT 工具
使用 pypdf 库将 PDF 文件转换为 TXT 格式
"""

from pypdf import PdfReader
from pathlib import Path
import sys

def pdf_to_txt(pdf_path, txt_path=None):
    """将 PDF 转换为 TXT"""
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        print(f"❌ PDF 文件不存在：{pdf_path}")
        return False
    
    if txt_path is None:
        txt_path = pdf_path.with_suffix('.txt')
    else:
        txt_path = Path(txt_path)
    
    print(f"📄 正在处理：{pdf_path.name}")
    print(f"文件大小：{pdf_path.stat().st_size / 1024:.1f} KB\n")
    
    try:
        # 打开 PDF
        reader = PdfReader(pdf_path)
        print(f"✅ PDF 加载成功")
        print(f"总页数：{len(reader.pages)}\n")
        
        # 提取所有文本
        text_content = []
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                text_content.append(f"--- 第 {i} 页 ---\n{text.strip()}")
                print(f"第 {i} 页：{len(text)} 字符")
            else:
                print(f"第 {i} 页：⚠️ 无文本内容 (可能是图片)")
        
        # 保存为 TXT
        if text_content:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(text_content))
            
            print(f"\n{'='*50}")
            print(f"✅ 转换完成！")
            print(f"输出文件：{txt_path}")
            print(f"文件大小：{txt_path.stat().st_size / 1024:.1f} KB")
            print(f"{'='*50}")
            return True
        else:
            print("\n⚠️ 警告：未从 PDF 中提取到文本内容")
            print("   该 PDF 可能是扫描版图片，需要使用 OCR 工具")
            return False
            
    except Exception as e:
        print(f"\n❌ 转换失败：{e}")
        return False

if __name__ == "__main__":
    # 默认转换特高压.pdf
    pdf_file = "/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/documents/特高压.pdf"
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    
    pdf_to_txt(pdf_file)
