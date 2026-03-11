#!/usr/bin/env python3
"""
iFlow Skill: Bilibili/Local Video Transcription

一个用于转录Bilibili视频和本地视频/音频文件的iFlow技能。
支持BV号、URL、短链接和本地文件自动识别。

Usage (iFlow):
    from skill import run
    result = run("BV1xx411c7mD")

Usage (Claude/其他Agent):
    result = skill.run("https://www.bilibili.com/video/BV1xx411c7mD")

Usage (CLI):
    python skill.py "BV1xx411c7mD"
    python skill.py --status
    python skill.py --init
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Skill metadata - iFlow标准格式
__skill__ = {
    "name": "readbilibili-video",
    "version": "1.0.0",
    "display_name": "Bilibili视频转录",
    "description": "提取并转录Bilibili视频和本地媒体文件的语音",
    "long_description": """
        一个综合性的视频分析工具，可以从Bilibili视频下载音频或从本地视频/音频文件提取音频，
        然后使用FunASR SenseVoice模型将语音转录为文本。支持多种输入格式，包括BV号、URL、短链接和本地文件。
    """,
    "author": "iFlow Community",
    "license": "MIT",
    "homepage": "https://github.com/yourusername/readbilibili-video",
    "repository": {
        "type": "git",
        "url": "https://github.com/yourusername/readbilibili-video.git"
    },
    "keywords": [
        "bilibili", "b站", "video", "transcription", "speech-to-text", 
        "asr", "funasr", "audio", "iflow", "skill"
    ],
    "categories": ["media-processing", "ai-ml", "productivity"],
    "compatibility": {
        "python": ">=3.8,<3.13",
        "iflow_cli": ">=1.0.0"
    },
    "tags": [
        "video", "transcription", "bilibili", "b站", 
        "speech-to-text", "asr", "funasr"
    ],
    "requirements": {
        "python_version": ">=3.8,<3.13",
        "disk_space": "~1GB for models",
        "memory": "~2GB RAM recommended",
        "network": True,
        "system_tools": ["ffmpeg (optional for local videos)"]
    },
    "entry_points": {
        "function": "run",
        "skill_info": "info",
        "status": "check_status",
        "clear_cache": "clear_cache",
        "initialize": "initialize_models"
    }
}

# Import the main analyzer
skill_dir = Path(__file__).parent.resolve()
if str(skill_dir) not in sys.path:
    sys.path.insert(0, str(skill_dir))

try:
    from bilibili_video import VideoAnalyzer, identify_input, get_config
except ImportError as e:
    print(f"Error importing from bilibili_video.py: {e}")
    sys.exit(1)


# ==================== iFlow Skill 标准入口函数 ====================

def run(input_text: str, **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - iFlow skill标准接口
    
    Args:
        input_text: Bilibili URL, BV号, 或本地视频/音频文件路径
        **kwargs: 可选参数
            - transcribe_only: bool - 仅转录，不生成摘要
            - max_duration: int - 覆盖最大时长限制（分钟）
            - language: str - 语言设置 (zh, en, auto)
    
    Returns:
        Dict: 包含转录结果或错误信息的字典
    
    Example (iFlow):
        result = skill.run("BV1xx411c7mD")
    
    Example (Claude):
        result = skill.run("https://www.bilibili.com/video/BV1xx411c7mD")
    """
    # Handle empty input
    if not input_text or not input_text.strip():
        return {
            "status": "error",
            "error": "invalid_input",
            "message": "输入不能为空",
            "suggestion": "请提供Bilibili URL、BV号或本地视频/音频文件路径"
        }
    
    # Handle help/status commands
    cmd = input_text.strip().lower()
    if cmd in ["--help", "help", "?"]:
        return {"status": "help", "message": get_skill_help()}
    if cmd in ["--status", "status"]:
        return check_status()
    if cmd in ["--clear-cache", "clear-cache"]:
        return clear_cache()
    if cmd in ["--init", "init", "initialize"]:
        return initialize_models()
    
    try:
        config = migrate_config()
        analyzer = VideoAnalyzer()
        analyzer.config = config
        
        if "max_duration" in kwargs:
            analyzer.config["max_duration_minutes"] = kwargs["max_duration"]
        
        result = asyncio.run(analyzer.analyze(input_text))
        
        # Add skill metadata
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
            "suggestion": "请检查输入格式和依赖是否正确安装"
        }


def info() -> Dict[str, Any]:
    """
    获取技能元数据信息
    
    Returns:
        Dict: 技能完整元数据
    """
    return {"status": "success", "skill": __skill__}


def get_iflow_config_path() -> Path:
    """Get the standard iFlow skill configuration directory"""
    home_dir = Path.home()
    config_dir = home_dir / ".iflow" / "skills" / "bilibili-video"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def migrate_config() -> Dict[str, Any]:
    """
    Migrate configuration from old location to iFlow standard location
    Returns the merged configuration
    """
    old_config = get_config()
    iflow_dir = get_iflow_config_path()
    
    # Create iFlow standard directories
    (iflow_dir / "cache" / "audio").mkdir(parents=True, exist_ok=True)
    (iflow_dir / "cache" / "text").mkdir(parents=True, exist_ok=True)
    
    # Check if config exists in iFlow location
    iflow_config_path = iflow_dir / "config.json"
    
    if iflow_config_path.exists():
        # Use iFlow config
        try:
            import json
            with open(iflow_config_path, 'r', encoding='utf-8') as f:
                iflow_config = json.load(f)
            # Merge with defaults, iFlow config takes precedence
            config = {**old_config, **iflow_config, "cache_dir": str(iflow_dir / "cache")}
        except Exception as e:
            print(f"Warning: Could not load iFlow config: {e}, using default config")
            config = {**old_config, "cache_dir": str(iflow_dir / "cache")}
    else:
        # Migrate old config to iFlow location
        config = {**old_config, "cache_dir": str(iflow_dir / "cache")}
        try:
            import json
            with open(iflow_config_path, 'w', encoding='utf-8') as f:
                json.dump({k: v for k, v in config.items() if k != "cache_dir"}, 
                         f, ensure_ascii=False, indent=2)
            print(f"Migrated config to: {iflow_config_path}")
        except Exception as e:
            print(f"Warning: Could not migrate config: {e}")
    
    return config


