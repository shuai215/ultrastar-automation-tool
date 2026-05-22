"""Shared data models used across the import pipeline.

导入流程中各模块共享的数据模型。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SongRequest:
    """User request for importing one song.

    用户发起的一首歌导入请求。
    """
    artist: str
    title: str
    media_format: str = "mp3"
    target_root: Path | None = None

    def __post_init__(self) -> None:
        artist = self.artist.strip()
        title = self.title.strip()
        media_format = self.media_format.lower().strip()

        if not artist:
            raise ValueError("artist is required")
        if not title:
            raise ValueError("title is required")
        if media_format not in {"mp3", "mp4"}:
            raise ValueError("media_format must be 'mp3' or 'mp4'")

        object.__setattr__(self, "artist", artist)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "media_format", media_format)

    @property
    def folder_name(self) -> str:
        return safe_filename(f"{self.artist} - {self.title}")


@dataclass(frozen=True)
class SongMetadata:
    """Metadata discovered from USDB before downloading files.

    从 USDB 搜索阶段获得的歌曲元数据。
    """
    song_id: str
    youtube_url: str | None = None


@dataclass(frozen=True)
class ImportResult:
    """Paths produced by one completed import.

    一次导入完成后生成的文件路径结果。
    """
    request: SongRequest
    song_folder: Path
    txt_path: Path
    media_path: Path | None


def safe_filename(value: str) -> str:
    """Return a Windows-safe filename for song folders and files.

    生成适合 Windows 文件系统使用的安全文件名。
    """
    forbidden = '<>:"/\\|?*'
    cleaned = "".join("_" if char in forbidden else char for char in value)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip(" .") or "untitled"
