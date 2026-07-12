"""
文档创作相关 API 路由
仅支持流式输出
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.retriever import get_retriever
from app.llm import get_llm_client
from app.prompts import build_creation_messages
from app.config import RETRIEVE_TOP_N
import json
from fastapi.responses import StreamingResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateRequest(BaseModel):
    requirement: str
    title: Optional[str] = None
    original_text: Optional[str] = None


@router.post("/stream")
async def create_content_stream(request: CreateRequest):
    """流式文档创作
    
    召回策略（文档生成模式）：
    1. 直接使用基于向量匹配的粗排召回结果
    2. 全部交给大模型用于文档生成
    3. 提示 LLM 仅使用与待生成文档相关的知识，无需全部使用
    """
    try:
        logger.info(f"收到流式创作请求：requirement={request.requirement[:50]}...")
        
        if not request.requirement.strip():
            raise HTTPException(status_code=400, detail="创作要求不能为空")
        
        # 文档生成模式：使用向量粗排结果，不使用 rerank
        # 使用 RETRIEVE_TOP_N 配置（默认 20 条片段），召回足够素材供 LLM 筛选
        retriever = get_retriever()
        search_text = request.original_text or request.requirement
        raw_chunks = await retriever.retrieve(search_text, top_k=RETRIEVE_TOP_N, use_rerank=False, mode="generation")
        
        logger.info(f"检索到 {len(raw_chunks)} 个文档片段（粗排 top_n={RETRIEVE_TOP_N}）")
        
        # 构建上下文（使用全部召回片段）
        context = "\n\n".join([f"[素材{i+1}]\n{chunk.get('content', '')}" for i, chunk in enumerate(raw_chunks)]) if raw_chunks else "无额外素材"
        
        # 构建提示词
        messages = build_creation_messages(
            context=context,
            requirement=request.requirement,
            title=request.title or "",
            original_text=request.original_text or "",
        )
        system_prompt = messages[0]["content"]
        user_prompt = messages[1]["content"]
        
        async def generate():
            client = get_llm_client()
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            full_content = ""
            try:
                async for chunk in client.stream_complete(user_prompt, system_prompt):
                    full_content += chunk
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            except Exception as e:
                logger.error(f"流式生成失败：{e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': f'生成失败：{str(e)}'})}\n\n"
                return
            
            sources = [chunk.get('file_name', '未知文档') for chunk in raw_chunks]
            yield f"data: {json.dumps({'type': 'done', 'content': full_content, 'sources': sources})}\n\n"
            
            logger.info(f"流式创作完成，内容长度：{len(full_content)}，素材来源：{len(sources)} 个文档")
        
        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"流式创作失败：{e}", exc_info=True)
        async def error_generate():
            yield f"data: {json.dumps({'type': 'error', 'message': f'请求失败：{str(e)}'})}\n\n"
        return StreamingResponse(error_generate(), media_type="text/event-stream")
