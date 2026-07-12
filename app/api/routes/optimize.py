"""
文档优化相关 API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.llm import get_llm_client
from app.prompts.optimize import build_optimize_messages
import json
from fastapi.responses import StreamingResponse

router = APIRouter()


class OptimizeRequest(BaseModel):
    content: str
    instruction: Optional[str] = ""


@router.post("/stream")
async def optimize_stream(request: OptimizeRequest):
    """流式文档优化接口
    
    优化类型包括：扩写、缩写、改写、结构化整理、润色、格式转换等
    
    Args:
        content: 原文内容（必填）
        instruction: 优化要求（必填，如"扩写这段内容"、"精简到 200 字"等）
    """
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    
    if not request.instruction.strip():
        raise HTTPException(status_code=400, detail="优化要求不能为空，请说明需要如何优化（如扩写、缩写、改写、结构化等）")
    
    # 构建优化提示词
    messages = build_optimize_messages(content=request.content, instruction=request.instruction)
    
    async def generate():
        yield f"data: {json.dumps({'type': 'start'})}\n\n"
        
        client = get_llm_client()
        full_content = ""
        try:
            async for chunk in client.stream_complete(
                prompt=messages[1]["content"],
                system_prompt=messages[0]["content"],
                temperature=0.7,
                max_tokens=4096,
            ):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'优化失败：{str(e)}'})}\n\n"
            return
        
        yield f"data: {json.dumps({'type': 'done', 'content': full_content})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
