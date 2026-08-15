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
文档创作 API 路由
基于本地知识库文档辅助用户撰写报告、总结、方案、笔记、摘要等内容
"""

import json
import logging
from quart import Response
from api.apps import current_user, login_required
from api.db.joint_services.tenant_model_service import get_tenant_default_model_by_type, resolve_model_config
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from api.utils.api_utils import get_data_error_result, get_json_result, get_request_json, server_error_response
from common.constants import LLMType, RetCode, StatusEnum
from common import settings
from rag.app.tag import label_question
from rag.prompts.template import load_prompt

logger = logging.getLogger(__name__)


@manager.route("/document_creation/stream", methods=["POST"])  # noqa: F821
@login_required
async def create_document_stream():
    """流式文档创作接口
    
    基于知识库中的文档素材，辅助用户撰写报告、总结、方案、笔记、摘要等内容。
    创作内容可调用本地文档中的数据、案例、条款、素材，贴合已有资料风格。
    
    请求参数：
    - requirement: 创作要求（必填）
    - title: 文档标题（可选）
    - original_text: 参考原文（可选，用于扩写/缩写/改写）
    - dataset_ids: 指定知识库 ID 列表（可选，不指定则使用所有可用知识库）
    
    返回：SSE 流式响应
    """
    try:
        req = await get_request_json()
        if not req:
            return get_data_error_result(message="请求体不能为空")
        
        requirement = req.get("requirement", "")
        title = req.get("title", "")
        original_text = req.get("original_text", "")
        dataset_ids = req.get("dataset_ids", None)
        
        # 参数验证
        if not requirement or not requirement.strip():
            return get_data_error_result(message="创作要求不能为空")
        
        logger.info(f"收到流式创作请求：requirement={requirement[:50]}..., user={current_user.id}")
        
        # 获取可用的知识库
        if dataset_ids:
            if not isinstance(dataset_ids, list):
                return get_data_error_result(message="dataset_ids 必须是列表")
            
            kb_list = []
            for kb_id in dataset_ids:
                if not await KnowledgebaseService.accessible(kb_id=kb_id, user_id=current_user.id):
                    return get_data_error_result(message=f"无权访问知识库 {kb_id}")
                kbs = KnowledgebaseService.query(id=kb_id)
                if kbs:
                    kb_list.append(kbs[0])
            
            if not kb_list:
                return get_data_error_result(message="没有可用的知识库")
        else:
            kb_list = KnowledgebaseService.query(
                tenant_id=current_user.id,
                status=StatusEnum.VALID.value
            )
        
        if not kb_list:
            return get_data_error_result(message="没有可用的知识库，请先创建知识库并上传文档")
        
        valid_kbs = [kb for kb in kb_list if kb.chunk_num > 0]
        if not valid_kbs:
            return get_data_error_result(message="所有知识库都没有解析完成的文档")
        
        kb_ids = [kb.id for kb in valid_kbs]
        tenant_ids = list(set([kb.tenant_id for kb in valid_kbs]))
        
        # 获取 LLM 模型
        try:
            chat_model_config = get_tenant_default_model_by_type(current_user.id, LLMType.CHAT)
            chat_mdl = LLMBundle(current_user.id, chat_model_config)
        except Exception as e:
            logger.error(f"获取 LLM 模型失败：{e}")
            return get_data_error_result(message=f"获取 LLM 模型失败：{str(e)}")
        
        # 获取 embedding 模型
        embd_id = valid_kbs[0].embd_id
        embd_owner_tenant_id = valid_kbs[0].tenant_id
        try:
            embd_model_config = resolve_model_config(embd_owner_tenant_id, LLMType.EMBEDDING, embd_id)
            embd_mdl = LLMBundle(embd_owner_tenant_id, embd_model_config)
        except Exception as e:
            logger.warning(f"获取 embedding 模型失败：{e}")
            embd_mdl = None
        
        # 执行检索
        search_text = original_text or requirement
        logger.info(f"执行检索，query={search_text[:50]}..., kb_ids={kb_ids}")
        
        try:
            kbinfos = await settings.retriever.retrieval(
                question=search_text,
                embd_mdl=embd_mdl,
                tenant_ids=tenant_ids,
                kb_ids=kb_ids,
                page=1,
                page_size=20,
                similarity_threshold=0.1,
                vector_similarity_weight=0.7,
                top=20,
                doc_ids=[],
                aggs=True,
                rerank_mdl=None,
                rank_feature=label_question(search_text, valid_kbs),
            )
            chunks = kbinfos.get("chunks", [])
            logger.info(f"检索到 {len(chunks)} 个文档片段")
        except Exception as e:
            logger.error(f"检索失败：{e}")
            chunks = []
            kbinfos = {"chunks": [], "doc_aggs": []}
        
        # 构建上下文
        from rag.prompts.generator import kb_prompt
        knowledges = kb_prompt(kbinfos, chat_mdl.max_length)
        context = "\n\n".join(knowledges) if knowledges else "无额外素材"
        
        # 加载提示词模板
        system_prompt = load_prompt("doc_creation")
        
        # 构建用户提示词
        title_line = f"文档标题：{title}" if title else ""
        original_line = f"参考原文：{original_text}" if original_text else ""
        
        user_prompt = f"""请根据以下素材创作内容：

{context}

创作要求：
{requirement}

{title_line}
{original_line}

请开始创作（注意：
1. 标题必须使用 Markdown 语法（# ## ###）配合编号格式（1.、1.1、1.1.1...）
2. 标题前后、段落之间均不要有空行，保持格式紧凑
3. 必须输出完整的文章，不要中途截断）："""
        
        # 流式生成
        async def generate():
            yield f"data: {json.dumps({'type': 'start', 'content': ''})}\n\n"
            
            full_content = ""
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                gen_conf = valid_kbs[0].llm_setting if hasattr(valid_kbs[0], 'llm_setting') and valid_kbs[0].llm_setting else {"temperature": 0.7}
                
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
                
                # 提取参考来源
                sources = []
                seen_docs = set()
                for chunk in chunks:
                    doc_name = chunk.get("docnm_kwd", "未知文档")
                    if doc_name and doc_name not in seen_docs:
                        seen_docs.add(doc_name)
                        sources.append(doc_name)
                
                yield f"data: {json.dumps({'type': 'done', 'content': full_content, 'sources': sources})}\n\n"
                logger.info(f"流式创作完成，内容长度：{len(full_content)}，素材来源：{len(sources)} 个文档")
                
            except Exception as e:
                logger.error(f"流式生成失败：{e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': f'生成失败：{str(e)}'})}\n\n"
        
        return Response(generate(), mimetype="text/event-stream")
        
    except Exception as e:
        logger.error(f"流式创作失败：{e}", exc_info=True)
        async def error_generate():
            yield f"data: {json.dumps({'type': 'error', 'message': f'请求失败：{str(e)}'})}\n\n"
        return Response(error_generate(), mimetype="text/event-stream")
