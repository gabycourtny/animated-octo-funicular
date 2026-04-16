# clipagent

AI-powered CLI tool that converts long-form videos into short viral clips for social media (Reels, TikTok, Shorts).

## How it works

1. **Extracts audio** from your video using FFmpeg
2. **Transcribes** the audio with OpenAI Whisper (word-level timestamps)
3. **Analyzes** the transcript with Claude AI to identify the 5 best 15-30 second viral moments
4. **Cuts** each clip automatically and formats it for 9:16 vertical video (1080×1920)
5. **Generates** a full report with captions in English and Spanish

## Requirements

- Python 3.10+
- FFmpeg installed and available in your PATH
- OpenAI API key (for Whisper transcription)
- Anthropic API key (for Claude clip analysis)

### Install FFmpeg

- **macOS:** `brew install ffmpeg`
- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **Windows:** Download from https://ffmpeg.org/download.html and add to PATH

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd animated-octo-funicular

# Install Python dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and OPENAI_API_KEY
```

## Usage

```bash
python clipagent.py --video my_video.mp4
python clipagent.py --video my_video.mp4 --output ./clips
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--video` | Yes | — | Path to the input video file |
| `--output` | No | `./clips` | Output directory for clips and reports |

## Output

All files are saved to the output directory:

| File | Description |
|------|-------------|
| `audio.mp3` | Extracted audio |
| `transcript.txt` | Timestamped transcript |
| `clips_data.json` | Raw Claude AI analysis |
| `clip_01.mp4` … `clip_05.mp4` | The cut viral clips (1080×1920) |
| `clips_report.md` | Full report with hooks, captions, and explanations |

## Example output structure

```
clips/
├── audio.mp3
├── transcript.txt
├── clips_data.json
├── clip_01.mp4
├── clip_02.mp4
├── clip_03.mp4
├── clip_04.mp4
├── clip_05.mp4
└── clips_report.md
```

## Error handling

- **FFmpeg not found:** Install FFmpeg and ensure it's in your PATH
- **Missing API keys:** Copy `.env.example` to `.env` and fill in your keys
- **Video not found:** Check the path to your video file
- **API errors:** Check your API key validity and account credits

## Clip types identified by Claude

- `educational` — teaches something valuable
- `emotional` — triggers an emotional response
- `surprising` — unexpected or counterintuitive
- `behind_the_scenes` — candid, authentic moments
- `testimonial` — personal story or proof
