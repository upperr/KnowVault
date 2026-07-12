"""
LLM 客户端模块
提供统一的 LLM 调用接口，支持流式和非流式两种模式

流式模式：适用于前端实时展示（智能问答、文档创作、文档优化）
非流式模式：适用于后端内部调用（知识召回、决策生成等）
"""
import json
import httpx
from typing import AsyncGenerator, Optional, List, Dict, Any
from app.config import OPENAI_BASE_URL, OPENAI_API_KEY, LLM_MODEL


class LLMClient:
    """LLM 客户端 - 支持流式和非流式调用"""
    
    def __init__(
        self,
        base_url: str = OPENAI_BASE_URL,
        api_key: str = OPENAI_API_KEY,
        model: str = LLM_MODEL,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        try:
            async with self.client.stream("POST", url, headers=headers, json=data) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
                        
        except httpx.HTTPStatusError as e:
            yield f"\n\n[错误：HTTP {e.response.status_code}]"
        except httpx.RequestError as e:
            yield f"\n\n[错误：请求失败 - {str(e)}]"
        except Exception as e:
            yield f"\n\n[错误：{str(e)}]"
    
    async def stream_complete(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """流式补全"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async for chunk in self.stream_chat(messages, temperature, max_tokens):
            yield chunk
    
    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """非流式完成，返回完整响应"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        
        try:
            response = await self.client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return content
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP 错误：{e.response.status_code}")
        except httpx.RequestError as e:
            raise Exception(f"请求失败：{str(e)}")
        except Exception as e:
            raise Exception(f"LLM 调用失败：{str(e)}")


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取或创建 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def close_llm_client():
    """关闭 LLM 客户端"""
    global _llm_client
    if _llm_client:
        await _llm_client.close()
        _llm_client = None
