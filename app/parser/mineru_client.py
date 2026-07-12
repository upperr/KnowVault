"""
MinerU API 客户端模块
仅支持批量上传方式
参考：scripts/mineru_batch_parse.py
"""
import logging
import time
import requests
import zipfile
import io
from typing import Optional, Dict, Any, List
from pathlib import Path as PathLib

from app.config import MINERU_BASE_URL, MINERU_TOKEN, MINERU_TIMEOUT

logger = logging.getLogger(__name__)

# MinerU API 支持的文件扩展名
SUPPORTED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.ppt', '.pptx', 
    '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'
}


class MinerUClient:
    """MinerU API 客户端（仅批量上传）"""
    
    def __init__(
        self, 
        base_url: str = MINERU_BASE_URL,
        token: str = MINERU_TOKEN,
        timeout: int = MINERU_TIMEOUT
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        
        self.headers = {
            "Content-Type": "application/json",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        
        # 创建 session 用于连接池和重试
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "POST", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(f"MinerU 客户端已初始化，地址：{self.base_url}")
    
    def get_upload_urls(self, file_names: List[str], data_ids: List[str] = None, is_ocr: bool = False) -> Optional[Dict[str, Any]]:
        """
        申请文件上传链接（批量 API）
        
        Args:
            file_names: 文件名列表
            data_ids: 自定义数据 ID 列表（可选，用于关联业务数据）
            is_ocr: 是否启动 OCR 功能（默认 False）
        
        Returns:
            {
                "batch_id": "xxx",
                "file_urls": [{"name": "file1.pdf", "url": "https://..."}, ...]
            }
        """
        if data_ids is None:
            data_ids = [f"file_{i}" for i in range(len(file_names))]
        
        url = f"{self.base_url}/api/v4/file-urls/batch"
        data = {
            "files": [
                {"name": name, "data_id": data_id, "is_ocr": is_ocr}
                for name, data_id in zip(file_names, data_ids)
            ],
            "model_version": "vlm"
        }
        
        logger.info(f"正在申请 {len(file_names)} 个文件的上传链接...")
        response = self.session.post(url, headers=self.headers, json=data, timeout=60, proxies={"http": "", "https": ""})
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                logger.info(f"申请成功！batch_id: {result['data']['batch_id']}")
                return result["data"]
            else:
                logger.error(f"申请失败：{result.get('msg', '未知错误')}")
                return None
        else:
            logger.error(f"请求失败：HTTP {response.status_code} - {response.text}")
            return None
    
    def upload_file(self, upload_url: str, file_path: str) -> bool:
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
                # 使用 session 上传，禁用代理
                response = self.session.put(
                    upload_url,
                    data=f,
                    timeout=300,
                    proxies={'http': '', 'https': ''}  # 禁用代理
                )
                if response.status_code == 200:
                    logger.debug(f"上传成功：{PathLib(file_path).name}")
                    return True
                else:
                    logger.error(f"上传失败：HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"上传异常：{e}")
            return False
    
    def check_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        检查批量任务状态
        接口：GET /api/v4/extract-results/batch/{batch_id}
        
        Returns:
            任务状态信息
        """
        url = f"{self.base_url}/api/v4/extract-results/batch/{batch_id}"
        
        response = self.session.get(url, headers=self.headers, timeout=60, proxies={"http": "", "https": ""})
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                return result
            else:
                logger.error(f"查询失败：{result.get('msg', '未知错误')}")
                return None
        else:
            logger.error(f"查询状态失败：HTTP {response.status_code} - {response.text[:200]}")
            return None
    
    def download_md_content(self, full_zip_url: str) -> Optional[str]:
        """
        下载解析结果并提取 Markdown 内容
        
        Args:
            full_zip_url: 压缩包 URL
        
        Returns:
            Markdown 内容，失败返回 None
        """
        try:
            response = self.session.get(full_zip_url, timeout=60, proxies={"http": "", "https": ""})
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                    for name in zf.namelist():
                        if name.endswith('full.md'):
                            md_content = zf.read(name).decode('utf-8')
                            return md_content
                    logger.warning("压缩包中未找到 full.md")
                    return None
            else:
                logger.error(f"下载失败：HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"下载异常：{e}")
            return None
    
    def parse_files_batch(
        self,
        file_paths: List[str],
        wait_complete: bool = True,
        poll_interval: int = 30,
        is_ocr: bool = False,
        max_batch_size: int = 50
    ) -> Dict[str, Optional[str]]:
        """
        批量解析文件（使用批量 API）
        
        Args:
            file_paths: 文件路径列表
            wait_complete: 是否等待完成
            poll_interval: 轮询间隔（秒）
            is_ocr: 是否启用 OCR 功能
            max_batch_size: 单次最多处理文件数（MinerU 限制 50）
        
        Returns:
            {file_path: md_content 或 None}
        """
        results = {}
        
        # 过滤支持的文件类型
        supported_files = []
        for f in file_paths:
            ext = PathLib(f).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                supported_files.append(f)
            else:
                logger.warning(f"跳过不支持的格式：{f}")
        
        if not supported_files:
            logger.warning("未找到支持的文件")
            return {}
        
        logger.info(f"找到 {len(supported_files)} 个文件，分 {(len(supported_files) + max_batch_size - 1) // max_batch_size} 批次处理")
        
        # 分批处理
        for batch_start in range(0, len(supported_files), max_batch_size):
            batch_files = supported_files[batch_start:batch_start + max_batch_size]
            batch_num = batch_start // max_batch_size + 1
            total_batches = (len(supported_files) + max_batch_size - 1) // max_batch_size
            
            logger.info(f"处理批次 {batch_num}/{total_batches}")
            
            # 准备文件名和 data_id
            file_names = [PathLib(f).name for f in batch_files]
            data_ids = [PathLib(f).stem for f in batch_files]
            
            # 1. 申请上传 URL
            upload_data = self.get_upload_urls(file_names, data_ids, is_ocr=is_ocr)
            if not upload_data:
                logger.error("申请上传 URL 失败，跳过此批次")
                continue
            
            batch_id = upload_data["batch_id"]
            file_urls = upload_data["file_urls"]
            
            # 2. 上传文件
            logger.info(f"正在上传 {len(batch_files)} 个文件...")
            upload_success = []
            for i, (file_path, upload_url) in enumerate(zip(batch_files, file_urls), 1):
                logger.info(f"[{i}/{len(batch_files)}] 上传 {PathLib(file_path).name}...")
                if self.upload_file(upload_url, file_path):
                    logger.info(f"上传成功：{PathLib(file_path).name}")
                    upload_success.append({
                        "file": file_path,
                        "upload_url": upload_url
                    })
                else:
                    logger.error(f"上传失败：{PathLib(file_path).name}")
            
            if not upload_success:
                logger.error("所有文件上传失败，跳过此批次")
                continue
            
            logger.info(f"上传完成：{len(upload_success)}/{len(batch_files)} 成功")
            
            # 3. 等待并查询状态
            if wait_complete:
                logger.info(f"等待解析完成 (轮询间隔：{poll_interval}秒)...")
                while True:
                    time.sleep(poll_interval)
                    status = self.check_batch_status(batch_id)
                    
                    if status and status.get("data"):
                        extract_results = status["data"].get("extract_result", [])
                        
                        # 检查所有任务状态
                        all_done = True
                        processing_count = 0
                        
                        for file_result in extract_results:
                            state = file_result.get("state", "unknown")
                            file_name = file_result.get("file_name", "unknown")
                            
                            if state == "done":
                                continue
                            elif state == "failed":
                                err_msg = file_result.get("err_msg", "未知错误")
                                logger.error(f"❌ {file_name} 解析失败：{err_msg}")
                            elif state in ["waiting-file", "pending", "running", "converting"]:
                                all_done = False
                                processing_count += 1
                                progress = file_result.get("extract_progress", {})
                                if progress:
                                    extracted = progress.get("extracted_pages", 0)
                                    total = progress.get("total_pages", 0)
                                    logger.info(f"⏳ {file_name}: {extracted}/{total} 页")
                        
                        if all_done:
                            logger.info("✅ 批次解析完成！")
                            break
                        else:
                            logger.info(f"仍有 {processing_count} 个文件在解析中...")
            
            # 4. 下载结果
            logger.info("正在下载解析结果...")
            status = self.check_batch_status(batch_id)
            if status and status.get("data"):
                extract_results = status["data"].get("extract_result", [])
                
                for file_result in extract_results:
                    file_name = file_result.get("file_name", "")
                    state = file_result.get("state", "")
                    full_zip_url = file_result.get("full_zip_url", "")
                    
                    # 找到对应的文件路径
                    original_file = None
                    for f in batch_files:
                        if PathLib(f).name == file_name:
                            original_file = f
                            break
                    
                    if state == "done" and full_zip_url and original_file:
                        md_content = self.download_md_content(full_zip_url)
                        if md_content:
                            results[original_file] = md_content
                            logger.info(f"成功：{file_name}")
                        else:
                            results[original_file] = None
                            logger.error(f"下载失败：{file_name}")
                    elif state == "failed":
                        err_msg = file_result.get("err_msg", "未知错误")
                        results[original_file] = None
                        logger.error(f"解析失败 {file_name}: {err_msg}")
                    else:
                        results[original_file] = None
                        logger.warning(f"状态异常 {file_name}: {state}")
            else:
                logger.error("无法获取解析结果")
        
        return results
