"""
记忆管理相关 API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.memory.manager import MemoryManager

router = APIRouter()

# 简单的内存存储（用于演示）
_simple_memories: Dict[str, List[Dict]] = {}


class MemoryRequest(BaseModel):
    conversation_id: str
    content: str
    metadata: Optional[dict] = None


class MemoryClearRequest(BaseModel):
    short_term: bool = False
    long_term: bool = False


@router.get("/stats")
async def get_memory_stats():
    """获取记忆统计信息"""
    try:
        from app.memory.manager import MemoryManager
        memory_mgr = MemoryManager()
        stats = memory_mgr.get_stats()
        return {"memory": stats}
    except Exception as e:
        return {"memory": {"short_term": {"size": 0}, "long_term": {"total_entries": 0}}}


@router.post("/clear")
async def clear_memory(request: MemoryClearRequest):
    """清空记忆（短期/长期/全部）"""
    try:
        from app.memory.manager import MemoryManager
        memory_mgr = MemoryManager()
        
        if request.short_term:
            memory_mgr.clear_short_term()
        if request.long_term:
            memory_mgr.clear_long_term()
        
        return {"status": "success", "message": "记忆已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败：{str(e)}")


@router.post("/add")
async def add_memory_endpoint(request: MemoryRequest):
    import uuid
    memory_id = str(uuid.uuid4())
    
    if request.conversation_id not in _simple_memories:
        _simple_memories[request.conversation_id] = []
    
    memory = {
        "id": memory_id,
        "content": request.content,
        "metadata": request.metadata or {},
        "timestamp": str(__import__('datetime').datetime.now())
    }
    _simple_memories[request.conversation_id].append(memory)
    
    return {"status": "success", "memory_id": memory_id}


@router.get("/{conversation_id}")
async def get_memories_endpoint(conversation_id: str):
    memories = _simple_memories.get(conversation_id, [])
    return {"memories": memories}


@router.delete("/{conversation_id}")
async def clear_memories_endpoint(conversation_id: str):
    if conversation_id in _simple_memories:
        del _simple_memories[conversation_id]
    return {"status": "success"}
