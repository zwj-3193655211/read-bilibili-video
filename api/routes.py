"""
API路由定义
处理所有HTTP请求
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse

from api.models import (
    TranscribeRequest,
    TranscribeResponse,
    JobStatusResponse,
    CacheClearResponse,
    HealthResponse,
    ErrorResponse,
    InputType
)
from api.worker import (
    job_queue,
    Job,
    cleanup_old_jobs,
    clear_all_cache,
    start_worker
)

# 启动Worker
start_worker()

# 创建路由
router = APIRouter()


# ==================== 任务提交 ====================

@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    summary="提交Bilibili视频转录任务",
    description="提交一个Bilibili视频转录任务，返回任务ID用于查询状态"
)
async def transcribe_bilibili(request: TranscribeRequest):
    """
    提交Bilibili视频转录任务
    
        支持的输入格式:

        - BV号: BV1xx411c7mD

        - 完整URL: https://www.bilibili.com/video/BV1xx411c7mD

        - 短链接: https://b23.tv/xxx

        - 带标题的分享链接: 【标题】 https://www.bilibili.com/video/...

        """
    # 生成任务ID
    job_id = str(uuid.uuid4())[:8]
    
    # 创建任务
    job = Job(
        job_id=job_id,
        input_text=request.input,
        input_type=InputType.BILIBILI
    )
    
    # 添加到队列
    job_queue.add_job(job)
    
    return TranscribeResponse(
        status="accepted",
        job_id=job_id,
        message="任务已提交",
        estimated_time="约2-5分钟"
    )


@router.post(
    "/upload",
    response_model=TranscribeResponse,
    summary="上传本地文件并转录",
    description="上传本地视频/音频文件并提交转录任务"
)
async def upload_and_transcribe(file: UploadFile = File(...)):
    """
    上传本地视频文件并转录
    
    支持格式: mp4, mkv, avi, mov, mp3, wav, m4a 等
    """
    # 生成任务ID
    job_id = str(uuid.uuid4())[:8]
    
    # 保存上传的文件
    uploads_dir = Path("/tmp/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取文件扩展名
    ext = Path(file.filename).suffix if file.filename else ".mp4"
    local_path = uploads_dir / f"{job_id}{ext}"
    
    # 保存文件
    try:
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存文件失败: {str(e)}"
        )
    
    # 创建任务
    job = Job(
        job_id=job_id,
        input_text=file.filename or "local_file",
        input_type=InputType.LOCAL,
        local_file_path=str(local_path)
    )
    
    # 添加到队列
    job_queue.add_job(job)
    
    return TranscribeResponse(
        status="accepted",
        job_id=job_id,
        message="任务已提交",
        estimated_time="约2-5分钟"
    )


# ==================== 任务查询 ====================

@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="获取任务状态",
    description="通过任务ID查询转录任务的当前状态"
)
async def get_job_status(job_id: str):
    """获取指定任务的执行状态"""
    job = job_queue.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {job_id} 不存在"
        )
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        title=job.title,
        duration=job.duration,
        download_url=f"/download/{job.job_id}" if job.status.value == "completed" else None,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


# ==================== 结果下载 ====================

@router.get(
    "/download/{job_id}",
    summary="下载转录结果",
    description="下载转录完成的文本结果"
)
async def download_result(job_id: str):
    """下载转录结果文本文件"""
    job = job_queue.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {job_id} 不存在"
        )
    
    if job.status.value != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务尚未完成，当前状态: {job.status.value}"
        )
    
    if not job.result_path or not os.path.exists(job.result_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="结果文件不存在"
        )
    
    # 生成文件名
    filename = f"{job.title or 'result'}_{job_id}.txt" if job.title else f"result_{job_id}.txt"
    
    return FileResponse(
        path=job.result_path,
        media_type="text/plain",
        filename=filename
    )


# ==================== 缓存管理 ====================

@router.delete(
    "/cache",
    response_model=CacheClearResponse,
    summary="清理缓存",
    description="清理所有临时文件和已完成的任务记录"
)
async def clear_cache():
    """手动清理所有缓存"""
    cleared_files, freed_mb = clear_all_cache()
    
    return CacheClearResponse(
        status="success",
        cleared_files=cleared_files,
        freed_mb=round(freed_mb, 2),
        message=f"已清理 {cleared_files} 个文件，释放 {freed_mb:.2f} MB"
    )


# ==================== 健康检查 ====================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查服务状态和模型是否就绪"
)
async def health_check():
    """服务健康检查"""
    # 检查模型目录
    models_ready = False
    model_dir = Path("/root/.cache/modelscope/hub")
    if model_dir.exists() and any(model_dir.iterdir()):
        models_ready = True
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        models_ready=models_ready,
        queue_size=job_queue.get_queue_size()
    )
