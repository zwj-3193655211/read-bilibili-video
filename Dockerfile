# Bilibili视频转录API服务 - Dockerfile
# 基于 python:3.10-slim 镜像构建

# ============================================
# 第一阶段：构建阶段（可选，用于减少最终镜像大小）
# ============================================
# FROM python:3.10-slim as builder

# # 安装构建工具
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# # 设置工作目录
# WORKDIR /app

# # 先复制依赖文件
# COPY requirements.txt .

# # 安装Python依赖到用户目录
# RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================
# 第二阶段：运行阶段
# ============================================
FROM python:3.10-slim

# ============================================
# 1. 安装系统依赖
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# 2. 设置环境变量
# ============================================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ============================================
# 3. 设置工作目录
# ============================================
WORKDIR /app

# ============================================
# 4. 复制依赖文件
# ============================================
COPY requirements.txt .

# ============================================
# 5. 安装Python依赖
# ============================================
# 先安装 torch (CPU版，体积小)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 安装其他依赖
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# 6. 复制应用代码
# ============================================
# 复制api模块
COPY api/ ./api/

# 复制skill模块
COPY skill/ ./skill/

# 复制主模块
COPY bilibili_video.py .

# 复制skill.py
COPY skill.py .

# ============================================
# 7. 创建必要的目录
# ============================================
RUN mkdir -p /tmp/uploads /tmp/results

# ============================================
# 8. 暴露端口
# ============================================
EXPOSE 5000

# ============================================
# 9. 健康检查
# ============================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

# ============================================
# 10. 启动命令
# ============================================
# 使用uvicorn运行FastAPI应用
# --host 0.0.0.0 允许外部访问
# --port 5000 端口
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "5000"]

# ============================================
# 备用启动方式（调试用）
# ============================================
# CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
