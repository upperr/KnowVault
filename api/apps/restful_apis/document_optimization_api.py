#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing language and
#  limitations under the License.
#

"""
文档优化 API 路由
针对用户上传文档进行扩写、缩写、改写、结构化整理，贴合上传资料风格
"""

import json
import logging
from quart import Response
from api.apps import current_user, login_required
from api.db.joint_services.tenant_model_service import get_tenant_default_model_by_type
from api.db.services.llm_service import LLMBundle
from api.utils.api_utils import get_data_error_result, get_json_result, get_request_json, server_error_response
from common.constants import LLMType, RetCode
from rag.prompts.template import load_prompt

logger = logging.getLogger(__name__)


@manager.route("/document_optimization/stream", methods=["POST"])  # noqa: F821
@login_required
async def optimize_document_stream():
    """流式文档优化接口
    
    针对用户上传文档进行扩写、缩写、改写、结构化整理，贴合上传资料风格，
    实现基于私有资料的定制化内容生成。
    
    优化类型包括：
    1. 扩写（Expand）- 保持原文核心意思，添加更多细节、例子和解释
    2. 缩写/总结（Summarize）- 提取核心要点，语言简洁精炼
    3. 改写（Rewrite）- 优化表达方式和语言风格，提升可读性
    4. 结构化整理（Structure）- 添加清晰的标题层级，使用列表、表格组织内容
    5. 润色（Polish）- 修正语法错误，调整措辞，提升专业性
    6. 格式转换（Format）- 转换为 Markdown 格式，调整排版
    
    请求参数：
    - content: 原文内容（必填）
    - instruction: 优化要求（必填，如"扩写这段内容"、"精简到 200 字"等）
    
    返回：SSE 流式响应
    """
    try:
        req = await get_request_json()
        if not req:
            return get_data_error_result(message="请求体不能为空")
        
        content = req.get("content", "")
        instruction = req.get("instruction", "")
        
        # 参数验证
        if not content or not content.strip():
            return get_data_error_result(message="内容不能为空")
        
        if not instruction or not instruction.strip():
            return get_data_error_result(message="优化要求不能为空，请说明需要如何优化（如扩写、缩写、改写、结构化等）")
        
        logger.info(f"收到流式优化请求：instruction={instruction[:50]}..., user={current_user.id}")
        
        # 获取 LLM 模型
        try:
            chat_model_config = get_tenant_default_model_by_type(current_user.id, LLMType.CHAT)
            chat_mdl = LLMBundle(current_user.id, chat_model_config)
        except Exception as e:
            logger.error(f"获取 LLM 模型失败：{e}")
            return get_data_error_result(message=f"获取 LLM 模型失败：{str(e)}")
        
        # 加载提示词模板
        system_prompt = load_prompt("doc_optimization")
        
        # 构建用户提示词
        user_prompt = f"""原文内容：

{content[:8000]}

用户要求：

{instruction}

请按照上述要求对文档进行优化，直接输出优化后的内容（使用 Markdown 格式，标题前后、段落之间均不要有空行）："""
        
        # 流式生成
        async def generate():
            yield f"data: {json.dumps({'type': 'start', 'content': ''})}\n\n"
            
            full_content = ""
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                gen_conf = {
                    "temperature": 0.7,
                    "max_tokens": 4096,
                }
                
                async for chunk in chat_mdl.async_chat_streamly_delta(
                    system_prompt,
                    messages,
                    gen_conf
                ):
                    if isinstance(chunk, tuple) and len(chunk) >= 3:
                        _, _, text = chunk
                    else:
                        text = str(chunk)
                    
                    if text:
                        full_content += text
                        yield f"data: {json.dumps({'type': 'content', 'content': text})}\n\n"
                
                yield f"data: {json.dumps({'type': 'done', 'content': full_content})}\n\n"
                logger.info(f"流式优化完成，内容长度：{len(full_content)}")
                
            except Exception as e:
                logger.error(f"流式生成失败：{e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': f'优化失败：{str(e)}'})}\n\n"
        
        return Response(generate(), mimetype="text/event-stream")
        
    except Exception as e:
        logger.error(f"流式优化失败：{e}", exc_info=True)
        async def error_generate():
            yield f"data: {json.dumps({'type': 'error', 'message': f'请求失败：{str(e)}'})}\n\n"
        return Response(error_generate(), mimetype="text/event-stream")
