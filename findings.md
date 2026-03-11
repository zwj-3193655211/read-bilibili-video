# 研究发现

**项目**: Bilibili视频转录API服务 (Docker)  
**日期**: 2026-03-11

---

## 技术调研

### FastAPI 选型

- **优点**: 高性能、异步支持、自动生成API文档、易于使用
- **结论**: ✅ 采用

### 任务队列方案

| 方案 | 优点 | 缺点 | 状态 |
|------|------|------|------|
| 内存队列 | 简单 | 重启丢失 | ✅ 采用 |
| Redis | 持久化 | 需额外部署 | 未来升级 |
| Celery | 功能强大 | 复杂度过高 | 排除 |

### Docker 镜像分发

| 方案 | 优点 | 缺点 |
|------|------|------|
| GitHub Packages (ghcr.io) | 免费、开源项目友好 | 国内下载慢 |
| Docker Hub | 最常用 | 可能需要私有仓库 |
| 阿里云容器镜像 | 国内快 | 需要阿里云账号 |

**结论**: 采用 GitHub Packages（用户选择）

---

## 代码复用

### 现有代码

- `bilibili_video.py` - 核心转录逻辑 ✅ 可复用
- `skill.py` - iFlow技能接口 ✅ 可参考
- `requirements.txt` - Python依赖 ✅ 需扩展

### 需要新增

- `api/main.py` - FastAPI应用
- `api/routes.py` - API路由
- `api/models.py` - 数据模型
- `api/worker.py` - 后台任务处理
- `Dockerfile` - 容器配置

---

## 参考资料

- FastAPI: https://fastapi.tiangolo.com/
- GitHub Packages: https://docs.github.com/en/packages
- Uvicorn: https://www.uvicorn.org/

---

## 待验证假设

1. ✅ FunASR 可以在Docker容器中正常运行
2. ✅ 模型下载在首次启动时自动完成
3. ✅ 文件上传大小限制足够处理70分钟视频

---

## 已知限制

- 单实例同时只能处理一个任务
- 重启后任务队列丢失（内存队列限制）
- 需要网络连接以下载Bilibili视频
