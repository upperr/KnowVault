#!/usr/bin/env python3
"""
本地私有文档库智能问答与辅助创作工具
主应用入口 - FastAPI Web 服务
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from app.config import HOST, PORT
from app.api.router import api_router
from app.llm import get_llm_client, close_llm_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 初始化 FastAPI
app = FastAPI(
    title="本地私有文档库智能问答与辅助创作工具",
    description="基于本地文档的智能问答与素材驱动式文档创作系统（支持记忆加速）",
    version="1.1.0",
)

# 注册 API 路由（所有 API 都在 app/api/routes/ 中）
app.include_router(api_router)


# ============================================================
# 静态文件与页面路由
# ============================================================

# 挂载 webui 目录的静态文件（JS, CSS 等）
webui_dir = Path(__file__).parent.parent / "webui"
app.mount("/js", StaticFiles(directory=str(webui_dir / "js")), name="js")
app.mount("/css", StaticFiles(directory=str(webui_dir / "css")), name="css")


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回主页面"""
    static_dir = Path(__file__).parent.parent / "webui"
    index_path = static_dir / "index.html"
    
    if index_path.exists():
        return FileResponse(str(index_path))
    
    return HTMLResponse(content="""
    <html>
        <head>
            <title>文档知识库</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
            <h1>本地私有文档库智能问答与辅助创作工具</h1>
            <p>API 文档：<a href="/docs">/docs</a></p>
        </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "1.1.0"}


# ============================================================
# 应用生命周期
# ============================================================

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("应用启动中...")
    
    # 初始化知识库
    from app.core.knowledge_base import get_knowledge_base
    kb = get_knowledge_base()
    kb.initialize()
    
    logger.info(f"知识库已初始化")
    logger.info(f"服务监听：http://{HOST}:{PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("应用关闭中...")
    
    # 关闭流式客户端
    await close_llm_client()
    
    logger.info("资源已清理")


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
    )
