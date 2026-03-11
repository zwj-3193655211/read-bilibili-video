---
name: bilibili-video
description: Use when users ask to analyze, summarize, or transcribe video content from Bilibili (B站) or local video files. Trigger when you see BV numbers, Bilibili URLs (including b23.tv short links), or requests to process local video/audio files (mp4, mkv, mp3, wav, etc.).
license: MIT
compatibility: Python 3.8-3.12, requires FunASR models (~1GB), optional ffmpeg for local videos
---

# Bilibili/Local Video Transcription Skill

一个用于转录Bilibili视频和本地视频/音频文件的iFlow技能。

## 概述

使用FunASR SenseVoice模型从Bilibili视频和本地媒体文件中提取并转录语音。支持BV号、URL、短链接和混合文本自动识别。

## 目录

- [快速开始](#快速开始)
- [功能特性](#功能特性)
- [输入格式](#输入格式)
- [输出格式](#输出格式)
- [iFlow集成](#iflow集成)
- [如何为iFlow编写技能](#如何为iflow编写技能)
- [如何为其他Agent编写技能](#如何为其他agent编写技能)
- [CLI用法](#cli用法)
- [配置说明](#配置说明)
- [错误处理](#错误处理)

---

## 快速开始

```bash
# 安装依赖
setup_env.bat  # Windows
# 或
chmod +x setup_env.sh && ./setup_env.sh  # Linux/macOS

# 初始化（下载模型，约1GB）
python skill.py --init

# 检查状态
python skill.py --status

# 转录Bilibili视频
python skill.py "BV1xx411c7mD"

# 转录本地视频
python skill.py "C:\\Videos\\lecture.mp4"
```

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 视频输入识别 | 自动识别Bilibili链接或本地视频文件 |
| 音频提取 | 从Bilibili下载或从本地视频提取音频 |
| 语音转录 | 使用FunASR SenseVoice模型进行准确转录 |
| 缓存机制 | 缓存音频和转录结果以加速后续处理 |
| 混合文本解析 | 从混合文本中提取Bilibili链接 |

---

## 输入格式

**无需预处理！** 脚本会自动识别输入类型：

| 类型 | 示例 |
|------|------|
| BV号 | `BV1xx411c7mD` |
| 标准URL | `https://www.bilibili.com/video/BV1xx411c7mD` |
| 移动端URL | `https://m.bilibili.com/video/BV1xx411c7mD` |
| 短链接 | `https://b23.tv/abc123` |
| 混合文本 | `帮我看看这个视频 https://www.bilibili.com/video/BV1xx411c7mD 怎么样` |
| 本地视频 | `C:\Videos\lecture.mp4` 或 `/home/user/video.mp4` |
| 本地音频 | `C:\Audio\speech.wav` |

---

## 输出格式

```json
{
  "status": "success",
  "type": "bilibili",
  "title": "视频标题",
  "bv_id": "BV1xx411c7mD",
  "url": "https://www.bilibili.com/video/BV1xx411c7mD",
  "duration": "15:30",
  "transcription": "完整转录文本...",
  "transcription_path": "C:\\Users\\xxx\\.iflow\\skills\\readbilibili-video\\cache\\text\\abc123.txt",
  "processing_time": "0:02:15",
  "_skill": {
    "name": "readbilibili-video",
    "version": "1.0.0"
  }
}
```

---

## iFlow集成

### 在iFlow中使用

```python
# 导入技能
import skill

# 转录Bilibili视频
result = skill.run("BV1xx411c7mD")

# 检查结果
if result["status"] == "success":
    print(f"标题: {result['title']}")
    print(f"时长: {result['duration']}")
    print(f"转录: {result['transcription'][:200]}...")
    
    # 读取完整转录
    with open(result["transcription_path"], 'r', encoding='utf-8') as f:
        full_text = f.read()
        print(f"全文长度: {len(full_text)} 字符")

# 检查技能状态
status = skill.check_status()
print(f"模型就绪: {status['status'] == 'ready'}")

# 清除缓存
skill.clear_cache()

# 获取技能信息
info = skill.info()
```

---

## 如何为iFlow编写技能

本节详细介绍如何为iFlow编写一个标准化的技能模块。

### 1. 技能文件结构

一个标准的iFlow技能需要以下文件：

```
my-skill/
├── skill.py          # 主入口文件（必需）
├── manifest.json     # 技能元数据（推荐）
├── SKILL.md          # 技能文档（推荐）
├── requirements.txt # Python依赖
└── README.md         # 使用说明（可选）
```

### 2. skill.py 标准格式

```python
#!/usr/bin/env python3
"""
Skill: My Custom Skill

技能的简要描述。

Usage:
    from skill import run
    result = run("input")
"""

import json
import asyncio
from typing import Dict, Any
from pathlib import Path

# ==================== 技能元数据 ====================
__skill__ = {
    "name": "my-skill-name",           # 技能唯一标识（必需）
    "version": "1.0.0",                  # 语义化版本（必需）
    "display_name": "技能显示名称",       # 友好显示名称
    "description": "技能简短描述",        # 1-2句话描述
    "long_description": """             # 详细描述（可选）
        详细的多行描述...
    """,
    "author": "Your Name",              # 作者
    "license": "MIT",                   # 许可证
    "homepage": "https://github.com/...", # 主页
    "repository": {
        "type": "git",
        "url": "https://github.com/..."
    },
    "keywords": ["keyword1", "keyword2"], # 搜索关键词
    "categories": ["category1"],          # 分类
    "compatibility": {
        "python": ">=3.8,<3.13",        # Python版本要求
        "iflow_cli": ">=1.0.0"          # iFlow CLI版本要求
    },
    "tags": ["tag1", "tag2"],            # 标签
    "requirements": {                   # 依赖要求
        "python_version": ">=3.8",
        "disk_space": "~100MB",
        "network": False
    },
    "entry_points": {                   # 入口点
        "function": "run",               # 主函数名
        "skill_info": "info",            # 获取信息
        "status": "check_status",       # 检查状态
        "clear_cache": "clear_cache",   # 清除缓存
        "initialize": "initialize"       # 初始化
    }
}

# ==================== 必需入口函数 ====================

def run(input_text: str, **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - iFlow skill标准接口
    
    Args:
        input_text: 输入文本或参数
        **kwargs: 可选参数
            - param1: 类型 - 参数说明
    
    Returns:
        Dict: 包含执行结果的字典，必须包含 "status" 字段
              - status: "success" | "error" | "help"
    
    Example:
        result = run("some input")
    """
    # 处理空输入
    if not input_text or not input_text.strip():
        return {
            "status": "error",
            "error": "invalid_input",
            "message": "输入不能为空",
            "suggestion": "请提供有效的输入"
        }
    
    # 处理帮助命令
    cmd = input_text.strip().lower()
    if cmd in ["--help", "help", "?"]:
        return {"status": "help", "message": get_skill_help()}
    
    # 处理状态命令
    if cmd in ["--status", "status"]:
        return check_status()
    
    # 处理缓存清除
    if cmd in ["--clear-cache", "clear-cache"]:
        return clear_cache()
    
    # 处理初始化
    if cmd in ["--init", "init"]:
        return initialize_models()
    
    try:
        # ===== 在这里实现主要逻辑 =====
        result = do_something(input_text, **kwargs)
        
        # 添加技能元数据
        result["_skill"] = {
            "name": __skill__["name"],
            "version": __skill__["version"]
        }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": "skill_execution_failed",
            "message": f"技能执行失败: {str(e)}",
            "suggestion": "请检查输入格式"
        }


def info() -> Dict[str, Any]:
    """
    获取技能元数据信息
    
    Returns:
        Dict: 技能完整元数据
    """
    return {"status": "success", "skill": __skill__}


# ==================== 可选工具函数 ====================

def check_status() -> Dict[str, Any]:
    """
    检查技能状态和配置
    
    Returns:
        Dict: 包含状态信息的字典
    """
    return {
        "status": "ready",  # 或 "need_init"
        "version": __skill__["version"]
    }


def clear_cache() -> Dict[str, Any]:
    """
    清除所有缓存文件
    
    Returns:
        Dict: 包含清理结果的字典
    """
    # 实现缓存清除逻辑
    return {"status": "success", "cleared": 0}


def initialize_models() -> Dict[str, Any]:
    """
    初始化技能（下载模型等）
    
    Returns:
        Dict: 包含初始化状态的字典
    """
    return {"status": "success", "message": "初始化完成"}


def get_skill_help() -> str:
    """获取技能帮助文本"""
    return f"""
{__skill__['name']} v{__skill__['version']}
{__skill__['description']}

用法: skill.run("<input>")
"""


# ==================== CLI入口（可选）================

def main():
    """CLI入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(description=__skill__["description"])
    parser.add_argument("input", nargs="?", help="输入")
    parser.add_argument("--status", action="store_true", help="检查状态")
    parser.add_argument("--skill-info", action="store_true", help="显示信息")
    
    args = parser.parse_args()
    
    if args.skill_info:
        print(json.dumps(__skill__, ensure_ascii=False, indent=2))
    elif args.status:
        print(json.dumps(check_status(), ensure_ascii=False, indent=2))
    elif args.input:
        print(json.dumps(run(args.input), ensure_ascii=False, indent=2))
    else:
        print(get_skill_help())


if __name__ == "__main__":
    main()
```

### 3. manifest.json 标准格式

```json
{
  "name": "my-skill-name",
  "version": "1.0.0",
  "type": "python-skill",
  "display_name": "技能显示名称",
  "description": "技能简短描述",
  "long_description": "详细的多行描述...",
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://github.com/...",
  "repository": {
    "type": "git",
    "url": "https://github.com/..."
  },
  "keywords": ["keyword1", "keyword2"],
  "categories": ["category1"],
  "compatibility": {
    "python": ">=3.8,<3.13",
    "iflow_cli": ">=1.0.0",
    "platforms": ["windows", "linux", "macos"]
  },
  "requirements": {
    "python_version": ">=3.8,<3.13",
    "disk_space": "~100MB",
    "memory": "~2GB RAM",
    "network": false
  },
  "entry_points": {
    "skill": "skill.py",
    "main_function": "run"
  },
  "dependencies": {
    "python": {
      "package1": ">=1.0.0"
    },
    "optional": {
      "package2": ">=2.0.0"
    }
  },
  "configuration": {
    "config_file": "~/.iflow/skills/my-skill/config.json",
    "defaults": {
      "option1": "default_value"
    }
  },
  "api": {
    "functions": [
      {
        "name": "run",
        "description": "主入口函数",
        "parameters": {
          "input_text": {
            "type": "string",
            "description": "输入描述"
          }
        }
      }
    ]
  }
}
```

### 4. iFlow技能调用约定

iFlow通过以下方式调用技能：

```python
# iFlow内部调用方式
import skill

# 主入口
result = skill.run("输入内容")

# 获取信息
info = skill.info()

# 检查状态
status = skill.check_status()

# 清除缓存
cache_result = skill.clear_cache()

# 初始化
init_result = skill.initialize_models()
```

---

## 如何为其他Agent编写技能

本节介绍如何为其他AI Agent（如Claude、ChatGPT等）编写可调用的技能模块。

### 1. Claude / OpenAI 函数调用

```python
# 定义为Claude可调用的函数
functions = [
    {
        "name": "transcribe_video",
        "description": "转录Bilibili视频或本地视频/音频文件的语音",
        "parameters": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Bilibili URL、BV号、或本地文件路径"
                },
                "max_duration": {
                    "type": "integer",
                    "description": "最大视频时长（分钟），默认70",
                    "optional": True
                }
            },
            "required": ["input"]
        }
    }
]

# 在Claude中调用
# response = openai.ChatCompletion.create(
#     model="gpt-4",
#     messages=[...],
#     functions=functions
# )
```

### 2. Anthropic Claude Tool Use

```python
# 为Claude Desktop定义工具
# 在 claude_settings.json 中配置:

{
  "tools": [
    {
      "name": "transcribe_video",
      "description": "Transcribe Bilibili video or local video/audio file",
      "input_schema": {
        "type": "object",
        "properties": {
          "input": {
            "type": "string",
            "description": "Bilibili URL, BV number, or local file path"
          }
        },
        "required": ["input"]
      }
    }
  ]
}

# 使用Tool
# from anthropic import Anthropic
# client = Anthropic()
# result = client.tools.transcribe_video(input="BV1xx411c7mD")
```

### 3. LangChain Agent

```python
from langchain.agents import AgentTool

transcribe_tool = AgentTool(
    name="transcribe_video",
    description="Transcribe Bilibili video or local video/audio file to text",
    func=lambda input: json.dumps(run(input))
)

# 在LangChain中使用
# agent = initialize_agent(
#     [transcribe_tool],
#     llm,
#     agent_type="structured-chat-zero-shot-react-description"
# )
```

### 4. 自定义Agent框架

```python
class VideoTranscriptionAgent:
    """一个简单的视频转录Agent"""
    
    def __init__(self):
        import skill
        self.skill = skill
    
    def process(self, user_input: str) -> str:
        """
        处理用户请求
        
        Args:
            user_input: 用户输入，可能包含Bilibili链接或本地文件路径
        
        Returns:
            str: 转录结果
        """
        result = self.skill.run(user_input)
        
        if result["status"] == "success":
            # 读取转录文件
            with open(result["transcription_path"], 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"错误: {result.get('message', '未知错误')}"
    
    def check_health(self) -> bool:
        """检查服务健康状态"""
        status = self.skill.check_status()
        return status.get("status") == "ready"


# 使用示例
agent = VideoTranscriptionAgent()
transcription = agent.process("BV1xx411c7mD")
print(transcription)
```

### 5. 通用REST API包装

```python
# 如果需要暴露为HTTP API
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.json
    result = run(data.get("input", ""))
    return jsonify(result)

@app.route("/status", methods=["GET"])
def status():
    return jsonify(check_status())

@app.route("/info", methods=["GET"])
def info():
    return jsonify(skill.info())

# 启动服务
# app.run(port=5000)
```

### 6. 技能发现与注册

```python
# 技能注册表 - 用于动态发现可用技能
SKILL_REGISTRY = {
    "readbilibili-video": {
        "module": "skill",
        "run": "run",
        "info": "info",
        "check_status": "check_status",
        "description": "转录Bilibili视频和本地媒体文件",
        "input_types": ["bv_number", "bilibili_url", "local_video", "local_audio"]
    },
    # 可添加更多技能
}

def discover_skills():
    """发现所有可用技能"""
    return [
        {
            "name": name,
            "description": info["description"],
            "input_types": info["input_types"]
        }
        for name, info in SKILL_REGISTRY.items()
    ]
```

---

## CLI用法

```bash
# Bilibili视频
python skill.py BV1xx411c7mD
python skill.py "https://www.bilibili.com/video/BV1xx411c7mD"

# 混合文本（自动提取URL）
python skill.py "帮我分析这个视频 https://b23.tv/abc123"

# 本地视频
python skill.py "C:\Videos\lecture.mp4"

# 本地音频
python skill.py "C:\Audio\speech.wav"

# 检查状态
python skill.py --status

# 清除缓存
python skill.py --clear-cache

# 显示技能信息
python skill.py --skill-info
```

---

## 配置说明

配置文件: `~/.iflow/skills/readbilibili-video/config.json`

```json
{
  "max_duration_minutes": 70,
  "model": "sensevoice"
}
```

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `max_duration_minutes` | 70 | 最大视频时长（分钟） |
| `model` | sensevoice | ASR模型 |

---

## 错误处理

| 错误码 | 原因 | 解决方案 |
|--------|------|----------|
| `invalid_input` | 无法识别输入格式 | 检查URL/路径格式 |
| `fetch_failed` | 无法获取视频信息 | 检查网络/视频是否可用 |
| `download_failed` | 音频下载失败 | 检查网络连接 |
| `duration_exceeded` | 视频过长 | 调整 `max_duration_minutes` |
| `extract_failed` | 音频提取失败 | 安装ffmpeg |
| `transcribe_failed` | 转录失败 | 检查音频格式 |
| `model_download_failed` | 模型下载失败 | 手动运行 `--init` |
| `skill_execution_failed` | 意外错误 | 查看日志 |

---

## License

MIT License - See LICENSE file for details.