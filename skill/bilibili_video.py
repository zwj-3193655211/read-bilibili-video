#!/usr/bin/env python3
"""
B 站视频理解工具 / 本地视频分析工具
功能：
  - 支持 B 站视频链接和本地视频文件识别
  - 提取视频音频并进行语音转写
  - 输出转写文本到 cache/text/ 目录

使用方法：
    python bilibili_video.py <URL 或 BV 号或本地视频路径>
    python bilibili_video.py --status
    python bilibili_video.py --clear-cache
    python bilibili_video.py --init
"""

import os
import re
import sys
import json
import asyncio
import logging
import argparse
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 常量定义 ====================

DEFAULT_CONFIG = {
    "max_duration_minutes": 70,
    "model": "sensevoice"
}

# FunASR 模型
VAD_MODEL_ID = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
ASR_MODEL_ID = "iic/SenseVoiceSmall"

# 语音识别模型参数
VAD_MAX_SEGMENT_TIME = 180000  # 3 分钟
VAD_MAX_END_SILENCE_TIME = 4000  # 4 秒
VAD_MAX_START_SILENCE_TIME = 3000  # 3 秒
ASR_BATCH_SIZE_S = 180  # 180 秒
ASR_MERGE_LENGTH_S = 180  # 180 秒

# 视频格式支持
VIDEO_EXTENSIONS = {'.mp4', '.flv', '.avi', '.mkv', '.mov', '.wmv', '.webm', '.m4v', '.mpeg', '.mpg'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma', '.aiff'}

# ==================== 工具函数 ====================

def find_ffmpeg() -> Optional[str]:
    """查找 ffmpeg 可执行文件"""
    # 1. 环境变量
    ffmpeg = os.environ.get("FFMPEG_PATH")
    if ffmpeg and os.path.exists(ffmpeg):
        return ffmpeg

    # 2. skill 目录
    skill_dir = get_skill_dir()
    for name in ["ffmpeg.exe", "ffmpeg"]:
        ffmpeg_path = skill_dir / name
        if ffmpeg_path.exists():
            return str(ffmpeg_path)

    # 3. PATH
    for path in os.environ.get("PATH", "").split(os.pathsep):
        for name in ["ffmpeg.exe", "ffmpeg"]:
            ffmpeg_path = os.path.join(path, name)
            if os.path.exists(ffmpeg_path):
                return ffmpeg_path

    return None


def format_duration(seconds: float) -> str:
    """格式化时长为 HH:MM:SS 或 MM:SS 格式"""
    seconds = int(seconds)
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ==================== 配置管理 ====================

def get_skill_dir() -> Path:
    """获取脚本所在目录"""
    return Path(__file__).parent.resolve()


def get_config() -> Dict[str, Any]:
    """加载配置"""
    skill_dir = get_skill_dir()
    config_path = skill_dir / "config.json"
    cache_dir = skill_dir / "cache"

    config = DEFAULT_CONFIG.copy()
    config["cache_dir"] = str(cache_dir)

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            logger.warning(f"加载配置失败：{e}")

    # 确保目录存在
    (cache_dir / "audio").mkdir(parents=True, exist_ok=True)
    (cache_dir / "text").mkdir(parents=True, exist_ok=True)

    return config


def save_config(config: Dict[str, Any]) -> None:
    """保存配置"""
    skill_dir = get_skill_dir()
    config_path = skill_dir / "config.json"

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_cache_hash(path: str) -> str:
    """获取路径的哈希值，用于缓存命名"""
    return hashlib.md5(path.encode('utf-8')).hexdigest()


# ==================== URL 和路径识别 ====================

def is_local_video_path(text: str) -> bool:
    """判断是否为本地视频文件路径"""
    path = Path(text.strip())
    return path.exists() and path.suffix.lower() in VIDEO_EXTENSIONS


def is_local_audio_path(text: str) -> bool:
    """判断是否为本地音频文件路径"""
    path = Path(text.strip())
    return path.exists() and path.suffix.lower() in AUDIO_EXTENSIONS


def get_video_id_from_url(url: str) -> Optional[str]:
    """从 URL 中提取 BV 号"""
    bv_pattern = r'BV[a-zA-Z0-9]{10,12}'
    match = re.search(bv_pattern, url)
    return match.group() if match else None


def extract_bilibili_url(text: str) -> Optional[str]:
    """
    从混合文本中提取 B 站链接

    支持格式：
    - "帮我看看这个视频 https://www.bilibili.com/video/BV1xx411c7mD"
    - "这个 BV1xx411c7mD 怎么样"
    - "看看 b23.tv/abc123"
    """
    bv_pattern = r'BV[a-zA-Z0-9]{10,12}'

    # 1. 直接提取 BV 号
    bv_match = re.search(bv_pattern, text)
    if bv_match:
        return f"https://www.bilibili.com/video/{bv_match.group()}"

    # 2. 提取标准链接
    url_pattern = r'https?://(?:www\.|m\.)?bilibili\.com/video/[^\s<>"{}|\\^`\[\]]+'
    url_match = re.search(url_pattern, text)
    if url_match:
        bv_match = re.search(bv_pattern, url_match.group())
        if bv_match:
            return f"https://www.bilibili.com/video/{bv_match.group()}"

    # 3. 提取短链接
    short_pattern = r'(?:https?://)?b23\.tv/[a-zA-Z0-9]+'
    short_match = re.search(short_pattern, text)
    if short_match:
        short_url = short_match.group()
        if not short_url.startswith('http'):
            short_url = 'https://' + short_url

        # 尝试解析短链接
        try:
            import requests
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(short_url, headers=headers, allow_redirects=True, timeout=10)
            real_url = str(resp.url)
            bv_match = re.search(bv_pattern, real_url)
            if bv_match:
                return f"https://www.bilibili.com/video/{bv_match.group()}"
        except Exception as e:
            logger.warning(f"解析短链接失败：{e}")

    return None


def identify_input(text: str) -> Dict[str, Any]:
    """
    识别输入类型

    返回：
        {"type": "bilibili" | "local" | "unknown", "url" | "path": str, "original": str}
    """
    text = text.strip()

    # 1. 检查是否为本地视频文件（优先检查真实存在的路径）
    if is_local_video_path(text):
        return {"type": "local", "path": text, "original": text}

    # 2. 检查是否为 B 站链接或包含 B 站链接
    url = extract_bilibili_url(text)
    if url:
        return {"type": "bilibili", "url": url, "original": text}

    # 3. 检查是否为本地音频文件（真实存在）
    if is_local_audio_path(text):
        return {"type": "audio", "path": text, "original": text}

    # 4. 检查是否为视频文件扩展名
    if Path(text).suffix.lower() in VIDEO_EXTENSIONS:
        return {"type": "local", "path": text, "original": text}

    # 5. 检查是否为音频文件扩展名
    if Path(text).suffix.lower() in AUDIO_EXTENSIONS:
        return {"type": "audio", "path": text, "original": text}

    return {"type": "unknown", "original": text}


# ==================== B 站爬虫模块 ====================

class BilibiliCrawler:
    """B 站视频爬取器"""

    # 默认备用 cookie
    DEFAULT_COOKIE = "buvid3=C0597D6F-655D-D954-E253-34B57995CDB583348infoc"

    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir) / "audio"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._session = None
        self._cookie: Optional[str] = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def get_bilibili_cookie(self) -> str:
        """从 B 站主页获取 cookie"""
        if self._cookie:
            return self._cookie

        try:
            import aiohttp
            session = await self._get_session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            async with session.get(
                "https://www.bilibili.com/",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                cookies = resp.cookies
                if cookies:
                    # SimpleCookie 对象需要用 keys() 迭代
                    cookie_pairs = [f"{key}={cookies[key].value}" for key in cookies.keys()]
                    self._cookie = "; ".join(cookie_pairs)
                    logger.debug(f"获取到 cookie: {self._cookie[:50]}...")
                    return self._cookie
        except Exception as e:
            logger.warning(f"获取 B 站 cookie 失败: {e}")

        # 使用默认 cookie
        self._cookie = self.DEFAULT_COOKIE
        return self._cookie

    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """获取视频信息"""
        bv_id = get_video_id_from_url(url)
        if not bv_id:
            return None

        page_url = f"https://www.bilibili.com/video/{bv_id}"

        try:
            import aiohttp
            session = await self._get_session()

            # 获取 cookie
            cookie = await self.get_bilibili_cookie()

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": page_url,
                "Cookie": cookie
            }

            async with session.get(page_url, headers=headers, timeout=30) as resp:
                html = await resp.text()

            # 提取标题
            title_match = re.findall(r'<title[^>]*>([^<]+)</title>', html)
            title = title_match[0].replace("_哔哩哔哩_bilibili", "").strip() if title_match else bv_id

            # 清理文件名
            title = re.sub(r'[\\/:*?"<>|]', '_', title)

            # 提取播放信息
            info_match = re.findall(r'window\.__playinfo__\s*=\s*(.+?)</script>', html)

            duration = 0
            audio_url = None

            if info_match:
                try:
                    data = json.loads(info_match[0])
                    if 'data' in data and 'dash' in data['data']:
                        audio_streams = data['data']['dash'].get('audio', [])
                        if audio_streams:
                            audio_url = audio_streams[0].get('baseUrl')

                        duration = data['data'].get('dash', {}).get('duration', 0)
                except json.JSONDecodeError:
                    pass

            return {
                "bv_id": bv_id,
                "title": title,
                "url": page_url,
                "duration": duration,
                "audio_url": audio_url
            }

        except Exception as e:
            logger.error(f"获取视频信息失败：{e}")
            return None

    async def download_audio(self, video_info: Dict[str, Any]) -> Optional[str]:
        """下载音频，使用标题作为文件名，支持重名检测"""
        if not video_info.get("audio_url"):
            return None

        try:
            import aiohttp
            session = await self._get_session()

            # 获取 cookie
            cookie = await self.get_bilibili_cookie()

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": video_info["url"],
                "Cookie": cookie
            }

            # 使用标题作为文件名
            title = video_info.get("title", video_info["bv_id"])

            # 检查是否有缓存的文件（基于 BV 号查找）
            bv_cache_pattern = f"{video_info['bv_id']}_*.mp3"
            existing_cache = list(self.cache_dir.glob(bv_cache_pattern))
            if existing_cache:
                logger.info(f"使用缓存音频：{existing_cache[0]}")
                return str(existing_cache[0])

            # 也检查以标题命名的缓存
            title_cache_pattern = f"{title}.mp3"
            title_cache_path = self.cache_dir / title_cache_pattern
            if title_cache_path.exists():
                logger.info(f"使用缓存音频：{title_cache_path}")
                return str(title_cache_path)

            logger.info(f"下载音频：{title}")

            async with session.get(video_info["audio_url"], headers=headers, timeout=60) as resp:
                if resp.status == 200:
                    audio_content = await resp.read()

                    # 直接保存为 m4a 格式（B站返回的就是aac编码的m4a）
                    m4a_filename = f"{title}.m4a"
                    m4a_path = self.cache_dir / m4a_filename

                    counter = 1
                    while m4a_path.exists():
                        m4a_filename = f"{title}_{counter}.m4a"
                        m4a_path = self.cache_dir / m4a_filename
                        counter += 1

                    with open(m4a_path, 'wb') as f:
                        f.write(audio_content)

                    logger.info(f"音频下载完成：{m4a_filename}")
                    return str(m4a_path)

            return None

        except Exception as e:
            logger.error(f"下载音频失败：{e}")
            return None


