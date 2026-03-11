"""
Bilibili视频转录API服务
FastAPI主应用入口
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from api.worker import cleanup_old_jobs, start_worker, stop_worker
from api.models import ErrorResponse


# ==================== 启动和关闭事件 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("=" * 50)
    print("Bilibili视频转录API服务启动中...")
    print("=" * 50)
    
    # 启动后台Worker
    start_worker()
    
    # 检查模型
    await check_models()
    
    print("服务启动完成！")
    print("API文档: http://localhost:5000/docs")
    print("=" * 50)
    
    yield
    
    # 关闭时
    print("正在关闭服务...")
    stop_worker()
    print("服务已关闭")


async def check_models():
    """检查模型是否已下载"""
    model_dir = Path.home() / ".cache" / "modelscope" / "hub"
    
    if not model_dir.exists() or not any(model_dir.iterdir()):
        print("⚠️  模型未找到，首次请求时将自动下载...")
        print("📥 模型下载约需1GB空间，首次启动可能需要几分钟")
    else:
        print("✅ 模型已就绪")


# ==================== FastAPI应用 ====================

app = FastAPI(
    title="Bilibili视频转录API",
    description="""
    将Bilibili视频和本地视频/音频文件转录为文本的API服务。
    
    ## 功能
    - Bilibili视频URL/BV号转录
    - 本地视频文件上传转录
    - 任务队列支持长视频处理
    - 转录结果下载
    
    ## 使用流程
    1. 提交转录任务 (POST /transcribe 或 POST /upload)
    2. 获取任务ID (job_id)
    3. 轮询任务状态 (GET /status/{job_id})
    4. 下载转录结果 (GET /download/{job_id})
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 全局异常处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message="服务器内部错误",
            detail=str(exc)
        ).model_dump()
    )


# ==================== 路由 ====================

app.include_router(router, prefix="/api/v1", tags=["转录服务"])


# ==================== 根路由 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Bilibili视频转录API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "transcribe": "/api/v1/transcribe",
            "upload": "/api/v1/upload",
            "status": "/api/v1/status/{job_id}",
            "download": "/api/v1/download/{job_id}",
            "cache": "/api/v1/cache",
            "health": "/api/v1/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=False
    )
