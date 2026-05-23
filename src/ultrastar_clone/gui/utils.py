"""GUI helper functions with no Qt dependency.

无 Qt 依赖的 GUI 辅助函数。
"""

from __future__ import annotations

from math import isfinite
from pathlib import Path

from ultrastar_clone.core.song_parser import Song


def format_media_time(milliseconds: int) -> str:
    total_seconds = max(0, milliseconds) // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def describe_lyric_sync_status(song: Song, timed_lyrics: tuple) -> tuple[str, str]:
    """Return status text and fallback current lyric text for parsed lyrics."""

    if timed_lyrics:
        return "Ready", ""
    if song.bpm is None or not isfinite(song.bpm) or song.bpm <= 0:
        return "Lyrics cannot sync because BPM is missing or invalid", "No synchronized lyrics"
    return "No synchronized lyrics found in TXT", "No synchronized lyrics"


def entry_uses_video_output(entry, media_path: Path) -> bool:
    video_path = getattr(entry, "video_path", None)
    return video_path is not None and Path(video_path) == Path(media_path)


def lyric_transition_required(previous_current: str, next_current: str) -> bool:
    """Return whether a lyric text update should animate."""

    return previous_current != next_current


def lyric_display_payload(window, position_ms: int) -> tuple[str, str, str]:
    """Return previous/current/next text without clearing the current line during gaps."""

    del position_ms
    if window.current:
        previous = window.previous.text if window.previous else ""
        current = window.current.text
        next_line = window.next.text if window.next else ""
        return previous, current, next_line

    if window.previous:
        next_line = window.next.text if window.next else ""
        return "", window.previous.text, next_line

    next_line = window.next.text if window.next else ""
    return "", "", next_line