# ==================== 本地视频处理模块 ====================

class LocalVideoProcessor:
    """本地视频处理器"""

    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir) / "audio"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = find_ffmpeg()

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取本地视频信息"""
        path = Path(video_path)
        return {
            "bv_id": f"local_{get_cache_hash(str(path))}",
            "title": path.stem,
            "url": str(path),
            "duration": 0,  # 需要通过 ffmpeg 获取
            "audio_url": None
        }

    def extract_audio(self, video_path: str) -> Optional[str]:
        """从本地视频中提取音频"""
        if not self.ffmpeg_path:
            logger.warning("未找到 ffmpeg，无法提取音频")
            return None

        try:
            video_path = Path(video_path)
            cache_hash = get_cache_hash(str(video_path))
            audio_path = self.cache_dir / f"{cache_hash}.m4a"

            # 检查缓存
            if audio_path.exists():
                logger.info(f"使用缓存音频：{audio_path}")
                return str(audio_path)

            logger.info(f"提取音频：{video_path.name}")

            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vn",  # 不处理视频
                "-acodec", "aac",
                "-y",  # 覆盖已存在文件
                str(audio_path)
            ]

            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(cmd, capture_output=True, creationflags=creation_flags)

            if result.returncode == 0 and audio_path.exists():
                logger.info("音频提取完成")
                return str(audio_path)
            else:
                stderr = result.stderr.decode('utf-8', errors='ignore')
                logger.error(f"ffmpeg 提取失败：{stderr}")
                return None

        except Exception as e:
            logger.error(f"提取音频失败：{e}")
            return None

    def get_duration(self, audio_path: str) -> Optional[float]:
        """获取音频时长（秒）"""
        if not self.ffmpeg_path:
            return None

        try:
            cmd = [self.ffmpeg_path, "-i", audio_path, "-hide_banner", "-f", "null", "-"]
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(cmd, capture_output=True, creationflags=creation_flags)

            stderr = result.stderr.decode('utf-8', errors='ignore')
            match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', stderr)
            if match:
                h, m, s, cs = map(int, match.groups())
                return h * 3600 + m * 60 + s + cs / 100
        except Exception as e:
            logger.error(f"获取时长失败：{e}")

        return None


# ==================== 音频处理模块 ====================

class AudioProcessor:
    """音频格式转换器"""

    def __init__(self):
        self.ffmpeg_path = find_ffmpeg()

    def convert_to_wav(self, audio_path: str) -> Optional[str]:
        """将音频转换为 16kHz 单声道 WAV 格式（FunASR 要求）"""
        if not self.ffmpeg_path:
            return self._convert_with_librosa(audio_path)

        try:
            audio_path = Path(audio_path)
            wav_path = audio_path.with_suffix('.wav')

            if wav_path.exists():
                logger.info(f"使用已转换文件：{wav_path}")
                return str(wav_path)

            logger.info(f"转换音频格式：{audio_path} -> {wav_path}")

            cmd = [
                self.ffmpeg_path,
                "-i", str(audio_path),
                "-ar", "16000",
                "-ac", "1",
                "-y",
                str(wav_path)
            ]

            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(cmd, capture_output=True, creationflags=creation_flags)

            if result.returncode == 0 and wav_path.exists():
                logger.info("音频格式转换完成")
                return str(wav_path)
            else:
                stderr = result.stderr.decode('utf-8', errors='ignore')
                logger.error(f"ffmpeg 转换失败：{stderr}")
                return self._convert_with_librosa(audio_path)

        except Exception as e:
            logger.error(f"音频转换失败：{e}")
            return self._convert_with_librosa(audio_path)

    def _convert_with_librosa(self, audio_path: str) -> Optional[str]:
        """使用 librosa 转换音频格式"""
        try:
            audio_path = Path(audio_path)
            wav_path = audio_path.with_suffix('.wav')

            if wav_path.exists():
                return str(wav_path)

            logger.info("使用 librosa 转换音频格式...")

            try:
                import librosa
                import soundfile as sf

                y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
                sf.write(str(wav_path), y, 16000)
                logger.info(f"音频转换完成：{wav_path}")
                return str(wav_path)

            except Exception as e:
                logger.error(f"librosa 转换失败：{e}")
                return None

        except Exception as e:
            logger.error(f"音频转换失败：{e}")
            return None


# ==================== 语音识别模块 ====================

class SpeechRecognizer:
    """语音识别器（使用 FunASR）"""

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.model_dir = skill_dir / "model"
        self.vad_path = self.model_dir / "vad" / "iic" / "speech_fsmn_vad_zh-cn-16k-common-pytorch"
        self.asr_path = self.model_dir / "sensevoice" / "iic" / "SenseVoiceSmall"
        self._model = None

    def check_models(self) -> Tuple[bool, List[str]]:
        """检查模型是否存在"""
        missing = []
        if not self.vad_path.exists():
            missing.append("VAD 模型")
        if not self.asr_path.exists():
            missing.append("SenseVoice 模型")
        return len(missing) == 0, missing

    def download_models(self) -> Tuple[bool, str]:
        """下载模型"""
        try:
            from modelscope.hub.snapshot_download import snapshot_download

            logger.info("下载 VAD 模型...")
            vad_dir = self.model_dir / "vad"
            vad_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(VAD_MODEL_ID, cache_dir=str(vad_dir), revision='master')

            logger.info("下载 SenseVoice 模型...")
            asr_dir = self.model_dir / "sensevoice"
            asr_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(ASR_MODEL_ID, cache_dir=str(asr_dir), revision='master')

            return True, "模型下载完成"
        except Exception as e:
            return False, f"模型下载失败：{e}"

    def _init_model(self) -> bool:
        """初始化模型"""
        if self._model is not None:
            return True

        try:
            from funasr import AutoModel

            # 检测 GPU
            device = "cpu"
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda:0"
                    logger.info("使用 GPU 加速")
            except ImportError:
                pass

            logger.info(f"初始化语音识别模型 ({device})...")

            self._model = AutoModel(
                disable_update=True,
                model=str(self.asr_path),
                frontend_conf={"fs": 16000},
                vad_model=str(self.vad_path),
                vad_kwargs={
                    "max_single_segment_time": VAD_MAX_SEGMENT_TIME,
                    "max_end_silence_time": VAD_MAX_END_SILENCE_TIME,
                    "max_start_silence_time": VAD_MAX_START_SILENCE_TIME,
                },
                device=device
            )

            logger.info("模型初始化完成")
            return True

        except ImportError as e:
            logger.error(f"缺少依赖：{e}")
            return False
        except Exception as e:
            logger.error(f"模型初始化失败：{e}")
            return False

    def transcribe(self, audio_path: str) -> Tuple[Optional[str], Optional[str]]:
        """转写音频"""
        try:
            if not self._init_model():
                return None, "模型初始化失败"

            from funasr.utils.postprocess_utils import rich_transcription_postprocess

            logger.info(f"开始转写：{audio_path}")

            result = self._model.generate(
                input=audio_path,
                cache={},
                language="auto",
                use_itn=True,
                batch_size_s=ASR_BATCH_SIZE_S,
                merge_vad=True,
                merge_length_s=ASR_MERGE_LENGTH_S,
            )

            if not result or not result[0].get("text"):
                return None, "识别结果为空"

            text = rich_transcription_postprocess(result[0]["text"])
            text = re.sub(r'[\U0001F000-\U0001F9FF]', '', text)

            logger.info("转写完成")
            return text, None

        except Exception as e:
            logger.error(f"转写失败：{e}")
            return None, str(e)


# ==================== 缓存管理模块 ====================

class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)

    def clear_all(self) -> Dict[str, Any]:
        """清理所有缓存"""
        cleared_files = []
        freed_size = 0

        for subdir in ["audio", "text"]:
            dir_path = self.cache_dir / subdir
            if not dir_path.exists():
                continue

            for file_path in dir_path.glob("*"):
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    cleared_files.append(str(file_path))
                    freed_size += size
                except Exception as e:
                    logger.error(f"清理缓存失败：{e}")

        return {
            "status": "success",
            "cleared_files": len(cleared_files),
            "freed_mb": round(freed_size / 1024 / 1024, 2)
        }

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        audio_dir = self.cache_dir / "audio"
        text_dir = self.cache_dir / "text"

        audio_files = list(audio_dir.glob("*")) if audio_dir.exists() else []
        text_files = list(text_dir.glob("*")) if text_dir.exists() else []

        audio_size = sum(f.stat().st_size for f in audio_files if f.is_file())
        text_size = sum(f.stat().st_size for f in text_files if f.is_file())

        return {
            "audio": {
                "files": len(audio_files),
                "size_mb": round(audio_size / 1024 / 1024, 2)
            },
            "text": {
                "files": len(text_files),
                "size_mb": round(text_size / 1024 / 1024, 2)
            },
            "total_mb": round((audio_size + text_size) / 1024 / 1024, 2)
        }


# ==================== 主处理类 ====================

class VideoAnalyzer:
    """视频分析器（支持 B 站和本地）"""

    def __init__(self):
        self.config = get_config()
        self.skill_dir = get_skill_dir()
        self.cache_manager = CacheManager(self.config["cache_dir"])
        self.bilibili_crawler = BilibiliCrawler(self.config["cache_dir"])
        self.local_processor = LocalVideoProcessor(self.config["cache_dir"])
        self.audio_processor = AudioProcessor()
        self.recognizer = SpeechRecognizer(self.skill_dir)

    async def analyze(self, input_text: str) -> Dict[str, Any]:
        """分析视频或音频"""
        start_time = datetime.now()

        # 1. 识别输入类型
        input_info = identify_input(input_text)

        if input_info["type"] == "unknown":
            return {
                "status": "error",
                "error": "invalid_input",
                "message": "无法识别输入，请提供有效的 B 站链接、本地视频或音频文件路径",
                "suggestion": "检查链接或路径是否正确"
            }

        # 2. 根据类型处理
        if input_info["type"] == "bilibili":
            return await self._analyze_bilibili(input_info["url"], start_time)
        elif input_info["type"] == "local":
            return await self._analyze_local(input_info["path"], start_time)
        elif input_info["type"] == "audio":
            return await self._analyze_audio(input_info["path"], start_time)

    async def _analyze_bilibili(self, url: str, start_time: datetime) -> Dict[str, Any]:
        """分析 B 站视频"""
        logger.info(f"获取视频信息：{url}")
        video_info = await self.bilibili_crawler.get_video_info(url)

        if not video_info:
            return {
                "status": "error",
                "error": "fetch_failed",
                "message": "无法获取视频信息",
                "suggestion": "请检查链接是否有效，或稍后重试"
            }

        # 检查时长
        duration = video_info.get("duration", 0)
        max_duration = self.config["max_duration_minutes"] * 60

        if duration > max_duration:
            return {
                "status": "error",
                "error": "duration_exceeded",
                "message": f"视频时长 {duration // 60} 分钟超过限制 {self.config['max_duration_minutes']} 分钟",
                "suggestion": "在配置中调整 max_duration_minutes"
            }

        # 下载音频
        logger.info("下载音频...")
        audio_path = await self.bilibili_crawler.download_audio(video_info)

        if not audio_path:
            return {
                "status": "error",
                "error": "download_failed",
                "message": "音频下载失败",
                "suggestion": "请检查网络连接或视频是否可访问"
            }

        return await self._process_audio(video_info, audio_path, start_time)

    async def _analyze_local(self, video_path: str, start_time: datetime) -> Dict[str, Any]:
        """分析本地视频"""
        logger.info(f"处理本地视频：{video_path}")

        # 获取视频信息
        video_info = self.local_processor.get_video_info(video_path)

        # 提取音频
        logger.info("提取音频...")
        audio_path = self.local_processor.extract_audio(video_path)

        if not audio_path:
            return {
                "status": "error",
                "error": "extract_failed",
                "message": "音频提取失败",
                "suggestion": "请确保已安装 ffmpeg 且视频文件可访问"
            }

        # 获取时长
        duration = self.local_processor.get_duration(audio_path) or 0
        video_info["duration"] = duration

        # 检查时长
        max_duration = self.config["max_duration_minutes"] * 60
        if duration > max_duration:
            return {
                "status": "error",
                "error": "duration_exceeded",
                "message": f"视频时长 {duration // 60} 分钟超过限制 {self.config['max_duration_minutes']} 分钟",
                "suggestion": "在配置中调整 max_duration_minutes"
            }

        return await self._process_audio(video_info, audio_path, start_time)

    async def _ensure_audio_format(self, audio_path: str) -> str:
        """检测并转换音频格式，确保扩展名与实际格式匹配"""
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            logger.warning("未找到 ffmpeg，无法检测音频格式")
            return audio_path

        # 使用 ffmpeg 检测实际格式
        try:
            cmd = [
                ffmpeg_path, "-i", audio_path,
                "-f", "null", "-"
            ]
            result = subprocess.run(
                cmd, capture_output=True, timeout=30
            )
            output = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""

            # 检测实际格式
            actual_format = None
            if "Stream #0:0: Audio: aac" in output or "Input #0, mov" in output:
                actual_format = "m4a"
            elif "Stream #0:0: Audio: mp3" in output:
                actual_format = "mp3"
            elif "Stream #0:0: Audio: wav" in output:
                actual_format = "wav"
            elif "Stream #0:0: Audio: flac" in output:
                actual_format = "flac"
            elif "Stream #0:0: Audio: opus" in output:
                actual_format = "ogg"

            if not actual_format:
                return audio_path

            # 检查扩展名是否匹配
            current_ext = Path(audio_path).suffix.lower()
            expected_ext = f".{actual_format}"

            if current_ext != expected_ext:
                logger.info(f"检测到实际格式: {actual_format}，但文件扩展名为: {current_ext}，进行格式转换...")

                # 转换格式
                new_path = Path(audio_path).with_suffix(expected_ext)
                cmd = [
                    ffmpeg_path, "-i", audio_path,
                    "-acodec", "copy", "-y", str(new_path)
                ]
                result = subprocess.run(
                    cmd, capture_output=True, timeout=300
                )
                if result.returncode == 0 and new_path.exists():
                    logger.info(f"格式转换成功: {new_path}")
                    return str(new_path)
                else:
                    stderr_output = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "未知错误"
                    logger.warning(f"格式转换失败: {stderr_output}")

            return audio_path

        except Exception as e:
            logger.warning(f"音频格式检测失败: {e}")
            return audio_path

    async def _analyze_audio(self, audio_path: str, start_time: datetime) -> Dict[str, Any]:
        """分析本地音频"""
        logger.info(f"处理本地音频：{audio_path}")

        # FunASR 支持 m4a 格式，直接使用

        # 获取音频时长
        duration = self.local_processor.get_duration(audio_path) or 0

        # 检查时长
        max_duration = self.config["max_duration_minutes"] * 60
        if duration > max_duration:
            return {
                "status": "error",
                "error": "duration_exceeded",
                "message": f"音频时长 {duration // 60} 分钟超过限制 {self.config['max_duration_minutes']} 分钟",
                "suggestion": "在配置中调整 max_duration_minutes"
            }

        # 构造视频信息（音频没有标题和BV号）
        audio_name = Path(audio_path).stem
        video_info = {
            "title": audio_name,
            "bv_id": audio_name,
            "url": None,
            "duration": duration
        }

        return await self._process_audio(video_info, audio_path, start_time)

    async def _process_audio(self, video_info: Dict[str, Any], audio_path: str,
                             start_time: datetime) -> Dict[str, Any]:
        """处理音频（转写）"""
        try:
            # 检查模型
            models_ready, missing = self.recognizer.check_models()
            if not models_ready:
                logger.info(f"缺少模型：{missing}，开始下载...")
                success, msg = self.recognizer.download_models()
                if not success:
                    return {
                        "status": "error",
                        "error": "model_download_failed",
                        "message": msg,
                        "suggestion": "请手动运行：python bilibili_video.py --init"
                    }

            # 转写音频
            logger.info("转写音频...")
            text, error = self.recognizer.transcribe(audio_path)

            if not text:
                return {
                    "status": "error",
                    "error": "transcribe_failed",
                    "message": f"转写失败：{error}",
                    "suggestion": "请确保音频格式正确"
                }

            # 保存转写结果
            cache_hash = get_cache_hash(video_info["url"] or video_info["bv_id"])
            text_dir = Path(self.config["cache_dir"]) / "text"
            txt_path = text_dir / f"{cache_hash}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)

            result = {
                "status": "success",
                "type": "bilibili" if video_info["bv_id"].startswith("BV") else "local",
                "title": video_info["title"],
                "bv_id": video_info["bv_id"],
                "url": video_info["url"],
                "duration": format_duration(video_info["duration"]),
                "transcription": text,
                "transcription_path": str(txt_path),
                "processing_time": str(datetime.now() - start_time)
            }

            return result
        finally:
            await self.bilibili_crawler.close()

    def check_status(self) -> Dict[str, Any]:
        """检查状态"""
        models_ready, missing = self.recognizer.check_models()
        cache_info = self.cache_manager.get_cache_info()

        return {
            "status": "ready" if models_ready else "need_init",
            "models": {
                "vad": "installed" if self.recognizer.vad_path.exists() else "missing",
                "sensevoice": "installed" if self.recognizer.asr_path.exists() else "missing"
            },
            "missing_models": missing,
            "config": {
                "max_duration_minutes": self.config["max_duration_minutes"]
            },
            "cache": cache_info,
            "ffmpeg": self.audio_processor.ffmpeg_path or self.local_processor.ffmpeg_path or "not found"
        }

    def clear_cache(self) -> Dict[str, Any]:
        """清理缓存"""
        return self.cache_manager.clear_all()


# ==================== CLI 入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="B 站/本地视频理解工具 - 提取音频、转写文字",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python bilibili_video.py BV1xx411c7mD
  python bilibili_video.py "https://bilibili.com/video/BV1xx411c7mD"
  python bilibili_video.py "C:\\Videos\\lecture.mp4"
  python bilibili_video.py --status
  python bilibili_video.py --clear-cache
  python bilibili_video.py --init
        """
    )

    parser.add_argument("input", nargs="?", help="B 站链接、BV 号或本地视频文件路径")
    parser.add_argument("--status", action="store_true", help="检查状态")
    parser.add_argument("--clear-cache", action="store_true", help="清理所有缓存")
    parser.add_argument("--init", action="store_true", help="初始化环境（下载模型）")

    args = parser.parse_args()

    analyzer = VideoAnalyzer()

    if args.status:
        result = analyzer.check_status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.clear_cache:
        result = analyzer.clear_cache()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.init:
        success, msg = analyzer.recognizer.download_models()
        result = {"status": "success" if success else "error", "message": msg}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if not args.input:
        parser.print_help()
        return

    # 运行分析
    result = asyncio.run(analyzer.analyze(args.input))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()