# ==================== 工具函数 ====================

def check_status() -> Dict[str, Any]:
    """
    检查技能状态和配置
    
    Returns:
        Dict: 包含状态信息的字典
    """
    try:
        config = migrate_config()
        analyzer = VideoAnalyzer()
        analyzer.config = config
        
        status = analyzer.check_status()
        status["_skill"] = {
            "name": __skill__["name"],
            "version": __skill__["version"],
            "config_path": str(get_iflow_config_path() / "config.json"),
            "cache_path": str(get_iflow_config_path() / "cache")
        }
        
        return status
    except Exception as e:
        return {
            "status": "error",
            "error": "status_check_failed",
            "message": f"状态检查失败: {str(e)}",
            "_skill": {
                "name": __skill__["name"],
                "version": __skill__["version"]
            }
        }


def clear_cache() -> Dict[str, Any]:
    """
    清除所有缓存的音频和转录文件
    
    Returns:
        Dict: 包含清理结果的字典
    """
    try:
        config = migrate_config()
        analyzer = VideoAnalyzer()
        analyzer.config = config
        
        result = analyzer.clear_cache()
        result["_skill"] = {
            "name": __skill__["name"],
            "version": __skill__["version"]
        }
        
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": "cache_clear_failed",
            "message": f"清除缓存失败: {str(e)}",
            "_skill": {
                "name": __skill__["name"],
                "version": __skill__["version"]
            }
        }


def initialize_models() -> Dict[str, Any]:
    """
    初始化技能 - 下载所需的模型
    
    Returns:
        Dict: 包含初始化状态的字典
    """
    try:
        config = migrate_config()
        analyzer = VideoAnalyzer()
        analyzer.config = config
        
        success, message = analyzer.recognizer.download_models()
        
        return {
            "status": "success" if success else "error",
            "message": message,
            "_skill": {
                "name": __skill__["name"],
                "version": __skill__["version"]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": "initialization_failed",
            "message": f"模型初始化失败: {str(e)}",
            "_skill": {
                "name": __skill__["name"],
                "version": __skill__["version"]
            }
        }


def get_skill_help() -> str:
    """
    获取技能帮助文本
    
    Returns:
        str: 格式化的帮助字符串
    """
    help_text = f"""
{__skill__['name']} v{__skill__['version']}
{__skill__['description']}

用法:
    skill.run("<输入>")
    skill.info()           # 获取技能信息
    skill.check_status()  # 检查状态

输入格式:
    - BV号: BV1xx411c7mD
    - Bilibili URL: https://www.bilibili.com/video/BV1xx411c7mD
    - 短链接: https://b23.tv/abc123
    - 本地视频: C:\\Videos\\lecture.mp4
    - 本地音频: C:\\Audio\\speech.wav

命令:
    --status       检查技能状态和配置
    --clear-cache  清除所有缓存文件
    --init         下载所需模型 (~1GB)
    --help         显示此帮助信息

配置:
    配置文件: {get_iflow_config_path() / 'config.json'}
    缓存目录: {get_iflow_config_path() / 'cache'}
    
    默认配置:
    {{
        "max_duration_minutes": 70,
        "model": "sensevoice"
    }}

要求:
    - Python {__skill__['requirements']['python_version']}
    - 磁盘空间: {__skill__['requirements']['disk_space']}
    - 可选: ffmpeg (用于本地视频处理)

示例:
    # 分析Bilibili视频
    result = skill.run("BV1xx411c7mD")
    
    # 分析本地视频
    result = skill.run("C:\\Videos\\lecture.mp4")
    
    # 检查状态
    status = skill.check_status()
    
    # 清除缓存
    result = skill.clear_cache()
"""
    return help_text.strip()


# ==================== CLI 入口 ====================

def main():
    """
    CLI入口点 - 支持命令行使用
    
    用法:
        python skill.py "BV1xx411c7mD"
        python skill.py --status
        python skill.py --init
    """
    parser = argparse.ArgumentParser(
        description=f"{__skill__['name']} v{__skill__['version']} - {__skill__['description']}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("input", nargs="?", help="Bilibili URL, BV号, 或本地视频/音频文件路径")
    parser.add_argument("--status", action="store_true", help="检查技能状态")
    parser.add_argument("--clear-cache", action="store_true", help="清除所有缓存")
    parser.add_argument("--init", action="store_true", help="初始化模型")
    parser.add_argument("--skill-info", action="store_true", help="显示技能元数据")
    
    args = parser.parse_args()
    
    if args.skill_info:
        print(json.dumps(__skill__, ensure_ascii=False, indent=2))
        return
    
    if args.status:
        result = check_status()
    elif args.clear_cache:
        result = clear_cache()
    elif args.init:
        result = initialize_models()
    elif args.input:
        result = run(args.input)
    else:
        print(get_skill_help())
        return
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()