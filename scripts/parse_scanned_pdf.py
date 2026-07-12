#!/usr/bin/env python3
"""
扫描版 PDF OCR 解析脚本
使用 pypdfium2 将 PDF 页面转为图片，再调用 qwen-vl-plus 进行 OCR 识别

参考：mineru_api_singlefile.py 的 API 调用方式
"""
import sys
import os
import base64
import io
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pypdfium2 as pdfium
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OCR_MODEL

# 配置
DEFAULT_PDF_PATH = "/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/documents/变电运维.pdf"
OUTPUT_DIR = "/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/output"


def pdf_to_images(pdf_path: str, scale: float = 2.0):
    """将 PDF 页面转换为 PIL 图片"""
    pdf = pdfium.PdfDocument(pdf_path)
    images = []
    
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        images.append((page_num + 1, image))
    
    pdf.close()
    return images


def image_to_base64(image, format: str = "JPEG", quality: int = 85) -> str:
    """将 PIL 图片转为 base64 字符串"""
    buffer = io.BytesIO()
    image.save(buffer, format=format, quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def ocr_image(client: OpenAI, image_base64: str, model: str = OCR_MODEL) -> str:
    """使用多模态模型进行 OCR 识别"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system", 
                "content": "你是一个专业的 OCR 文字识别助手。你的任务是识别图片中的所有文字内容。\n\n要求：\n1. 准确识别图片中的文字，包括中文、英文、数字和符号\n2. 保持原有的段落结构和格式\n3. 如果是表格，按行列顺序输出文字内容"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    }
                ]
            }
        ],
        max_tokens=3000,
        timeout=120,
    )
    return response.choices[0].message.content or ""


def parse_pdf_with_ocr(pdf_path: str, output_path: str = None, pages: int = None):
    """
    使用 OCR 解析扫描版 PDF
    
    Args:
        pdf_path: PDF 文件路径
        output_path: 输出文件路径（可选）
        pages: 处理的页数（None 表示全部）
    """
    print("=" * 60)
    print("扫描版 PDF OCR 解析")
    print("=" * 60)
    print(f"文件：{pdf_path}")
    print()
    
    # 初始化 OCR 客户端
    client = OpenAI(
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
    )
    print(f"OCR 模型：{OCR_MODEL}")
    print(f"API 地址：{OPENAI_BASE_URL}")
    print()
    
    # 转换 PDF 为图片
    print("正在转换 PDF 页面为图片...")
    images = pdf_to_images(pdf_path)
    total_pages = len(images)
    print(f"总页数：{total_pages}")
    
    if pages:
        images = images[:pages]
        print(f"仅处理前 {pages} 页")
    print()
    
    # 逐页 OCR
    results = []
    for page_num, image in images:
        print(f"[{page_num}/{total_pages}] 正在识别第 {page_num} 页...", end=" ")
        
        img_base64 = image_to_base64(image)
        text = ocr_image(client, img_base64)
        
        results.append({
            "page": page_num,
            "text": text,
            "char_count": len(text)
        })
        print(f"完成 ({len(text)} 字符)")
    
    # 合并结果
    full_text = "\n\n".join([f"=== 第 {r['page']} 页 ===\n{r['text']}" for r in results])
    
    print()
    print("=" * 60)
    print("解析完成")
    print("=" * 60)
    print(f"总字符数：{sum(r['char_count'] for r in results)}")
    
    # 保存结果
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"结果已保存：{output_path}")
    
    return full_text


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="扫描版 PDF OCR 解析")
    parser.add_argument("pdf_path", nargs="?", default=DEFAULT_PDF_PATH, help="PDF 文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出文件路径")
    parser.add_argument("-n", "--pages", type=int, default=None, help="处理的页数（测试用）")
    
    args = parser.parse_args()
    
    output_path = args.output or f"{OUTPUT_DIR}/{Path(args.pdf_path).stem}_ocr.txt"
    
    parse_pdf_with_ocr(args.pdf_path, output_path, args.pages)
