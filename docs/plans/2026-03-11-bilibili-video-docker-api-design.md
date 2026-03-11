# Bilibili视频转录API服务 - Docker部署方案

**版本**: 1.0.0  
**日期**: 2026-03-11  
**状态**: 待批准

---

## 1. 项目概述

将Bilibili视频转录技能封装为Docker容器化API服务，用户可以通过HTTP请求调用转录功能。

### 1.1 核心功能

- 支持Bilibili视频URL/BV号转录
- 支持本地视频文件上传转录
- 任务队列模式：提交→轮询→下载
- 转录结果下载

### 1.2 目标用户

- 需要将Bilibili视频转文字的开发者
- 集成到其他AI Agent工作流中

---

## 2. 技术方案

### 2.1 技术栈

| 组件 | 技术选择 | 说明 |
|------|---------|------|
| Web框架 | FastAPI | 高性能，易用，支持异步 |
| 任务队列 | 内存队列 | 基础版，单实例 |
| 语音识别 | FunASR SenseVoice | 已有的转录能力 |
| 容器化 | Docker | 打包部署 |
| 镜像分发 | GitHub Packages (ghcr.io) | 免费开源 |

### 2.2 架构图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   用户       │────▶│  FastAPI    │────▶│  任务队列   │
│  (HTTP请求)  │     │   服务      │     │  (内存)     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       │                                       ▼
       │                               ┌─────────────┐
       │                               │  Worker     │
       │                               │  (转录处理)  │
       │                               └─────────────┘
       │                                       │
       ▼                                       ▼
┌─────────────┐                       ┌─────────────┐
│  下载结果   │◀─────────────────────│  存储       │
│  (txt文件) │                       │  (临时文件)  │
└─────────────┘                       └─────────────┘
```

---

## 3. API设计

### 3.1 端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /transcribe | 提交转录任务 |
| GET | /status/{job_id} | 获取任务状态 |
| GET | /download/{job_id} | 下载转录结果 |
| POST | /upload | 上传本地文件并转录 |
| DELETE | /cache | 手动清理缓存 |
| GET | /health | 健康检查 |

### 3.2 API详情

#### 3.2.1 提交转录任务

**请求**
```bash
# 方式1：Bilibili视频
POST /transcribe
Content-Type: application/json

{"input": "BV1xx411c7mD"}
# 或带标题的分享链接
{"input": "【一年吃掉7亿只...】https://www.bilibili.com/video/BV1ApNFzKE1c/..."}
```

**响应**
```json
{
  "status": "accepted",
  "job_id": "abc123",
  "message": "任务已提交",
  "estimated_time": "约2-5分钟"
}
```

#### 3.2.2 获取任务状态

```bash
GET /status/abc123
```

**响应**
```json
{
  "job_id": "abc123",
  "status": "processing",  // queued, processing, completed, failed
  "progress": 45,
  "message": "正在转录音频..."
}
```

或完成后：
```json
{
  "job_id": "abc123",
  "status": "completed",
  "title": "视频标题",
  "duration": "15:30",
  "download_url": "/download/abc123"
}
```

#### 3.2.3 下载转录结果

```bash
GET /download/abc123
```

返回纯文本文件 (text/plain)

#### 3.2.4 上传本地文件

```bash
# 直接上传视频文件
curl -X POST http://localhost:5000/upload \
  -F "file=@/path/to/video.mp4"
```

**响应**
```json
{
  "status": "accepted",
  "job_id": "local123",
  "message": "任务已提交"
}
```

#### 3.2.5 清理缓存

```bash
DELETE /cache
```

**响应**
```json
{
  "status": "success",
  "cleared_files": 5,
  "freed_mb": 450.2
}
```

---

## 4. Docker配置

### 4.1 镜像结构

```dockerfile
# 基础镜像
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建临时目录
RUN mkdir -p /tmp/uploads /tmp/results

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
```

### 4.2 构建命令

```bash
# 构建镜像
docker build -t readbilibili-video .

# 运行容器
docker run -d -p 5000:5000 readbilibili-video
```

### 4.3 首次启动流程

1. 容器启动
2. 检测模型是否存在
3. 如不存在，自动从ModelScope下载（约1GB）
4. 启动API服务

---

## 5. 任务队列设计

### 5.1 队列结构

```python
# 内存队列（基础版）
jobs = {
    "job_id": {
        "status": "queued|processing|completed|failed",
        "input": "原始输入",
        "input_type": "bilibili|local",
        "progress": 0,
        "result": None,
        "result_path": None,
        "created_at": timestamp,
        "updated_at": timestamp,
        "error": None
    }
}
```

### 5.2 处理流程

1. **提交任务** → 存入队列，返回job_id
2. **后台Worker** → 从队列取任务，处理
3. **状态更新** → 实时更新进度
4. **完成** → 保存结果到临时文件
5. **清理** → 定时或手动清理过期任务

---

## 6. 缓存管理

### 6.1 临时文件存储

- **上传文件**: `/tmp/uploads/{job_id}.{ext}`
- **转录结果**: `/tmp/results/{job_id}.txt`

### 6.2 清理策略

1. **定时清理**: 每24小时清理超过24小时的任务
2. **手动清理**: API调用 `/cache` 立即清理
3. **完成后清理**: 下载后可选择立即删除

---

## 7. 用户使用示例

### 7.1 方式一：转录Bilibili视频

```bash
# 1. 提交任务
curl -X POST http://localhost:5000/transcribe \
  -H "Content-Type: application/json" \
  -d '{"input": "【一年吃掉7亿只...】https://www.bilibili.com/video/BV1ApNFzKE1c/"}'

# 响应: {"job_id": "abc123", "status": "accepted"}

# 2. 轮询状态
curl http://localhost:5000/status/abc123
# {"status": "completed", "download_url": "/download/abc123"}

# 3. 下载结果
curl -o result.txt http://localhost:5000/download/abc123
```

### 7.2 方式二：上传本地文件

```bash
# 直接上传
curl -X POST http://localhost:5000/upload \
  -F "file=@/path/to/video.mp4"

# 轮询并下载（同上）
```

---

## 8. 文件结构

```
readbilibili-video/
├── api/
│   ├── __init__.py
│   ├── main.py           # FastAPI应用
│   ├── routes.py         # API路由
│   ├── models.py         # 数据模型
│   └── worker.py         # 后台任务处理
├── skill/
│   ├── __init__.py
│   ├── skill.py          # iFlow技能接口
│   └── bilibili_video.py # 原有转录逻辑
├── tests/
├── Dockerfile
├── docker-compose.yml    # 可选
├── requirements.txt
├── .dockerignore
└── README.md
```

---

## 9. 待确认项

- [ ] GitHub Packages 配置完成
- [ ] 镜像命名确定
- [ ] 是否需要用户认证？

---

## 10. 后续工作

1. 创建Dockerfile
2. 实现FastAPI服务
3. 实现任务队列
4. 实现文件上传
5. 配置GitHub Actions自动构建
6. 测试并完善文档
