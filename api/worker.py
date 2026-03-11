"""
任务队列和后台Worker
处理转录任务的提交、执行、状态管理
"""

import os
import sys
import uuid
import asyncio
import shutil
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入数据模型
from api.models import JobStatus, InputType


class Job:
    """任务数据类"""
    
    def __init__(
        self,
        job_id: str,
        input_text: str,
        input_type: InputType,
        local_file_path: Optional[str] = None
    ):
        self.job_id = job_id
        self.input = input_text
        self.input_type = input_type
        self.local_file_path = local_file_path
        
        self.status = JobStatus.QUEUED
        self.progress = 0
        self.message = "任务已排队，等待处理"
        
        self.title: Optional[str] = None
        self.duration: Optional[str] = None
        self.result_text: Optional[str] = None
        self.result_path: Optional[str] = None
        
        self.error: Optional[str] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "input_type": self.input_type.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        
        if self.status == JobStatus.COMPLETED:
            data["title"] = self.title
            data["duration"] = self.duration
            data["download_url"] = f"/download/{self.job_id}"
        
        if self.status == JobStatus.FAILED:
            data["error"] = self.error
        
        return data


class JobQueue:
    """内存任务队列"""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()
        self.processing = False
        self.worker_thread: Optional[threading.Thread] = None
    
    def add_job(self, job: Job) -> str:
        """添加新任务"""
        with self.lock:
            self.jobs[job.job_id] = job
        return job.job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务"""
        return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, **kwargs) -> bool:
        """更新任务"""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            job.updated_at = datetime.now()
            return True
    
    def get_all_jobs(self) -> Dict[str, Job]:
        """获取所有任务"""
        return self.jobs.copy()
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        with self.lock:
            return sum(1 for j in self.jobs.values() if j.status in [JobStatus.QUEUED, JobStatus.PROCESSING])


# 全局任务队列
job_queue = JobQueue()


# ==================== Worker ====================

def process_job(job: Job) -> None:
    """
    处理转录任务
    这是核心业务逻辑，调用现有的bilibili_video模块
    """
    try:
        # 更新状态为处理中
        job.status = JobStatus.PROCESSING
        job.progress = 10
        job.message = "正在处理任务..."
        job.updated_at = datetime.now()
        
        # 导入bilibili_video模块
        from skill.bilibili_video import VideoAnalyzer, get_config
        
        # 获取配置
        config = get_config()
        analyzer = VideoAnalyzer()
        analyzer.config = config
        
        # 根据输入类型调用不同的处理方式
        if job.input_type == InputType.BILIBILI:
            # Bilibili视频
            job.progress = 20
            job.message = "正在下载视频..."
            job.updated_at = datetime.now()
            
            # 使用异步方式调用
            result = asyncio.run(analyzer.analyze(job.input))
            
        elif job.input_type == InputType.LOCAL:
            # 本地文件
            job.progress = 20
            job.message = "正在提取音频..."
            job.updated_at = datetime.now()
            
            # 本地文件直接调用转录
            result = asyncio.run(analyzer.analyze(job.local_file_path))
        
        # 处理完成
        if result.get("status") == "success":
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.message = "转录完成"
            
            # 提取结果
            job.title = result.get("title", "未知标题")
            job.duration = result.get("duration", "未知时长")
            job.result_text = result.get("transcription", result.get("text", ""))
            
            # 保存结果到文件
            job.result_path = save_result(job)
            
        else:
            # 处理失败
            job.status = JobStatus.FAILED
            job.message = "转录失败"
            job.error = result.get("message", result.get("error", "未知错误"))
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.message = "处理失败"
        job.error = str(e)
    
    finally:
        job.updated_at = datetime.now()


def save_result(job: Job) -> str:
    """保存转录结果到文件"""
    results_dir = Path("/tmp/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    result_file = results_dir / f"{job.job_id}.txt"
    
    with open(result_file, "w", encoding="utf-8") as f:
        if job.result_text:
            # 如果有视频标题，添加到开头
            if job.title:
                f.write(f"# {job.title}\n\n")
            f.write(job.result_text)
        else:
            f.write("")
    
    return str(result_file)


def worker_loop():
    """Worker主循环"""
    while job_queue.processing:
        # 查找下一个待处理任务
        with job_queue.lock:
            next_job = None
            for job in job_queue.jobs.values():
                if job.status == JobStatus.QUEUED:
                    next_job = job
                    break
        
        if next_job:
            # 处理任务
            process_job(next_job)
        else:
            # 没有任务，短暂休眠
            time.sleep(1)


def start_worker():
    """启动Worker线程"""
    if not job_queue.processing:
        job_queue.processing = True
        job_queue.worker_thread = threading.Thread(target=worker_loop, daemon=True)
        job_queue.worker_thread.start()


def stop_worker():
    """停止Worker线程"""
    job_queue.processing = False
    if job_queue.worker_thread:
        job_queue.worker_thread.join(timeout=5)


# ==================== 缓存管理 ====================

def cleanup_old_jobs(max_age_hours: int = 24) -> tuple:
    """
    清理过期任务
    返回: (清理的文件数, 释放的空间MB)
    """
    cleared_count = 0
    freed_bytes = 0
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    
    jobs_to_delete = []
    
    with job_queue.lock:
        for job_id, job in job_queue.jobs.items():
            # 只清理已完成或失败的任务
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                if job.updated_at < cutoff_time:
                    jobs_to_delete.append(job_id)
                    
                    # 删除结果文件
                    if job.result_path and os.path.exists(job.result_path):
                        try:
                            freed_bytes += os.path.getsize(job.result_path)
                            os.remove(job.result_path)
                            cleared_count += 1
                        except Exception:
                            pass
                    
                    # 删除上传的临时文件
                    if job.local_file_path and os.path.exists(job.local_file_path):
                        try:
                            freed_bytes += os.path.getsize(job.local_file_path)
                            os.remove(job.local_file_path)
                            cleared_count += 1
                        except Exception:
                            pass
    
    # 删除任务记录
    for job_id in jobs_to_delete:
        del job_queue.jobs[job_id]
    
    freed_mb = freed_bytes / (1024 * 1024)
    return cleared_count, freed_mb


def clear_all_cache() -> tuple:
    """
    清理所有缓存
    返回: (清理的文件数, 释放的空间MB)
    """
    cleared_count = 0
    freed_bytes = 0
    
    # 清理结果目录
    results_dir = Path("/tmp/results")
    if results_dir.exists():
        for file in results_dir.glob("*.txt"):
            try:
                freed_bytes += os.path.getsize(file)
                os.remove(file)
                cleared_count += 1
            except Exception:
                pass
    
    # 清理上传目录
    uploads_dir = Path("/tmp/uploads")
    if uploads_dir.exists():
        for file in uploads_dir.glob("*"):
            try:
                freed_bytes += os.path.getsize(file)
                os.remove(file)
                cleared_count += 1
            except Exception:
                pass
    
    # 清空任务队列
    with job_queue.lock:
        job_queue.jobs.clear()
    
    freed_mb = freed_bytes / (1024 * 1024)
    return cleared_count, freed_mb
