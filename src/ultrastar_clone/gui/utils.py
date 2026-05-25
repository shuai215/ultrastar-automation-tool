"""GUI helper functions with no Qt dependency.

无 Qt 依赖的 GUI 辅助函数。
"""

from __future__ import annotations

from pathlib import Path


def format_media_time(milliseconds: int) -> str:
    total_seconds = max(0, milliseconds) // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def entry_uses_video_output(entry, media_path: Path) -> bool:
    video_path = getattr(entry, "video_path", None)
    return video_path is not None and Path(video_path) == Path(media_path)
