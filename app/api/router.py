"""
API 路由注册模块
"""
from fastapi import APIRouter
from app.api.routes import qa, creation, optimize, files, memory

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(qa.router, prefix="/api/qa", tags=["问答"])
api_router.include_router(creation.router, prefix="/api/create", tags=["创作"])
api_router.include_router(optimize.router, prefix="/api/optimize", tags=["优化"])
api_router.include_router(files.router, prefix="/api/files", tags=["文件"])
api_router.include_router(memory.router, prefix="/api/memory", tags=["记忆"])
