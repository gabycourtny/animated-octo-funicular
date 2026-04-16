#!/usr/bin/env python3
"""
clipagent - Automatically converts long-form videos into short viral clips for social media.

Usage:
    python clipagent.py --video my_video.mp4 --output ./clips
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Load environment variables early
from dotenv import load_dotenv
load_dotenv()

import anthropic
import openai
import ffmpeg
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from rich.text import Text

console = Console()

MODEL = "claude-sonnet-4-20250514"
WHISPER_MODEL = "whisper-1"

CLAUDE_SYSTEM_PROMPT = """You are an expert social media content strategist specializing in viral Reels and TikTok clips.
Analyze the transcript and identify the 5 best moments for 15-30 second clips.

Selection criteria:
- Must start with a strong hook sentence that stops the scroll
- Must make complete sense without any prior context
- Must be emotional, surprising, educational, or entertaining
- Must end at a natural closing moment
- Ideal length: 15-30 seconds (never exceed 35 seconds)

Return ONLY valid JSON in this exact format:
{
  "clips": [
    {
      "clip_number": 1,
      "start_time": "00:01:23",
      "end_time": "00:01:48",
      "duration_seconds": 25,
      "hook": "The opening sentence that makes this a great hook",
      "why_viral": "Brief explanation of why this clip will perform well",
      "caption_english": "Suggested Instagram/TikTok caption in English with hashtags",
      "caption_spanish": "Suggested Instagram/TikTok caption in Spanish with hashtags",
      "clip_type": "one of: educational / emotional / surprising / behind_the_scenes / testimonial"
    }
  ]
}"""


def check_ffmpeg():
    """Verify FFmpeg is installed and accessible."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            raise RuntimeError("FFmpeg returned non-zero exit code")
    except FileNotFoundError:
        console.print("[bold red]Error:[/bold red] FFmpeg is not installed or not in PATH.")
        console.print("Install it from: https://ffmpeg.org/download.html")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        console.print("[bold red]Error:[/bold red] FFmpeg check timed out.")
        sys.exit(1)


