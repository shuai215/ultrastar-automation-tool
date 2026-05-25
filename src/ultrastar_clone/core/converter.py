"""Media download and conversion helpers.

媒体下载与转换工具。

Uses ``yt-dlp`` Python API (not subprocess) so the frozen EXE works
without a standalone yt-dlp binary on PATH.  ffmpeg is still required
and is bundled inside the PyInstaller distribution.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
import re
import shutil
from urllib.parse import parse_qs, urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from ultrastar_clone.models import SongMetadata, SongRequest


VIDEO_FORMAT = (
    "bestvideo[height<=1080][ext=mp4][vcodec!=none]+bestaudio[ext=m4a]/"
    "best[height<=1080][ext=mp4]/"
    "bestvideo[height<=720][vcodec!=none]+bestaudio/"
    "best[height<=720]/18"
)
LOWEST_AUDIO_SOURCE_FORMAT = "worst[ext=mp4][vcodec!=none]/18/worstaudio/bestaudio/best"
STABLE_YOUTUBE_FORMAT = "18/worst[ext=mp4][vcodec!=none]/worst[vcodec!=none]/worst"
REMOTE_JS_COMPONENT = "ejs:github"


def _find_ffmpeg() -> str | None:
    """Locate ffmpeg — checks the frozen bundle first, then PATH."""
    if getattr(sys, "frozen", False):
        bundled = Path(sys._MEIPASS) / "ffmpeg.exe"
        if bundled.is_file():
            return str(bundled)
    return shutil.which("ffmpeg")


class MediaConverter(ABC):
    """Common interface for media conversion."""

    @abstractmethod
    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path | None:
        """Download and convert media for a song."""


class NotImplementedConverter(MediaConverter):
    """Placeholder converter used before real media conversion is wired."""

    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path | None:
        raise NotImplementedError("YouTube media converter is not implemented yet")


class NoMediaConverter(MediaConverter):
    """Converter that intentionally skips media download."""

    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path | None:
        return None


class YtDlpConverter(MediaConverter):
    """Download video or extract audio with yt-dlp Python API."""

    def __init__(
        self,
        yt_dlp_path: str | None = None,
        ffmpeg_path: str | None = None,
        runner=None,
        progress_callback: Callable[[int, str], None] | None = None,
        cookies_from_browser: str | None = None,
    ) -> None:
        self.ffmpeg_path = ffmpeg_path or _find_ffmpeg()
        self.progress_callback = progress_callback
        self.cookies_from_browser = cookies_from_browser
        # yt_dlp_path and runner are kept for backward-compat but unused with Python API.

    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path | None:
        if not metadata.youtube_url:
            return None
        self._ensure_tools()

        song_folder.mkdir(parents=True, exist_ok=True)
        output_path = song_folder / f"{request.folder_name}.{request.media_format}"
        youtube_url = normalize_youtube_url(metadata.youtube_url)

        try:
            self._run_download(youtube_url, output_path, request.media_format, fallback=False)
        except DownloadError as exc:
            if _is_retryable_youtube_error(exc):
                cleanup_partial_files(output_path)
                self._notify_progress(0, "Retrying with stable YouTube format")
                try:
                    self._run_download(youtube_url, output_path, request.media_format, fallback=True)
                except DownloadError as exc2:
                    cleanup_partial_files(output_path)
                    raise RuntimeError(f"yt-dlp failed: {exc2}") from exc2
            else:
                cleanup_partial_files(output_path)
                raise RuntimeError(f"yt-dlp failed: {exc}") from exc

        if not output_path.exists():
            cleanup_partial_files(output_path)
            raise FileNotFoundError(f"yt-dlp did not create expected file: {output_path}")
        return output_path

    def _run_download(self, youtube_url: str, output_path: Path, media_format: str, fallback: bool) -> None:
        opts = self._build_opts(output_path, media_format, fallback)
        with YoutubeDL(opts) as ydl:
            ydl.download([youtube_url])

    def _build_opts(self, output_path: Path, media_format: str, fallback: bool) -> dict:
        opts: dict = {
            "noplaylist": True,
            "outtmpl": str(output_path),
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
        }
        if self.ffmpeg_path:
            opts["ffmpeg_location"] = str(Path(self.ffmpeg_path).parent)
        if self.cookies_from_browser:
            opts["cookiesfrombrowser"] = (self.cookies_from_browser,)
        if fallback:
            opts.update(
                {
                    "remote_components": REMOTE_JS_COMPONENT,
                    "no_js_runtimes": True,
                    "js_runtimes": "node",
                    "extractor_args": {
                        "youtube": {
                            "player_client": ["default", "mweb", "tv"],
                        }
                    },
                }
            )
            opts["format"] = STABLE_YOUTUBE_FORMAT
        elif media_format == "mp3":
            opts["format"] = LOWEST_AUDIO_SOURCE_FORMAT
        elif media_format == "mp4":
            opts["format"] = VIDEO_FORMAT
        else:
            raise ValueError("media_format must be 'mp3' or 'mp4'")

        if media_format == "mp3":
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                }
            ]
        elif media_format == "mp4":
            opts["merge_output_format"] = "mp4"

        return opts

    def _progress_hook(self, d: dict) -> None:
        if d.get("status") == "downloading" and self.progress_callback:
            percent_str = d.get("_percent_str", "0%").strip().replace("%", "")
            try:
                percent = int(float(percent_str))
                self.progress_callback(percent, f"Downloading {percent}%")
            except (ValueError, TypeError):
                pass

    def _notify_progress(self, percent: int, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(percent, message)

    def _ensure_tools(self) -> None:
        if not self.ffmpeg_path:
            raise FileNotFoundError("ffmpeg was not found — ensure ffmpeg is on PATH or bundled")


def _is_retryable_youtube_error(error: DownloadError) -> bool:
    message = str(error).lower()
    return any(
        kw in message
        for kw in (
            "http error 403",
            "sabr",
            "po token",
            "signature extraction failed",
            "requested format is not available",
            "only images are available",
        )
    )


def cleanup_partial_files(output_path: Path) -> None:
    """Remove yt-dlp partial files that match the expected output."""
    patterns = [
        f"{output_path.name}.part",
        f"{output_path.stem}*.part",
        f"{output_path.name}.*.part",
    ]
    for pattern in patterns:
        for partial in output_path.parent.glob(pattern):
            if partial.is_file():
                partial.unlink(missing_ok=True)


def normalize_youtube_url(url: str) -> str:
    """Convert YouTube embed URLs to normal watch URLs for yt-dlp."""
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc and parsed.path.startswith("/embed/"):
        video_id = parsed.path.removeprefix("/embed/").split("/", 1)[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    if "youtube.com" in parsed.netloc and parsed.path == "/watch":
        query = parse_qs(parsed.query)
        video_id = query.get("v", [""])[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    return url
