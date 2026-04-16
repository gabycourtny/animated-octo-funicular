"""
Unit tests for clipagent — mocks FFmpeg, Whisper, and Claude to test all logic paths.
Run with: python -m pytest test_clipagent.py -v
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest

# Ensure the repo root is importable
sys.path.insert(0, str(Path(__file__).parent))

import clipagent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_segments(texts_with_times):
    """Build fake Whisper segment dicts."""
    segments = []
    for start, text in texts_with_times:
        seg = MagicMock()
        seg.start = start
        seg.end = start + 3.0
        seg.text = text
        seg.get = lambda k, d=None, s=start, t=text: (
            s if k == "start" else (s + 3.0 if k == "end" else (t if k == "text" else d))
        )
        segments.append(seg)
    return segments


SAMPLE_CLIPS_DATA = {
    "clips": [
        {
            "clip_number": 1,
            "start_time": "00:00:05",
            "end_time": "00:00:30",
            "duration_seconds": 25,
            "hook": "This one trick doubled my productivity overnight.",
            "why_viral": "Bold claim with immediate practical value.",
            "caption_english": "The secret nobody tells you #productivity #lifehack",
            "caption_spanish": "El secreto que nadie te dice #productividad",
            "clip_type": "educational",
        },
        {
            "clip_number": 2,
            "start_time": "00:01:00",
            "end_time": "00:01:20",
            "duration_seconds": 20,
            "hook": "I was completely wrong about this.",
            "why_viral": "Vulnerability + surprise creates engagement.",
            "caption_english": "I was wrong #mindset #growth",
            "caption_spanish": "Estaba equivocado #mentalidad",
            "clip_type": "emotional",
        },
    ]
}


# ---------------------------------------------------------------------------
# format_timestamp
# ---------------------------------------------------------------------------

def test_format_timestamp_zero():
    assert clipagent.format_timestamp(0) == "00:00:00"


def test_format_timestamp_minutes():
    assert clipagent.format_timestamp(90) == "00:01:30"


def test_format_timestamp_hours():
    assert clipagent.format_timestamp(3661) == "01:01:01"


# ---------------------------------------------------------------------------
# timestamp_to_seconds
# ---------------------------------------------------------------------------

def test_timestamp_to_seconds_hms():
    assert clipagent.timestamp_to_seconds("00:01:30") == 90.0


def test_timestamp_to_seconds_ms():
    assert clipagent.timestamp_to_seconds("01:05") == 65.0


def test_timestamp_to_seconds_large():
    assert clipagent.timestamp_to_seconds("01:00:00") == 3600.0


# ---------------------------------------------------------------------------
# save_transcript
# ---------------------------------------------------------------------------

def test_save_transcript(tmp_path):
    segments = [
        {"start": 4.0, "end": 8.0, "text": " Hi, welcome to today's video."},
        {"start": 12.0, "end": 16.0, "text": " Today we're going to talk about AI."},
    ]
    transcript_path = clipagent.save_transcript(segments, tmp_path)
    content = transcript_path.read_text()
    assert "[00:00:04]" in content
    assert "[00:00:12]" in content
    assert "Hi, welcome to today's video." in content
    assert "Today we're going to talk about AI." in content


def test_save_transcript_skips_empty_segments(tmp_path):
    segments = [
        {"start": 1.0, "end": 2.0, "text": "  "},
        {"start": 3.0, "end": 4.0, "text": "Hello world."},
    ]
    transcript_path = clipagent.save_transcript(segments, tmp_path)
    content = transcript_path.read_text()
    lines = [l for l in content.splitlines() if l.strip()]
    assert len(lines) == 1
    assert "Hello world." in lines[0]


# ---------------------------------------------------------------------------
# analyze_with_claude — JSON parsing
# ---------------------------------------------------------------------------

def test_analyze_with_claude_clean_json(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("[00:00:05] Hello world.", encoding="utf-8")

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(SAMPLE_CLIPS_DATA))]

    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_message
        result = clipagent.analyze_with_claude(transcript_path)

    assert "clips" in result
    assert len(result["clips"]) == 2
    assert result["clips"][0]["hook"] == "This one trick doubled my productivity overnight."


def test_analyze_with_claude_markdown_wrapped(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("[00:00:05] Hello world.", encoding="utf-8")

    wrapped = f"```json\n{json.dumps(SAMPLE_CLIPS_DATA)}\n```"
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=wrapped)]

    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_message
        result = clipagent.analyze_with_claude(transcript_path)

    assert "clips" in result
    assert len(result["clips"]) == 2


def test_analyze_with_claude_invalid_json(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("[00:00:05] Hello.", encoding="utf-8")

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="not valid json at all")]

    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_message
        with pytest.raises(RuntimeError, match="invalid JSON"):
            clipagent.analyze_with_claude(transcript_path)


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

def test_generate_report(tmp_path):
    report_path = clipagent.generate_report(
        SAMPLE_CLIPS_DATA,
        tmp_path,
        Path("my_video.mp4"),
        processing_time=42.5,
    )
    content = report_path.read_text()
    assert "ClipAgent Report" in content
    assert "my_video.mp4" in content
    assert "42.5 seconds" in content
    assert "Clip 1" in content
    assert "Clip 2" in content
    assert "00:00:05" in content
    assert "This one trick doubled my productivity overnight." in content
    assert "El secreto que nadie te dice" in content


# ---------------------------------------------------------------------------
# check_ffmpeg
# ---------------------------------------------------------------------------

def test_check_ffmpeg_not_installed(monkeypatch):
    import subprocess
    monkeypatch.setattr(
        subprocess,
        "run",
        MagicMock(side_effect=FileNotFoundError),
    )
    with pytest.raises(SystemExit):
        clipagent.check_ffmpeg()


def test_check_ffmpeg_installed(monkeypatch):
    import subprocess
    mock_result = MagicMock()
    mock_result.returncode = 0
    monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_result))
    # Should not raise
    clipagent.check_ffmpeg()


# ---------------------------------------------------------------------------
# check_api_keys
# ---------------------------------------------------------------------------

def test_check_api_keys_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        clipagent.check_api_keys()


def test_check_api_keys_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    # Should not raise
    clipagent.check_api_keys()


# ---------------------------------------------------------------------------
# get_video_dimensions fallback
# ---------------------------------------------------------------------------

def test_get_video_dimensions_fallback():
    with patch("clipagent.ffmpeg.probe", side_effect=Exception("probe failed")):
        w, h = clipagent.get_video_dimensions(Path("fake.mp4"))
    assert w == 1920
    assert h == 1080


# ---------------------------------------------------------------------------
# cut_clip — invalid duration raises ValueError
# ---------------------------------------------------------------------------

def test_cut_clip_invalid_duration(tmp_path):
    with pytest.raises(ValueError, match="Invalid clip duration"):
        clipagent.cut_clip(
            Path("fake.mp4"),
            "00:01:00",
            "00:00:30",  # end before start
            tmp_path / "clip.mp4",
            1920,
            1080,
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
