"""
API数据模型
定义请求/响应数据结构
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class JobStatus(str, Enum):
    """任务状态枚举"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InputType(str, Enum):
    """输入类型枚举"""
    BILIBILI = "bilibili"
    LOCAL = "local"


# ==================== 请求模型 ====================

class TranscribeRequest(BaseModel):
    """转录请求模型"""
    input: str = Field(..., description="Bilibili URL, BV号, 或带标题的分享链接")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {"input": "BV1xx411c7mD"},
                {"input": "https://www.bilibili.com/video/BV1xx411c7mD"},
                {"input": "【一年吃掉7亿只...】https://www.bilibili.com/video/BV1ApNFzKE1c/"}
            ]
        }


class UploadResponse(BaseModel):
    """上传响应模型"""
    status: str = Field(..., description="任务状态")
    job_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="提示信息")


# ==================== 响应模型 ====================

class TranscribeResponse(BaseModel):
    """转录响应模型"""
    status: str = Field(..., description="任务状态: accepted, queued, processing")
    job_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="提示信息")
    estimated_time: Optional[str] = Field(None, description="预计处理时间")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "status": "accepted",
                    "job_id": "abc123",
                    "message": "任务已提交",
                    "estimated_time": "约2-5分钟"
                }
            ]
        }


class JobStatusResponse(BaseModel):
    """任务状态响应模型"""
    job_id: str = Field(..., description="任务ID")
    status: JobStatus = Field(..., description="任务状态")
    progress: Optional[int] = Field(None, description="进度百分比 (0-100)")
    message: str = Field(..., description="状态描述")
    
    # 完成时可选字段
    title: Optional[str] = Field(None, description="视频标题")
    duration: Optional[str] = Field(None, description="视频时长")
    download_url: Optional[str] = Field(None, description="结果下载链接")
    
    # 失败时可选字段
    error: Optional[str] = Field(None, description="错误信息")
    
    # 时间戳
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "job_id": "abc123",
                    "status": "processing",
                    "progress": 45,
                    "message": "正在转录音频..."
                },
                {
                    "job_id": "abc123",
                    "status": "completed",
                    "title": "视频标题",
                    "duration": "15:30",
                    "download_url": "/download/abc123"
                }
            ]
        }


class CacheClearResponse(BaseModel):
    """缓存清理响应模型"""
    status: str = Field(..., description="状态")
    cleared_files: int = Field(..., description="清理的文件数")
    freed_mb: float = Field(..., description="释放的空间(MB)")
    message: str = Field(..., description="提示信息")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="服务版本")
    models_ready: bool = Field(..., description="模型是否就绪")
    queue_size: int = Field(..., description="当前队列任务数")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细错误信息")
