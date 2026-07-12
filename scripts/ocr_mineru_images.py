#!/usr/bin/env python3
"""
MinerU 输出图片 OCR 处理脚本

功能：
1. 解析 MinerU 输出的 zip 文件
2. 对其中所有图片进行 OCR 识别
3. 将 OCR 结果填入 content_list.json 的 content 字段
4. 重新生成 full.md 文件

使用 OpenAI 兼容 API 调用 qwen-vl-plus 模型进行 OCR
"""
import sys
import os
import json
import base64
import zipfile
import io
import tempfile
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OCR_MODEL
from openai import OpenAI


def image_to_base64(image_path: str) -> str:
    """将图片文件转为 base64 字符串"""
    with open(image_path, 'rb') as f:
        img_data = f.read()
    return base64.b64encode(img_data).decode('utf-8')


def ocr_image(client: OpenAI, image_base64: str, model: str = OCR_MODEL) -> str:
    """
    使用多模态模型进行 OCR 识别
    
    Args:
        client: OpenAI 客户端
        image_base64: 图片的 base64 编码
        model: OCR 模型名称
    
    Returns:
        识别的文字内容
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的 OCR 文字识别助手。你的任务是识别图片中的所有文字内容。\n\n要求：\n1. 准确识别图片中的文字，包括中文、英文、数字和符号\n2. 保持原有的段落结构和格式\n3. 如果是表格，按行列顺序输出文字内容\n4. 如果是流程图或架构图，描述图中的关键信息和连接关系"
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
    except Exception as e:
        print(f"OCR 识别失败：{e}")
        return ""


def process_mineru_output(
    zip_path: str,
    output_dir: str = None,
    skip_existing: bool = True,
    cleanup: bool = True
) -> Dict[str, Any]:
    """
    处理 MinerU 输出，对图片进行 OCR
    
    Args:
        zip_path: MinerU 输出的 zip 文件路径（格式：xxx_mineru.zip）
        output_dir: 输出目录（默认与 zip 同目录）
        skip_existing: 是否跳过已处理的文件
        cleanup: 是否删除中间文件（zip、json 等，仅保留 md）
    
    Returns:
        处理结果统计
    """
    print("=" * 60)
    print("MinerU 输出图片 OCR 处理")
    print("=" * 60)
    print(f"输入文件：{zip_path}")
    print()
    
    zip_path = Path(zip_path)
    if output_dir is None:
        output_dir = zip_path.parent
    else:
        output_dir = Path(output_dir)
    
    # 从 zip 文件名提取原文件名
    # 格式：原文件名_mineru.zip -> 原文件名
    # 例如：数字化建运专业协同_mineru.zip -> 数字化建运专业协同
    zip_stem = zip_path.stem  # 不含 .zip 的文件名
    if zip_stem.endswith("_mineru"):
        original_name = zip_stem[:-7]  # 去掉 "_mineru"
    else:
        original_name = zip_stem
    
    # 输出文件命名：原文件名。原文件扩展名.md
    # 例如：数字化建运专业协同.pdf.md
    output_md_name = f"{original_name}.pdf.md"
    
    # 初始化 OCR 客户端
    client = OpenAI(
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
    )
    print(f"OCR 模型：{OCR_MODEL}")
    print(f"API 地址：{OPENAI_BASE_URL}")
    print()
    
    # 解压 zip 文件到临时目录
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"解压 zip 文件到临时目录：{tmp_dir}")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_dir)
        
        # 查找 content_list.json 文件
        content_list_file = None
        for f in Path(tmp_dir).glob("*_content_list.json"):
            content_list_file = f
            break
        
        if not content_list_file:
            print("错误：未找到 content_list.json 文件")
            return {"error": "content_list.json not found"}
        
        print(f"找到 content_list.json: {content_list_file.name}")
        
        # 读取 content_list.json
        with open(content_list_file, 'r', encoding='utf-8') as f:
            content_list = json.load(f)
        
        # 统计图片数量
        image_items = [
            item for item in content_list
            if isinstance(item, dict) and item.get('type') == 'image'
        ]
        
        print(f"\n找到 {len(image_items)} 个图片项")
        print(f"总内容项数：{len(content_list)}")
        print()
        
        # 对每个图片进行 OCR
        results = {
            "total_images": len(image_items),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }
        
        for i, img_item in enumerate(image_items, 1):
            img_path_rel = img_item.get('img_path', '')
            img_path = Path(tmp_dir) / img_path_rel
            
            print(f"[{i}/{len(image_items)}] 处理 {img_path_rel}...", end=" ")
            
            # 检查是否已有 OCR 结果
            existing_content = img_item.get('content', '')
            if existing_content and skip_existing:
                print("已存在 OCR 结果，跳过")
                results["skipped"] += 1
                results["details"].append({
                    "image": img_path_rel,
                    "status": "skipped",
                    "content_length": len(existing_content)
                })
                continue
            
            # 检查图片文件是否存在
            if not img_path.exists():
                print(f"图片文件不存在")
                results["failed"] += 1
                results["details"].append({
                    "image": img_path_rel,
                    "status": "file_not_found"
                })
                continue
            
            # 进行 OCR 识别
            img_base64 = image_to_base64(str(img_path))
            ocr_text = ocr_image(client, img_base64)
            
            if ocr_text:
                # 更新 content 字段
                img_item['content'] = ocr_text
                print(f"成功 ({len(ocr_text)} 字符)")
                results["processed"] += 1
                results["details"].append({
                    "image": img_path_rel,
                    "status": "success",
                    "content_length": len(ocr_text)
                })
            else:
                print("OCR 失败")
                results["failed"] += 1
                results["details"].append({
                    "image": img_path_rel,
                    "status": "ocr_failed"
                })
        
        # 保存更新后的 content_list.json（临时文件，后续删除）
        output_content_list = output_dir / f"{zip_path.stem}_ocr.json"
        with open(output_content_list, 'w', encoding='utf-8') as f:
            json.dump(content_list, f, ensure_ascii=False, indent=2)
        
        # 重新生成 full.md
        print("\n正在重新生成 full.md...")
        md_content = generate_markdown(content_list)
        
        # 输出文件命名：原文件名。原文件扩展名.md
        output_md = output_dir / output_md_name
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"已保存：{output_md}")
        
        # 打包新的 zip 文件（临时文件，后续删除）
        output_zip = output_dir / f"{zip_path.stem}_ocr.zip"
        if not cleanup:
            print(f"\n正在打包新的 zip 文件：{output_zip}")
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in Path(tmp_dir).rglob('*'):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(tmp_dir)
                        # 更新 content_list.json
                        if file_path.name == content_list_file.name:
                            zf.writestr(str(arc_name), json.dumps(content_list, ensure_ascii=False, indent=2))
                        else:
                            zf.write(file_path, arc_name)
            print(f"已保存：{output_zip}")
        else:
            print("\n[清理模式] 跳过打包 zip 文件")
    
    # 清理中间文件
    if cleanup:
        print("\n正在清理中间文件...")
        files_to_delete = [
            output_dir / f"{zip_path.stem}_ocr.json",
            output_dir / f"{zip_path.stem}_ocr.zip",
            output_dir / f"{zip_path.stem}_ocr.md",  # 旧的命名格式
            output_dir / f"{zip_path.stem}.md",  # 可能的其他格式
        ]
        deleted_count = 0
        for f in files_to_delete:
            if f.exists() and f != output_md:  # 不删除最终输出文件
                try:
                    f.unlink()
                    print(f"  已删除：{f.name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  删除失败 {f.name}: {e}")
        print(f"共删除 {deleted_count} 个中间文件")
    
    # 打印统计
    print("\n" + "=" * 60)
    print("处理完成")
    print("=" * 60)
    print(f"总图片数：{results['total_images']}")
    print(f"成功处理：{results['processed']} 个")
    print(f"已跳过：{results['skipped']} 个")
    print(f"失败：{results['failed']} 个")
    
    return results


def generate_markdown(content_list: List[Dict]) -> str:
    """
    根据 content_list 生成 Markdown 内容
    
    Args:
        content_list: 内容列表
    
    Returns:
        Markdown 文本
    """
    md_parts = []
    
    for item in content_list:
        if not isinstance(item, dict):
            continue
        
        item_type = item.get('type', '')
        
        if item_type == 'text':
            text = item.get('text', '')
            level = item.get('text_level', 0)
            
            if text:
                if level > 0:
                    # 添加标题标记
                    prefix = '#' * min(level, 6)
                    md_parts.append(f"{prefix} {text}")
                else:
                    md_parts.append(text)
        
        elif item_type == 'image':
            # 图片项，插入 OCR 识别的文字
            ocr_content = item.get('content', '')
            if ocr_content:
                md_parts.append("")
                md_parts.append("**[图片内容]**")
                md_parts.append(ocr_content)
                md_parts.append("")
        
        elif item_type == 'table':
            # 表格项
            table_md = item.get('markdown', '')
            if table_md:
                md_parts.append("")
                md_parts.append(table_md)
                md_parts.append("")
        
        elif item_type == 'equation':
            # 公式项
            latex = item.get('latex', '')
            if latex:
                md_parts.append(f"$${latex}$$")
    
    return "\n\n".join(md_parts)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MinerU 输出图片 OCR 处理")
    parser.add_argument("zip_path", nargs="?", help="MinerU 输出的 zip 文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出目录")
    parser.add_argument("--no-skip", action="store_true", help="重新处理已有 OCR 结果的文件")
    parser.add_argument("--no-cleanup", action="store_true", help="保留中间文件（json、zip 等）")
    
    args = parser.parse_args()
    
    if not args.zip_path:
        # 默认处理最新的输出文件
        output_dir = Path("/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/output")
        zip_files = list(output_dir.glob("*_mineru.zip"))
        if zip_files:
            zip_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            args.zip_path = str(zip_files[0])
            print(f"使用最新的 zip 文件：{args.zip_path}")
        else:
            print("错误：未找到 MinerU 输出的 zip 文件")
            print("用法：python ocr_mineru_images.py <zip 文件路径>")
            sys.exit(1)
    
    results = process_mineru_output(
        args.zip_path,
        args.output,
        skip_existing=not args.no_skip,
        cleanup=not args.no_cleanup
    )
    
    if results.get("error"):
        sys.exit(1)
