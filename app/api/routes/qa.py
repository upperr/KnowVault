"""
问答相关 API 路由
仅支持流式输出
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.retriever import get_retriever
from app.llm import get_llm_client
from app.config import RERANK_TOP_K
from app.prompts import QUICK_QA_SYSTEM_PROMPT, QUICK_QA_USER_PROMPT_TEMPLATE
import json
from fastapi.responses import StreamingResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class QAStreamRequest(BaseModel):
    question: str
    top_k: int = 5
    use_rerank: bool = True  # 是否启用 rerank 精排
    use_history: bool = False  # 兼容前端参数（暂未使用）


@router.post("/stream")
async def ask_question_stream(request: QAStreamRequest):
    """流式问答接口
    
    召回策略（知识问答模式）：
    1. 对用户问题向量化
    2. 向量相似度粗排（获取 top_k * RETRIEVE_MULTIPLIER 候选）
    3. Reranker 模型精排（qwen3-rerank）
    4. LLM 基于精排结果进行最终决策并流式生成回复
    5. 至多召回 1 条最相关知识（top_k=1），因为问答一般只需回答一个具体知识点
    """
    try:
        logger.info(f"收到流式问答请求：question={request.question[:50]}..., top_k={request.top_k}, use_rerank={request.use_rerank}")
        
        retriever = get_retriever(top_k=request.top_k)
        
        # 知识问答模式：仅召回 top 1 最相关知识
        raw_chunks = await retriever.retrieve(request.question, top_k=request.top_k, use_rerank=request.use_rerank, mode="qa")
        
        logger.info(f"检索到 {len(raw_chunks)} 个文档片段（精排后）")
        
        if not raw_chunks:
            logger.warning("未找到相关文档")
            async def empty_generate():
                yield f"data: {json.dumps({'type': 'error', 'message': '未找到相关文档'})}\n\n"
            return StreamingResponse(empty_generate(), media_type="text/event-stream")
        
        # 构建上下文（包含来源和 Rerank 分数）
        context_parts = []
        for i, chunk in enumerate(raw_chunks[:5]):
            source = chunk.get('file_name', '未知文档')
            score = chunk.get('rerank_score', 0.0)
            content = chunk.get('content', '')
            context_parts.append(f"[文档{i+1}] 来源：{source} (相关性分数：{score:.3f})\n{content}")
        
        context = "\n\n".join(context_parts)
        
        # 使用 prompts 中的提示词和 config 中的超参数
        system_prompt = QUICK_QA_SYSTEM_PROMPT
        user_prompt = QUICK_QA_USER_PROMPT_TEMPLATE.format(context=context, question=request.question)
        
        logger.info(f"开始流式生成，上下文长度：{len(context)} 字符")
        
        async def generate():
            client = get_llm_client()
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            full_answer = ""
            try:
                async for chunk in client.stream_complete(
                    user_prompt, 
                    system_prompt, 
                    temperature=0.3, 
                    max_tokens=2048
                ):
                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'answer', 'content': chunk})}\n\n"
            except Exception as e:
                logger.error(f"流式生成失败：{e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': f'生成失败：{str(e)}'})}\n\n"
                return
            
            # 去重后的来源列表
            sources = list(set([chunk.get('file_name', '未知文档') for chunk in raw_chunks[:5]]))
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'answer': full_answer})}\n\n"
            
            logger.info(f"流式问答完成，来源：{sources}")
        
        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"流式问答失败：{e}", exc_info=True)
        async def error_generate():
            yield f"data: {json.dumps({'type': 'error', 'message': f'请求失败：{str(e)}'})}\n\n"
        return StreamingResponse(error_generate(), media_type="text/event-stream")
