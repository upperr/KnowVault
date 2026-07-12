"""
内容提取模块
从 MinerU API 返回结果中提取文本、图片、表格等内容
"""
import logging
import base64
import zipfile
import io
from typing import Dict, Any, List

from openai import OpenAI
from app.config import (
    OCR_MODEL, OCR_API_KEY, OCR_BASE_URL,
    TABLE_MODEL, TABLE_API_KEY, TABLE_BASE_URL,
)
from app.prompts import OCR_SYSTEM_PROMPT, TABLE_TO_MARKDOWN_PROMPT

logger = logging.getLogger(__name__)


class ContentExtractor:
    """内容提取器"""
    
    def __init__(self):
        # 初始化 OCR 客户端
        self.ocr_client = OpenAI(
            base_url=OCR_BASE_URL,
            api_key=OCR_API_KEY,
        )
        # 初始化表格解析客户端
        self.table_client = OpenAI(
            base_url=TABLE_BASE_URL,
            api_key=TABLE_API_KEY,
        )
    
    def extract(self, result: Dict, file_path: str) -> Dict[str, Any]:
        """
        从 MinerU API 返回结果中提取内容
        
        Returns:
            {
                "text_blocks": [{"content": str, "page": int}, ...],
                "images": [{"image_data": bytes, "ocr_text": str, "page": int}, ...],
                "tables": [{"markdown": str, "page": int}, ...],
                "full_text": str
            }
        """
        text_blocks = []
        images = []
        tables = []
        
        try:
            # 格式 1: 直接返回 Markdown
            if "md_content" in result:
                md_content = result["md_content"]
                paragraphs = [
                    p.strip() 
                    for p in md_content.split("\n\n") 
                    if p.strip()
                ]
                for para in paragraphs:
                    text_blocks.append({"content": para, "page": 0})
            
            # 格式 2: 返回 pages 结构
            if "pages" in result:
                for page_num, page_data in enumerate(result["pages"], 1):
                    # 提取文本块
                    if "text_blocks" in page_data:
                        for block in page_data["text_blocks"]:
                            text = block.get("text", "") or block.get("content", "")
                            if text and text.strip():
                                text_blocks.append({"content": text, "page": page_num})
                    
                    # 提取图片
                    if "images" in page_data:
                        for img_info in page_data["images"]:
                            img_data = img_info.get("image_data", "") or img_info.get("data", "")
                            if img_data:
                                ocr_text = self._ocr_image_from_base64(img_data)
                                images.append({
                                    "image_data": img_data,
                                    "ocr_text": ocr_text,
                                    "page": page_num
                                })
                    
                    # 提取表格
                    if "tables" in page_data:
                        for table_info in page_data["tables"]:
                            if "markdown" in table_info:
                                tables.append({
                                    "markdown": table_info["markdown"],
                                    "page": page_num
                                })
                            elif "image_data" in table_info or "data" in table_info:
                                table_img_data = (
                                    table_info.get("image_data", "") or 
                                    table_info.get("data", "")
                                )
                                if table_img_data:
                                    markdown = self._parse_table_from_base64(table_img_data)
                                    tables.append({
                                        "markdown": markdown,
                                        "page": page_num
                                    })
            
            # 格式 3: 返回 zip 文件（base64 编码）
            if "zip_data" in result:
                zip_data = base64.b64decode(result["zip_data"])
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    for name in zf.namelist():
                        if name.endswith(".md"):
                            md_content = zf.read(name).decode("utf-8")
                            paragraphs = [
                                p.strip() 
                                for p in md_content.split("\n\n") 
                                if p.strip()
                            ]
                            for para in paragraphs:
                                text_blocks.append({"content": para, "page": 0})
            
            # 合并完整文本
            full_text = self._merge_content(text_blocks, images, tables)
            
            logger.info(
                f"内容提取完成：{len(text_blocks)} 文本块，"
                f"{len(images)} 图片，{len(tables)} 表格"
            )
            
            return {
                "text_blocks": text_blocks,
                "images": images,
                "tables": tables,
                "full_text": full_text
            }
            
        except Exception as e:
            logger.error(f"内容提取失败：{e}")
            return {"text_blocks": [], "images": [], "tables": [], "full_text": ""}
    
    def _ocr_image_from_base64(self, image_data: str) -> str:
        """使用 OCR 模型识别图片中的文字"""
        try:
            mime_type = "image/jpeg"
            
            response = self.ocr_client.chat.completions.create(
                model=OCR_MODEL,
                messages=[
                    {"role": "system", "content": OCR_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                timeout=60,
            )
            
            ocr_text = response.choices[0].message.content or ""
            logger.info(f"OCR 识别完成，共 {len(ocr_text)} 字符")
            return ocr_text
            
        except Exception as e:
            logger.error(f"OCR 识别失败：{e}")
            return ""
    
    def _parse_table_from_base64(self, image_data: str) -> str:
        """使用多模态大模型将表格图片转为 Markdown"""
        try:
            mime_type = "image/jpeg"
            
            response = self.table_client.chat.completions.create(
                model=TABLE_MODEL,
                messages=[
                    {"role": "system", "content": TABLE_TO_MARKDOWN_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=3000,
                timeout=60,
            )
            
            markdown = response.choices[0].message.content or ""
            logger.info("表格解析完成")
            return markdown
            
        except Exception as e:
            logger.error(f"表格解析失败：{e}")
            return ""
    
    def _merge_content(
        self, 
        text_blocks: List, 
        images: List, 
        tables: List
    ) -> str:
        """合并所有内容为一个完整文本"""
        parts = []
        
        # 添加文本块
        for block in text_blocks:
            if block.get("content"):
                parts.append(block["content"])
        
        # 添加图片 OCR 文本
        for img in images:
            if img.get("ocr_text"):
                parts.append(f"[图片内容] {img['ocr_text']}")
        
        # 添加表格 Markdown
        for table in tables:
            if table.get("markdown"):
                parts.append(table["markdown"])
        
        return "\n\n".join(parts)
