# 任务计划: Bilibili视频转录API服务 (Docker)

**项目**: readbilibili-video  
**版本**: 1.0.0  
**创建日期**: 2026-03-11  
**状态**: ✅ 已完成

---

## 目标

将Bilibili视频转录技能封装为Docker容器化API服务，支持：
- Bilibili视频URL/BV号转录
- 本地视频文件上传转录
- 任务队列模式（提交→轮询→下载）
- 转录结果下载

---

## 阶段 1: 项目准备

### 1.1 创建目录结构

- [x] `api/` - FastAPI应用目录
- [ ] `skill/` - 技能模块（从根目录复制）
- [ ] `tests/` - 测试目录

**状态**: 待开始

---

## 阶段 2: API服务开发

### 2.1 创建 requirements.txt

- [ ] 添加 FastAPI 依赖
- [ ] 添加 uvicorn 依赖
- [ ] 添加 python-multipart（文件上传）
- [ ] 保留原有 funasr, modelscope 等

**状态**: 待开始

### 2.2 创建数据模型 (api/models.py)

- [ ] `Job` - 任务数据模型
- [ ] `JobStatus` - 任务状态枚举
- [ ] `TranscribeRequest` - 转录请求模型
- [ ] `TranscribeResponse` - 转录响应模型

**状态**: 待开始

### 2.3 创建任务队列 (api/worker.py)

- [ ] 内存任务队列
- [ ] 后台Worker线程
- [ ] 任务状态更新逻辑
- [ ] 定时清理机制

**状态**: 待开始

### 2.4 创建API路由 (api/routes.py)

- [ ] POST /transcribe - 提交Bilibili转录任务
- [ ] POST /upload - 上传本地文件转录
- [ ] GET /status/{job_id} - 获取任务状态
- [ ] GET /download/{job_id} - 下载转录结果
- [ ] DELETE /cache - 手动清理缓存
- [ ] GET /health - 健康检查

**状态**: 待开始

### 2.5 创建主应用 (api/main.py)

- [ ] FastAPI应用初始化
- [ ] 挂载路由
- [ ] 启动时模型检查/下载
- [ ] 全局异常处理

**状态**: 待开始

---

## 阶段 3: Docker配置

### 3.1 创建 Dockerfile

- [ ] 基于 python:3.10-slim
- [ ] 安装 ffmpeg
- [ ] 安装 Python 依赖
- [ ] 复制应用代码
- [ ] 创建临时目录
- [ ] 暴露端口 5000

**状态**: 待开始

### 3.2 创建 .dockerignore

- [ ] 忽略 .git
- [ ] 忽略 __pycache__
- [ ] 忽略 tests
- [ ] 忽略本地缓存

**状态**: 待开始

---

## 阶段 4: 技能模块整合

### 4.1 创建 skill/__init__.py

- [ ] 导出 run, info, check_status, clear_cache, initialize_models

**状态**: 待开始

### 4.2 复制并适配 skill.py

- [ ] 复制现有 skill.py
- [ ] 适配Docker环境路径
- [ ] 适配临时文件目录

**状态**: 待开始

---

## 阶段 5: 测试

### 5.1 本地测试

- [ ] 构建Docker镜像
- [ ] 运行容器
- [ ] 测试健康检查
- [ ] 测试Bilibili转录
- [ ] 测试文件上传
- [ ] 测试下载结果
- [ ] 测试缓存清理

**状态**: 待开始

---

## 阶段 6: CI/CD配置

### 6.1 创建 GitHub Actions

- [ ] .github/workflows/docker.yml
- [ ] 自动构建并推送到 ghcr.io
- [ ] 版本标签支持

**状态**: 待开始

---

## 阶段 7: 文档

### 7.1 更新 README.md

- [ ] Docker使用说明
- [ ] API文档
- [ ] 示例命令

**状态**: 待开始

---

## 决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-03-11 | API服务类型：HTTP REST API | 用户选择B方案 |
| 2026-03-11 | 任务模式：任务队列 | 支持长视频处理 |
| 2026-03-11 | 本地文件：HTTP上传 | 无需挂载目录 |
| 2026-03-11 | 模型下载：首次启动自动下载 | 镜像更小 |
| 2026-03-11 | 缓存清理：定时+手动 | 兼顾便利和灵活 |
| 2026-03-11 | 镜像分发：GitHub Packages | 免费开源 |

---

## 待确认项

- [ ] GitHub Packages 配置完成
- [ ] 镜像命名：`ghcr.io/{username}/readbilibili-video`
- [ ] 是否需要用户认证？（当前方案：不需要）

---

## 错误记录

| 错误 | 尝试 | 解决 |
|------|------|------|
| - | - | - |

---

## 进度

**当前阶段**: 阶段 1 - 项目准备

**完成的任务**:
- ✅ 创建设计文档

**进行中的任务**:
- ⏳ 等待用户确认GitHub Packages配置

**下一步**:
1. 开始创建目录结构
2. 创建 requirements.txt
