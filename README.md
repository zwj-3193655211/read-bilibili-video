# Bilibili Video Understanding Skill

An AI-powered video analysis tool that extracts audio, transcribes speech to text, and generates intelligent summaries for Bilibili videos and local video files.

## Features

- **Dual Source Support**: Analyze both Bilibili videos and local video files
- **Smart URL Extraction**: Extract BV numbers from URLs, short links, or mixed text
- **High-Quality Transcription**: Powered by FunASR SenseVoiceSmall model
- **AI Summarization**: Optional LLM-powered content summarization
- **Automatic Caching**: Efficient cache management with auto-cleanup
- **Async Processing**: Fast, non-blocking operations

## Supported Input Formats

### Bilibili Videos
| Format | Example |
|--------|---------|
| BV Number | `BV1xx411c7mD` |
| Standard URL | `https://www.bilibili.com/video/BV1xx411c7mD` |
| Mobile URL | `https://m.bilibili.com/video/BV1xx411c7mD` |
| Short Link | `https://b23.tv/abc123` |
| Mixed Text | "帮我看看这个视频 https://bilibili.com/video/BV1xx..." |

### Local Videos
- **Supported formats**: mp4, flv, avi, mkv, mov, wmv, webm, m4v, mpeg, mpg
- **Requires**: ffmpeg (for audio extraction)

## Quick Start

### Prerequisites

- Python 3.8 - 3.12
- ~1GB disk space (for models)
- ffmpeg (optional, for local videos)

### Installation

**Windows:**
```batch
setup_env.bat
```

**Linux/macOS:**
```bash
chmod +x setup_env.sh && ./setup_env.sh
```

**Manual:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python bilibili_video.py --init
```

## Usage

### Analyze a Video

```bash
# Bilibili video by BV number
python bilibili_video.py BV1xx411c7mD

# Bilibili video by URL
python bilibili_video.py "https://www.bilibili.com/video/BV1xx411c7mD"

# Local video file
python bilibili_video.py "C:\Videos\lecture.mp4"
```

### CLI Commands

```bash
# Check system status
python bilibili_video.py --status

# Clear all cache
python bilibili_video.py --clear-cache

# Clear expired cache only
python bilibili_video.py --clear-expired

# Transcription only (no summary)
python bilibili_video.py BV1xx411c7mD --transcribe-only
```

## Configuration

Edit `~/.iflow/skills/bilibili-video/config.json`:

```json
{
  "max_duration_minutes": 70,
  "auto_clear_days": 7,
  "llm_api_key": "",
  "llm_api_url": ""
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `max_duration_minutes` | 70 | Maximum video duration limit |
| `auto_clear_days` | 7 | Days before auto-cleanup |
| `llm_api_key` | "" | API key for AI summaries |
| `llm_api_url` | "" | LLM API endpoint |

## Output Example

```json
{
  "status": "success",
  "type": "bilibili",
  "title": "Video Title",
  "bv_id": "BV1xx411c7mD",
  "url": "https://www.bilibili.com/video/BV1xx411c7mD",
  "duration": "15:30",
  "transcription": "Full transcription text...",
  "transcription_path": "/path/to/cache/text/xxx.txt",
  "summary": "AI-generated summary...",
  "processing_time": "0:02:15"
}
```

## Technical Details

### Speech Recognition
- **Model**: FunASR SenseVoiceSmall
- **VAD**: speech_fsmn_vad_zh-cn-16k-common-pytorch
- **Sample Rate**: 16kHz mono
- **Languages**: Chinese (primary), auto-detection

### Dependencies

```
aiohttp>=3.8.0      # Async HTTP client
requests>=2.28.0    # HTTP requests
funasr>=1.0.0       # Speech recognition
modelscope>=1.9.0   # Model downloading
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `invalid_input` | Unrecognized input format | Check URL/path |
| `fetch_failed` | Network or video unavailable | Check connection |
| `duration_exceeded` | Video too long | Adjust config |
| `extract_failed` | ffmpeg missing | Install ffmpeg |
| `transcribe_failed` | Audio format issue | Check file |

## Limitations

1. Maximum video duration: 70 minutes (configurable)
2. Member-only videos may not be accessible
3. Local video processing requires ffmpeg
4. Initial model download ~1GB

## Directory Structure

```
bilibili-video/
├── SKILL.md              # Skill definition
├── README.md             # This file
├── bilibili_video.py     # Main script
├── requirements.txt      # Python dependencies
├── setup_env.bat         # Windows setup
└── setup_env.sh          # Linux/macOS setup
```

## Integration

This skill integrates with AI assistants like iFlow CLI and Claude Code. Users can simply ask:
- "分析这个B站视频 BV1xx..."
- "总结一下这个视频内容"
- "转写这个本地视频"

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
