---
name: bilibili-video
description: |
  Analyze Bilibili videos or local video files with AI-powered transcription and summarization. Use this skill when users ask about understanding, summarizing, or transcribing video content from Bilibili (B站) or local video files. Supports BV numbers, Bilibili URLs, short links (b23.tv), and common video formats (mp4, mkv, avi, etc.).
license: MIT
compatibility: Python 3.8-3.12, requires FunASR models (~1GB), optional ffmpeg for local videos
---

# Bilibili/Local Video Understanding Skill

An AI-powered video analysis tool that extracts audio, transcribes speech to text, and generates intelligent summaries for Bilibili videos and local video files.

## When to Use

Activate this skill when users:
- Ask to analyze or understand a Bilibili video
- Provide a BV number (e.g., "BV1xx411c7mD")
- Share a Bilibili URL or short link (b23.tv)
- Request transcription of local video files
- Ask to summarize video content

## Supported Input Formats

### Bilibili Videos
- **BV Number**: `BV1xx411c7mD`
- **Standard URL**: `https://www.bilibili.com/video/BV1xx411c7mD`
- **Mobile URL**: `https://m.bilibili.com/video/BV1xx411c7mD`
- **Short Link**: `https://b23.tv/abc123`
- **Mixed Text**: "帮我看看这个视频 https://www.bilibili.com/video/BV1xx411c7mD 怎么样"

### Local Videos
- **Common formats**: mp4, flv, avi, mkv, mov, wmv, webm, m4v, mpeg, mpg
- **Full path**: `C:\Videos\lecture.mp4` or `/home/user/video.mp4`

## Quick Start

### Automatic Setup (Windows)
```batch
setup_env.bat
```

### Automatic Setup (Linux/macOS)
```bash
chmod +x setup_env.sh && ./setup_env.sh
```

### Manual Setup
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python bilibili_video.py --init
```

## Usage Examples

### Analyze a Bilibili Video
```bash
# Using BV number
python bilibili_video.py BV1xx411c7mD

# Using URL
python bilibili_video.py "https://www.bilibili.com/video/BV1xx411c7mD"
```

### Analyze a Local Video
```bash
python bilibili_video.py "C:\Videos\lecture.mp4"
```

### Check System Status
```bash
python bilibili_video.py --status
```

### Clear Cache
```bash
# Clear all cache
python bilibili_video.py --clear-cache

# Clear only expired cache (older than 7 days)
python bilibili_video.py --clear-expired
```

## Output Format

The skill returns a JSON response with:

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

## Configuration

Configuration file location: `~/.iflow/skills/bilibili-video/config.json`

```json
{
  "max_duration_minutes": 70,
  "auto_clear_days": 7,
  "model": "sensevoice",
  "llm_api_key": "",
  "llm_api_url": ""
}
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `max_duration_minutes` | 70 | Maximum video duration in minutes |
| `auto_clear_days` | 7 | Auto-clear cache older than N days |
| `llm_api_key` | "" | API key for AI summarization (optional) |
| `llm_api_url` | "" | LLM API endpoint for summarization (optional) |

## Technical Details

### Speech Recognition
- **Model**: FunASR SenseVoiceSmall
- **VAD**: speech_fsmn_vad_zh-cn-16k-common-pytorch
- **Sample Rate**: 16kHz
- **Languages**: Chinese (primary), auto-detection

### Cache Management
- Audio files cached in `cache/audio/`
- Transcriptions cached in `cache/text/`
- Automatic cleanup of files older than 7 days
- Cache keyed by content hash for deduplication

### Dependencies
- `aiohttp>=3.8.0` - Async HTTP client
- `requests>=2.28.0` - HTTP requests
- `funasr>=1.0.0` - Speech recognition
- `modelscope>=1.9.0` - Model downloading
- `librosa` (optional) - Audio format conversion
- `ffmpeg` (optional) - Local video processing

## Error Handling

The skill handles common errors gracefully:

| Error Type | Message | Suggestion |
|------------|---------|------------|
| `invalid_input` | Cannot recognize input | Check URL/path format |
| `fetch_failed` | Cannot get video info | Check network/video availability |
| `download_failed` | Audio download failed | Check network connection |
| `duration_exceeded` | Video too long | Adjust `max_duration_minutes` |
| `extract_failed` | Audio extraction failed | Install ffmpeg |
| `transcribe_failed` | Transcription failed | Check audio format |

## Limitations

1. **Duration**: Videos longer than `max_duration_minutes` are rejected
2. **Bilibili Access**: Some region-locked or member-only videos may not be accessible
3. **Local Videos**: Requires ffmpeg for audio extraction
4. **Model Size**: Initial download ~1GB for FunASR models

## Integration with AI Assistants

When integrated with AI coding assistants like iFlow CLI or Claude Code, this skill can be automatically invoked when users mention:
- "帮我分析这个B站视频"
- "总结一下这个视频内容"
- "转写这个视频的字幕"
- "看看这个本地视频说了什么"

## License

MIT License - See LICENSE file for details.
