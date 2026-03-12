---
name: bilibili-video-docker
description: Docker version of Bilibili video transcription API. Use when users want to deploy using Docker without installing Python. Requires Docker Desktop.
license: MIT
compatibility: Docker, requires Docker Desktop
---

# Bilibili Video Transcription API (Docker Version)

B站视频转录 API 服务的 Docker 部署版本，无需安装 Python 环境。

## 概述

使用 Docker 部署 Bilibili 视频转录 API 服务，避免环境配置问题。包含 FunASR SenseVoice 语音识别模型。

## 前置要求

- Docker Desktop 已安装并运行
- 端口 5000 可用

## 快速开始

```bash
# 1. 构建镜像（首次构建约 10 分钟，后续约 1-2 分钟）
docker build -t bilibili-video-api:latest .

# 2. 运行容器
docker run -d -p 5000:5000 --name bilibili-video-api bilibili-video-api:latest

# 3. 检查健康状态
curl http://localhost:5000/api/v1/health
```

## 使用部署脚本（推荐）

```bash
# Windows
deploy_docker.bat

# 或使用 docker-compose
docker-compose up -d
```

## API 访问

| 服务 | 地址 |
|------|------|
| 健康检查 | http://localhost:5000/api/v1/health |
| Swagger 文档 | http://localhost:5000/docs |
| 提交转录 | POST http://localhost:5000/api/v1/transcribe |
| 查询状态 | GET http://localhost:5000/api/v1/status/{job_id} |
| 下载结果 | GET http://localhost:5000/api/v1/download/{job_id} |

## Docker 命令

```bash
# 查看日志
docker logs -f bilibili-video-api

# 停止服务
docker stop bilibili-video-api

# 重新启动
docker start bilibili-video-api

# 删除容器（保留镜像）
docker rm bilibili-video-api

# 删除镜像
docker rmi bilibili-video-api
```

## API 使用示例

### 提交转录任务

```bash
curl -X POST http://localhost:5000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -d '{"input": "https://www.bilibili.com/video/BV1xx411c7mD"}'
```

响应：
```json
{
  "status": "accepted",
  "job_id": "abc12345",
  "message": "任务已提交",
  "estimated_time": "约2-5分钟"
}
```

### 查询任务状态

```bash
curl http://localhost:5000/api/v1/status/abc12345
```

响应：
```json
{
  "job_id": "abc12345",
  "status": "processing",
  "progress": 50,
  "message": "正在转录...",
  "title": "视频标题",
  "duration": "10:30"
}
```

### 下载转录结果

```bash
curl http://localhost:5000/api/v1/download/abc12345 -o result.txt
```

## Python SDK 调用

如果需要从 Python 代码调用 Docker 部署的 API：

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"

def submit_transcription(url: str) -> str:
    """提交转录任务，返回 job_id"""
    response = requests.post(
        f"{BASE_URL}/transcribe",
        json={"input": url}
    )
    return response.json()["job_id"]

def get_status(job_id: str) -> dict:
    """查询任务状态"""
    response = requests.get(f"{BASE_URL}/status/{job_id}")
    return response.json()

def download_result(job_id: str) -> str:
    """下载转录结果"""
    response = requests.get(f"{BASE_URL}/download/{job_id}")
    return response.text

# 使用示例
job_id = submit_transcription("https://www.bilibili.com/video/BV1xx411c7mD")
print(f"Job ID: {job_id}")

# 轮询等待完成
import time
while True:
    status = get_status(job_id)
    if status["status"] == "completed":
        break
    time.sleep(10)

# 下载结果
result = download_result(job_id)
print(result)
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| 首次启动慢 | 首次构建会下载模型（约 1GB），请耐心等待 |
| 端口被占用 | 修改 `-p 5000:5000` 为其他端口如 `-p 8080:5000` |
| 模型下载失败 | 检查网络，或使用代理 |
| Docker 不响应 | 重启 Docker Desktop |

## 文件结构

```
readbilibili-video/
├── Dockerfile              # Docker 构建文件
├── docker-compose.yml     # Docker Compose 配置
├── deploy_docker.bat      # 部署脚本 (Windows)
├── api/                   # API 模块
│   ├── main.py           # FastAPI 主入口
│   ├── routes.py         # API 路由
│   ├── worker.py         # 后台任务处理
│   └── models.py         # 数据模型
├── skill/                # 技能核心模块
│   └── bilibili_video.py # 视频转录逻辑
├── bilibili_video.py     # 主入口
├── skill.py              # iFlow 技能入口
├── requirements.txt      # Python 依赖
└── README.md             # 使用说明
```

## 技术细节

- **基础镜像**: python:3.10-slim
- **API 框架**: FastAPI + Uvicorn
- **语音识别**: FunASR SenseVoice
- **端口**: 5000
- **首次启动**: 约 2-5 分钟（模型下载）
- **后续启动**: 约 10-30 秒

## License

MIT License
