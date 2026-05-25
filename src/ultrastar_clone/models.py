"""Shared data models used across the import pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class SongRequest:
    """User request for importing one song."""
    artist: str = ""
    title: str = ""
    media_format: str = "mp3"
    target_root: Path | None = None
    input_mode: str = "search"
    youtube_url: str | None = None
    download_lyrics: bool = True
    download_audio: bool | None = None
    download_video: bool | None = None
    selected_song_id: str | None = None

    def __post_init__(self) -> None:
        artist = self.artist.strip()
        title = self.title.strip()
        media_format = self.media_format.lower().strip()
        input_mode = self.input_mode.lower().strip()
        youtube_url = self.youtube_url.strip() if self.youtube_url else None
        selected_song_id = self.selected_song_id.strip() if self.selected_song_id else None
        download_audio = self.download_audio
        download_video = self.download_video

        if download_audio is None:
            download_audio = media_format == "mp3"
        if download_video is None:
            download_video = media_format == "mp4"

        if input_mode not in {"search", "url"}:
            raise ValueError("input_mode must be 'search' or 'url'")
        if input_mode == "search" and not (artist or title):
            raise ValueError("artist or title is required")
        if input_mode == "url" and not youtube_url:
            raise ValueError("youtube_url is required for direct URL imports")
        if media_format not in {"mp3", "mp4"}:
            raise ValueError("media_format must be 'mp3' or 'mp4'")

        object.__setattr__(self, "artist", artist)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "media_format", media_format)
        object.__setattr__(self, "input_mode", input_mode)
        object.__setattr__(self, "youtube_url", youtube_url)
        object.__setattr__(self, "selected_song_id", selected_song_id)
        object.__setattr__(self, "download_audio", bool(download_audio))
        object.__setattr__(self, "download_video", bool(download_video))

    @property
    def folder_name(self) -> str:
        if self.input_mode == "url" and not (self.artist and self.title):
            return safe_filename(f"YouTube - {youtube_id_from_url(self.youtube_url or '')}")
        if not self.artist:
            return safe_filename(self.title)
        if not self.title:
            return safe_filename(self.artist)
        return safe_filename(f"{self.artist} - {self.title}")


@dataclass(frozen=True)
class SongMetadata:
    """Metadata discovered from USDB before downloading files."""
    song_id: str
    youtube_url: str | None = None


@dataclass(frozen=True)
class ImportResult:
    """Paths produced by one completed import."""
    request: SongRequest
    song_folder: Path
    txt_path: Path | None
    media_path: Path | None
    media_paths: tuple[Path, ...] = ()


def safe_filename(value: str) -> str:
    """Return a Windows-safe filename for song folders and files."""
    forbidden = '<>:"/\\|?*'
    cleaned = "".join("_" if char in forbidden else char for char in value)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip(" .") or "untitled"


def youtube_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    if "youtu.be" in parsed.netloc:
        return parsed.path.strip("/") or "direct-url"
    if "youtube.com" in parsed.netloc and parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        return video_id or "direct-url"
    if "youtube.com" in parsed.netloc and parsed.path.startswith("/embed/"):
        return parsed.path.removeprefix("/embed/").split("/", 1)[0] or "direct-url"
    return "direct-url"