def check_api_keys():
    """Validate required API keys are present."""
    missing = []
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if missing:
        console.print(f"[bold red]Error:[/bold red] Missing API keys: {', '.join(missing)}")
        console.print("Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract audio from video as MP3 using FFmpeg."""
    audio_path = output_dir / "audio.mp3"
    try:
        (
            ffmpeg
            .input(str(video_path))
            .output(
                str(audio_path),
                acodec="libmp3lame",
                audio_bitrate="192k",
                ac=2,
                ar="44100",
                vn=None,
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr.decode() if e.stderr else str(e)}")
    return audio_path


def transcribe_audio(audio_path: Path) -> list[dict]:
    """Transcribe audio using OpenAI Whisper with word-level timestamps."""
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"],
        )
    # Return segments (each segment has start/end and text)
    return response.segments if hasattr(response, "segments") else []


def format_timestamp(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS string."""
    td = timedelta(seconds=int(seconds))
    total_secs = int(td.total_seconds())
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def save_transcript(segments: list[dict], output_dir: Path) -> Path:
    """Save timestamped transcript to a .txt file."""
    transcript_path = output_dir / "transcript.txt"
    lines = []
    for seg in segments:
        start = format_timestamp(seg.get("start", 0))
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"[{start}] {text}")
    transcript_path.write_text("\n".join(lines), encoding="utf-8")
    return transcript_path


def analyze_with_claude(transcript_path: Path) -> dict:
    """Send transcript to Claude for viral clip identification."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    transcript_text = transcript_path.read_text(encoding="utf-8")

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=CLAUDE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here is the timestamped transcript to analyze:\n\n{transcript_text}",
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # Extract JSON even if Claude wraps it in markdown code blocks
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude returned invalid JSON: {e}\nResponse: {response_text[:500]}")


def timestamp_to_seconds(ts: str) -> float:
    """Convert HH:MM:SS timestamp string to float seconds."""
    parts = ts.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


def get_video_dimensions(video_path: Path) -> tuple[int, int]:
    """Return (width, height) of input video."""
    try:
        probe = ffmpeg.probe(str(video_path))
        video_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
        if video_streams:
            return int(video_streams[0]["width"]), int(video_streams[0]["height"])
    except Exception:
        pass
    return 1920, 1080  # fallback assumption


def cut_clip(
    video_path: Path,
    start_time: str,
    end_time: str,
    output_path: Path,
    original_width: int,
    original_height: int,
) -> None:
    """Cut a single clip from video with social media formatting (9:16 vertical)."""
    start_sec = timestamp_to_seconds(start_time)
    end_sec = timestamp_to_seconds(end_time)
    duration = end_sec - start_sec

    if duration <= 0:
        raise ValueError(f"Invalid clip duration: start={start_time}, end={end_time}")

    target_w, target_h = 1080, 1920

    # Build video filter for 9:16 crop/scale
    if original_width >= original_height:
        # Horizontal video: crop to center square, then scale to 1080x1920
        # Crop height = original_height, width = original_height * 9/16
        crop_w = int(original_height * 9 / 16)
        crop_h = original_height
        # If crop_w > original_width, just use original_width
        crop_w = min(crop_w, original_width)
        vf = (
            f"crop={crop_w}:{crop_h}:(iw-{crop_w})/2:(ih-{crop_h})/2,"
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=disable"
        )
    else:
        # Vertical video: scale to fit 1080x1920
        vf = (
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"
        )

    try:
        (
            ffmpeg
            .input(str(video_path), ss=start_sec, t=duration)
            .output(
                str(output_path),
                vcodec="libx264",
                acodec="aac",
                audio_bitrate="192k",
                ac=2,
                vf=vf,
                pix_fmt="yuv420p",
                movflags="+faststart",
                preset="fast",
                crf=23,
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg clip cutting failed: {e.stderr.decode() if e.stderr else str(e)}")


def generate_report(
    clips_data: dict,
    output_dir: Path,
    video_path: Path,
    processing_time: float,
) -> Path:
    """Generate clips_report.md with full details of each clip."""
    report_path = output_dir / "clips_report.md"
    lines = [
        "# ClipAgent Report",
        "",
        f"**Source Video:** `{video_path.name}`",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Processing Time:** {processing_time:.1f} seconds",
        f"**Clips Found:** {len(clips_data.get('clips', []))}",
        "",
        "---",
        "",
    ]

    for clip in clips_data.get("clips", []):
        n = clip.get("clip_number", "?")
        lines += [
            f"## Clip {n} — {clip.get('clip_type', 'unknown').upper()}",
            "",
            f"- **Timestamps:** `{clip.get('start_time')}` → `{clip.get('end_time')}`",
            f"- **Duration:** {clip.get('duration_seconds')} seconds",
            f"- **File:** `clip_{n:02d}.mp4`",
            "",
            f"**Hook:** {clip.get('hook', '')}",
            "",
            f"**Why It'll Go Viral:** {clip.get('why_viral', '')}",
            "",
            "**Caption (English):**",
            f"> {clip.get('caption_english', '')}",
            "",
            "**Caption (Spanish):**",
            f"> {clip.get('caption_spanish', '')}",
            "",
            "---",
            "",
        ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def print_summary_table(clips_data: dict) -> None:
    """Render a rich table summarizing all clips."""
    table = Table(
        title="[bold cyan]ClipAgent — Viral Clips Summary[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
        expand=True,
    )
    table.add_column("#", style="bold", width=4)
    table.add_column("Start", width=9)
    table.add_column("End", width=9)
    table.add_column("Secs", width=6)
    table.add_column("Type", width=18)
    table.add_column("Hook", ratio=2)
    table.add_column("File", width=12)

    type_colors = {
        "educational": "blue",
        "emotional": "magenta",
        "surprising": "yellow",
        "behind_the_scenes": "green",
        "testimonial": "cyan",
    }

    for clip in clips_data.get("clips", []):
        n = clip.get("clip_number", "?")
        ctype = clip.get("clip_type", "unknown")
        color = type_colors.get(ctype, "white")
        hook = clip.get("hook", "")
        # Truncate long hooks for the table
        if len(hook) > 60:
            hook = hook[:57] + "..."
        table.add_row(
            str(n),
            clip.get("start_time", ""),
            clip.get("end_time", ""),
            str(clip.get("duration_seconds", "")),
            f"[{color}]{ctype}[/{color}]",
            hook,
            f"clip_{n:02d}.mp4",
        )

    console.print()
    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="clipagent — Convert long-form videos into viral short clips using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clipagent.py --video my_video.mp4
  python clipagent.py --video my_video.mp4 --output ./clips
        """,
    )
    parser.add_argument(
        "--video",
        required=True,
        type=Path,
        help="Path to the input video file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./clips"),
        help="Output directory for clips and reports (default: ./clips)",
    )
    args = parser.parse_args()

    start_time = time.time()

    console.print(
        Panel(
            "[bold cyan]clipagent[/bold cyan] — AI-powered viral clip generator",
            subtitle="Powered by Claude + Whisper + FFmpeg",
            border_style="cyan",
        )
    )

    # --- Pre-flight checks ---
    video_path: Path = args.video.resolve()
    if not video_path.exists():
        console.print(f"[bold red]Error:[/bold red] Video file not found: {video_path}")
        sys.exit(1)
    if not video_path.is_file():
        console.print(f"[bold red]Error:[/bold red] Path is not a file: {video_path}")
        sys.exit(1)

    check_ffmpeg()
    check_api_keys()

    output_dir: Path = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]✓[/green] Input video: [bold]{video_path.name}[/bold]")
    console.print(f"[green]✓[/green] Output directory: [bold]{output_dir}[/bold]")
    console.print()

    # --- Step 1: Audio extraction ---
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Step 1/5[/cyan] Extracting audio...", total=None)
        try:
            audio_path = extract_audio(video_path, output_dir)
            progress.update(task, completed=True, description="[cyan]Step 1/5[/cyan] [green]Audio extracted[/green]")
        except RuntimeError as e:
            console.print(f"[bold red]Error during audio extraction:[/bold red] {e}")
            sys.exit(1)

    console.print(f"  [dim]→ Saved: {audio_path.name}[/dim]")

    # --- Step 2: Transcription ---
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Step 2/5[/cyan] Transcribing with Whisper...", total=None)
        try:
            segments = transcribe_audio(audio_path)
            transcript_path = save_transcript(segments, output_dir)
            progress.update(task, completed=True, description="[cyan]Step 2/5[/cyan] [green]Transcription complete[/green]")
        except openai.OpenAIError as e:
            console.print(f"[bold red]OpenAI API error:[/bold red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]Transcription error:[/bold red] {e}")
            sys.exit(1)

    console.print(f"  [dim]→ Segments: {len(segments)} | Transcript: {transcript_path.name}[/dim]")

    # --- Step 3: Claude clip analysis ---
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Step 3/5[/cyan] Analyzing with Claude AI...", total=None)
        try:
            clips_data = analyze_with_claude(transcript_path)
            progress.update(task, completed=True, description="[cyan]Step 3/5[/cyan] [green]Clip analysis complete[/green]")
        except anthropic.APIError as e:
            console.print(f"[bold red]Anthropic API error:[/bold red] {e}")
            sys.exit(1)
        except RuntimeError as e:
            console.print(f"[bold red]Claude analysis error:[/bold red] {e}")
            sys.exit(1)

    num_clips = len(clips_data.get("clips", []))
    console.print(f"  [dim]→ Identified {num_clips} viral clips[/dim]")

    # Save raw Claude response for debugging
    (output_dir / "clips_data.json").write_text(
        json.dumps(clips_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- Step 4: Video cutting ---
    orig_w, orig_h = get_video_dimensions(video_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Step 4/5[/cyan] Cutting clips...",
            total=num_clips,
        )
        cut_errors = []
        for clip in clips_data.get("clips", []):
            n = clip.get("clip_number", 0)
            clip_filename = output_dir / f"clip_{n:02d}.mp4"
            try:
                cut_clip(
                    video_path,
                    clip["start_time"],
                    clip["end_time"],
                    clip_filename,
                    orig_w,
                    orig_h,
                )
            except (RuntimeError, ValueError, KeyError) as e:
                cut_errors.append(f"Clip {n}: {e}")
            progress.advance(task)
        progress.update(task, description="[cyan]Step 4/5[/cyan] [green]Clips cut[/green]")

    if cut_errors:
        console.print("[yellow]⚠ Some clips had errors:[/yellow]")
        for err in cut_errors:
            console.print(f"  [red]• {err}[/red]")
    else:
        console.print(f"  [dim]→ {num_clips} clips saved to {output_dir}[/dim]")

    # --- Step 5: Report generation ---
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Step 5/5[/cyan] Generating report...", total=None)
        processing_time = time.time() - start_time
        report_path = generate_report(clips_data, output_dir, video_path, processing_time)
        progress.update(task, completed=True, description="[cyan]Step 5/5[/cyan] [green]Report generated[/green]")

    console.print(f"  [dim]→ Report: {report_path.name}[/dim]")

    # --- Final summary ---
    print_summary_table(clips_data)

    console.print()
    console.print(
        Panel(
            f"[bold green]Done![/bold green] Processed in [cyan]{processing_time:.1f}s[/cyan]\n"
            f"Output directory: [bold]{output_dir}[/bold]\n"
            f"Report: [bold]{report_path}[/bold]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
