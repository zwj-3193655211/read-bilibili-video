"""
Skill模块
提供bilibili视频转录的核心功能
"""

from skill.bilibili_video import VideoAnalyzer, identify_input, get_config

__all__ = [
    "VideoAnalyzer",
    "identify_input",
    "get_config"
]
