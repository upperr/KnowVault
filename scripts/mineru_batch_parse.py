#!/usr/bin/env python3
"""
MinerU 批量文件解析脚本
参考：mineru_api_batch.py

流程：
1. 调用 /api/v4/file-urls/batch 获取上传 URL
2. 上传文件到这些 URL
3. 系统自动解析，轮询任务状态
4. 下载解析结果
"""
import sys
import os
import time
import requests
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import MINERU_TOKEN, MINERU_TIMEOUT

# 配置
DEFAULT_INPUT_DIR = "/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/documents"
DEFAULT_OUTPUT_DIR = "/Users/yanghanxuan/Documents/工作/入职/国网新员工培训/AI+微创新/创客营/code/data/output"
MINERU_BASE_URL = "https://mineru.net"
MAX_BATCH_SIZE = 50  # 单次最多 50 个文件

# MinerU 支持的文件扩展名
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}


def get_upload_urls(
    file_names: List[str], 
    data_ids: List[str] = None,
    is_ocr: bool = False
) -> Dict[str, Any]:
    """
    申请文件上传链接
    
    Args:
        file_names: 文件名列表
        data_ids: 自定义数据 ID 列表（可选，用于关联业务数据）
        is_ocr: 是否启动 OCR 功能（默认 False，仅对 pipeline、vlm 模型有效）
    
    Returns:
        {
            "batch_id": "xxx",
            "file_urls": [
                {"name": "file1.pdf", "url": "https://..."},
                ...
            ]
        }
    """
    if data_ids is None:
        data_ids = [f"file_{i}" for i in range(len(file_names))]
    
    url = f"{MINERU_BASE_URL}/api/v4/file-urls/batch"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINERU_TOKEN}"
    }
    data = {
        "files": [
            {"name": name, "data_id": data_id, "is_ocr": is_ocr}
            for name, data_id in zip(file_names, data_ids)
        ],
        "model_version": "vlm"  # 使用 VLM 模型进行版面分析
    }
    
    print(f"正在申请 {len(file_names)} 个文件的上传链接...")
    print(f"OCR 功能：{'已启用' if is_ocr else '未启用'}")
    response = requests.post(url, headers=headers, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 0:
            print(f"申请成功！batch_id: {result['data']['batch_id']}")
            return result["data"]
        else:
            print(f"申请失败：{result.get('msg', '未知错误')}")
            return None
    else:
        print(f"请求失败：HTTP {response.status_code} - {response.text}")
        return None


def upload_file(upload_url: str, file_path: str) -> bool:
    """
    上传单个文件到 MinerU
    
    Args:
        upload_url: 上传 URL
        file_path: 本地文件路径
    
    Returns:
        上传是否成功
    """
    try:
        with open(file_path, 'rb') as f:
            response = requests.put(upload_url, data=f, timeout=300)
            if response.status_code == 200:
                return True
            else:
                print(f"上传失败：HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"上传异常：{e}")
        return False


def check_batch_status(batch_id: str) -> Dict[str, Any]:
    """
    检查批量任务状态
    接口：GET /api/v4/extract-results/batch/{batch_id}
    
    Returns:
        任务状态信息
    """
    url = f"{MINERU_BASE_URL}/api/v4/extract-results/batch/{batch_id}"
    headers = {
        "Authorization": f"Bearer {MINERU_TOKEN}"
    }
    
    response = requests.get(url, headers=headers, timeout=60)
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 0:
            return result
        else:
            print(f"查询失败：{result.get('msg', '未知错误')}")
            return None
    else:
        print(f"查询状态失败：HTTP {response.status_code} - {response.text[:200]}")
        return None


def download_result(file_url: str, output_path: str) -> bool:
    """
    下载解析结果（Markdown 格式）
    
    Args:
        file_url: 结果文件 URL
        output_path: 保存路径
    
    Returns:
        下载是否成功
    """
    try:
        response = requests.get(file_url, timeout=60)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            return True
        else:
            print(f"下载失败：HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"下载异常：{e}")
        return False


def batch_parse_files(
    input_dir: str,
    output_dir: str,
    wait_complete: bool = True,
    poll_interval: int = 30,
    is_ocr: bool = False
) -> List[Dict[str, Any]]:
    """
    批量解析文件
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        wait_complete: 是否等待完成
        poll_interval: 轮询间隔（秒）
        is_ocr: 是否启用 OCR 功能（默认 False，仅对 pipeline、vlm 模型有效）
    
    Returns:
        处理结果列表
    """
    # 扫描所有文件
    input_path = Path(input_dir)
    all_files = [f for f in input_path.iterdir() if f.is_file()]
    
    # 过滤支持的文件类型
    supported_files = []
    skipped_files = []
    
    for f in all_files:
        if f.suffix.lower() in SUPPORTED_EXTENSIONS:
            supported_files.append(f)
        else:
            skipped_files.append(f)
    
    # 报告文件过滤结果
    print(f"扫描目录：{input_dir}")
    print(f"找到文件总数：{len(all_files)}")
    print(f"支持的文件：{len(supported_files)} 个")
    if skipped_files:
        print(f"跳过的文件：{len(skipped_files)} 个（不支持的格式）")
        for f in skipped_files:
            print(f"  - {f.name} (扩展名：{f.suffix.lower()})")
    print()
    
    if not supported_files:
        print(f"在 {input_dir} 目录下未找到支持的文件")
        print(f"支持的格式：{', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        return []
    
    print(f"找到 {len(supported_files)} 个文件:")
    for f in supported_files:
        print(f"  - {f.name}")
    print()
    
    # 分批处理（每批最多 50 个）
    results = []
    for batch_start in range(0, len(supported_files), MAX_BATCH_SIZE):
        batch_files = supported_files[batch_start:batch_start + MAX_BATCH_SIZE]
        batch_num = batch_start // MAX_BATCH_SIZE + 1
        total_batches = (len(supported_files) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
        
        print("=" * 60)
        print(f"处理批次 {batch_num}/{total_batches}")
        print("=" * 60)
        
        # 准备文件名和 data_id
        file_names = [f.name for f in batch_files]
        data_ids = [f.stem for f in batch_files]
        
        # 1. 申请上传 URL
        upload_data = get_upload_urls(file_names, data_ids, is_ocr=is_ocr)
        if not upload_data:
            print("申请上传 URL 失败，跳过此批次")
            continue
        
        batch_id = upload_data["batch_id"]
        file_urls = upload_data["file_urls"]  # 这是字符串列表 ["https://...", ...]
        
        # 2. 上传文件
        print(f"\n正在上传 {len(batch_files)} 个文件...")
        upload_success = []
        for i, (file_path, upload_url) in enumerate(zip(batch_files, file_urls), 1):
            print(f"[{i}/{len(batch_files)}] 上传 {file_path.name}...", end=" ")
            if upload_file(upload_url, str(file_path)):
                print("成功")
                upload_success.append({
                    "file": file_path,
                    "upload_url": upload_url
                })
            else:
                print("失败")
        
        if not upload_success:
            print("所有文件上传失败，跳过此批次")
            continue
        
        print(f"\n上传完成：{len(upload_success)}/{len(batch_files)} 成功")
        
        # 3. 等待并查询状态
        if wait_complete:
            print(f"\n等待解析完成 (轮询间隔：{poll_interval}秒)...")
            while True:
                time.sleep(poll_interval)
                status = check_batch_status(batch_id)
                if status and status.get("data"):
                    extract_results = status["data"].get("extract_result", [])
                    
                    # 检查所有任务状态
                    all_done = True
                    any_failed = False
                    processing_count = 0
                    
                    for file_result in extract_results:
                        state = file_result.get("state", "unknown")
                        file_name = file_result.get("file_name", "unknown")
                        
                        if state == "done":
                            continue
                        elif state == "failed":
                            any_failed = True
                            err_msg = file_result.get("err_msg", "未知错误")
                            print(f"  ❌ {file_name} 解析失败：{err_msg}")
                        elif state in ["waiting-file", "pending", "running", "converting"]:
                            all_done = False
                            processing_count += 1
                            # 显示进度
                            progress = file_result.get("extract_progress", {})
                            if progress:
                                extracted = progress.get("extracted_pages", 0)
                                total = progress.get("total_pages", 0)
                                print(f"  ⏳ {file_name}: {extracted}/{total} 页")
                            else:
                                print(f"  ⏳ {file_name}: {state}")
                    
                    if all_done or any_failed:
                        if all_done and not any_failed:
                            print("✅ 批次解析完成！")
                        elif any_failed:
                            print("⚠️ 部分文件解析失败")
                        break
                    else:
                        print(f"  仍有 {processing_count} 个文件在解析中...")
        
        # 4. 下载结果
        print("\n正在下载解析结果...")
        status = check_batch_status(batch_id)
        if status and status.get("data"):
            extract_results = status["data"].get("extract_result", [])
            
            for file_result in extract_results:
                file_name = file_result.get("file_name", "")
                state = file_result.get("state", "")
                full_zip_url = file_result.get("full_zip_url", "")
                
                if state == "done" and full_zip_url:
                    file_stem = Path(file_name).stem
                    output_path = os.path.join(output_dir, f"{file_stem}_mineru.md")
                    zip_path = os.path.join(output_dir, f"{file_stem}_mineru.zip")
                    
                    # 下载压缩包
                    print(f"  下载 {file_name}...", end=" ")
                    try:
                        zip_response = requests.get(full_zip_url, timeout=60)
                        if zip_response.status_code == 200:
                            # 保存 zip 文件
                            with open(zip_path, 'wb') as f:
                                f.write(zip_response.content)
                            
                            # 解压并提取 full.md
                            import zipfile
                            with zipfile.ZipFile(zip_path, 'r') as zf:
                                # 查找 full.md 文件
                                md_file = None
                                for name in zf.namelist():
                                    if name.endswith('full.md'):
                                        md_file = name
                                        break
                                
                                if md_file:
                                    md_content = zf.read(md_file).decode('utf-8')
                                    with open(output_path, 'w', encoding='utf-8') as f:
                                        f.write(md_content)
                                    print(f"成功 -> {output_path}")
                                    results.append({
                                        "file": file_name,
                                        "status": "success",
                                        "output": output_path
                                    })
                                else:
                                    print(f"压缩包中未找到 full.md")
                                    results.append({
                                        "file": file_name,
                                        "status": "no_md_file",
                                        "output": None
                                    })
                        else:
                            print(f"下载失败：HTTP {zip_response.status_code}")
                            results.append({
                                "file": file_name,
                                "status": "download_failed",
                                "output": None
                            })
                    except Exception as e:
                        print(f"异常：{e}")
                        results.append({
                            "file": file_name,
                            "status": "exception",
                            "output": None
                        })
                elif state == "failed":
                    err_msg = file_result.get("err_msg", "未知错误")
                    print(f"  ❌ {file_name} 解析失败：{err_msg}")
                    results.append({
                        "file": file_name,
                        "status": "failed",
                        "output": None,
                        "error": err_msg
                    })
                else:
                    print(f"  ⏳ {file_name} 状态：{state}")
                    results.append({
                        "file": file_name,
                        "status": state,
                        "output": None
                    })
        else:
            print("无法获取解析结果")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MinerU 批量文件解析")
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT_DIR, help="输入目录")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_DIR, help="输出目录")
    parser.add_argument("--no-wait", action="store_true", help="上传后不等待完成")
    parser.add_argument("--interval", type=int, default=30, help="轮询间隔（秒）")
    parser.add_argument("--ocr", action="store_true", help="启用 OCR 功能（适用于扫描版 PDF、图片中的文字识别）")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MinerU 批量文件解析")
    print("=" * 60)
    print(f"输入目录：{args.input}")
    print(f"输出目录：{args.output}")
    print(f"Token: {MINERU_TOKEN[:20]}..." if len(MINERU_TOKEN) > 20 else f"Token: {MINERU_TOKEN}")
    print(f"支持的格式：{', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    print(f"OCR 功能：{'已启用' if args.ocr else '未启用'}")
    print()
    
    results = batch_parse_files(
        input_dir=args.input,
        output_dir=args.output,
        wait_complete=not args.no_wait,
        poll_interval=args.interval,
        is_ocr=args.ocr
    )
    
    print()
    print("=" * 60)
    print("处理完成")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] in ["failed", "download_failed", "exception", "no_md_file"])
    pending_count = len(results) - success_count - failed_count
    
    print(f"总计：{len(results)} 个文件")
    print(f"成功：{success_count} 个")
    print(f"失败：{failed_count} 个")
    if pending_count > 0:
        print(f"等待中：{pending_count} 个")
    
    if results:
        print("\n结果列表:")
        for r in results:
            if r["status"] == "success":
                print(f"  ✅ {r['file']} -> {r.get('output', 'N/A')}")
            elif r["status"] == "failed":
                print(f"  ❌ {r['file']} -> 解析失败：{r.get('error', '未知错误')}")
            elif r["status"] in ["download_failed", "exception", "no_md_file"]:
                print(f"  ❌ {r['file']} -> {r['status']}")
            else:
                print(f"  ⏳ {r['file']} -> 状态：{r['status']}")
    
    print()
