#!/usr/bin/env python3
"""
使用 MinerU 在线 API 解析 PDF 文档
参考：mineru_api_singlefile.py

直接从 config.py 加载 MINERU_TOKEN
"""
import sys
import os
import requests
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import MINERU_BASE_URL, MINERU_TOKEN, MINERU_TIMEOUT

# 配置
DEFAULT_PDF_PATH = "/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/documents/变电运维.pdf"
OUTPUT_DIR = "/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/output"


def parse_with_mineru(pdf_path: str, output_path: str = None):
    """
    使用 MinerU API 解析 PDF
    支持本地文件（file:// URL）和 HTTP/HTTPS URL
    """
    print("=" * 60)
    print("MinerU API 解析")
    print("=" * 60)
    print(f"文件：{pdf_path}")
    print(f"API 地址：{MINERU_BASE_URL}")
    print(f"Token: {MINERU_TOKEN[:20]}..." if len(MINERU_TOKEN) > 20 else f"Token: {MINERU_TOKEN}")
    print(f"超时：{MINERU_TIMEOUT}秒")
    print()
    
    # 准备请求头
    headers = {
        "Content-Type": "application/json",
    }
    if MINERU_TOKEN:
        headers["Authorization"] = f"Bearer {MINERU_TOKEN}"
    
    # 确定文件 URL
    if pdf_path.startswith(("http://", "https://")):
        file_url = pdf_path
    else:
        # 本地文件转换为 file:// URL
        file_url = f"file://{os.path.abspath(pdf_path)}"
    
    data = {
        "url": file_url,
        "model_version": "vlm"  # 使用 VLM 模型进行版面分析
    }
    
    print(f"文件 URL: {file_url}")
    print(f"正在调用 MinerU API...")
    print()
    
    try:
        response = requests.post(
            f"{MINERU_BASE_URL}/api/v4/extract/task",
            headers=headers,
            json=data,
            timeout=MINERU_TIMEOUT,
        )
        
        print(f"响应状态码：{response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("解析成功!")
            
            # 提取结果
            if "data" in result:
                data_content = result["data"]
                
                # 保存原始结果
                if output_path:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    import json
                    with open(output_path + ".json", "w", encoding="utf-8") as f:
                        json.dump(data_content, f, ensure_ascii=False, indent=2)
                    print(f"原始结果已保存：{output_path}.json")
                
                # 提取 Markdown 内容
                if "md_content" in data_content:
                    md_content = data_content["md_content"]
                    with open(output_path + ".md", "w", encoding="utf-8") as f:
                        f.write(md_content)
                    print(f"Markdown 已保存：{output_path}.md")
                    print(f"内容长度：{len(md_content)} 字符")
                    return md_content
                else:
                    print("返回数据中无 md_content 字段")
                    print(f"返回数据结构：{list(data_content.keys()) if isinstance(data_content, dict) else 'N/A'}")
            
            return result
        else:
            print(f"解析失败：{response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"请求超时 (>{MINERU_TIMEOUT}s)")
        return None
    except Exception as e:
        print(f"请求异常：{e}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MinerU PDF 解析")
    parser.add_argument("pdf_path", nargs="?", default=DEFAULT_PDF_PATH, help="PDF 文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出文件路径")
    
    args = parser.parse_args()
    
    output_path = args.output or f"{OUTPUT_DIR}/{Path(args.pdf_path).stem}_mineru"
    
    parse_with_mineru(args.pdf_path, output_path)
