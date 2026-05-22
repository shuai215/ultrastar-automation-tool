"""Media download and conversion helpers.

媒体下载与转换工具。

This module wraps ``yt-dlp`` and ``ffmpeg``. During an active download, yt-dlp
creates ``.part`` files as temporary partial downloads. If the command fails,
we remove matching partial files so the user does not mistake them for finished
media files.

本模块封装 ``yt-dlp`` 和 ``ffmpeg``。下载过程中，yt-dlp 会创建 ``.part``
临时文件；如果命令失败，我们会清理对应的残留文件，避免用户误以为它们是
已经完成的视频或音频。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
import re
import shutil
import subprocess
import traceback
from typing import Protocol
from urllib.parse import parse_qs, urlparse

from ultrastar_clone.models import SongMetadata, SongRequest


LOWEST_VIDEO_FORMAT = "worst[ext=mp4][vcodec!=none]/18/worst[vcodec!=none]/worst"
LOWEST_AUDIO_SOURCE_FORMAT = "worst[ext=mp4][vcodec!=none]/18/worstaudio/bestaudio/best"
STABLE_YOUTUBE_FORMAT = "18/worst[ext=mp4][vcodec!=none]/worst[vcodec!=none]/worst"
REMOTE_JS_COMPONENT = "ejs:github"
CHROME_COOKIE_LOCK_HINT = (
    "Hint: Chrome/Edge cookie extraction failed because the browser cookie database is usually locked. "
    "Close all Chrome/Edge windows and background processes, then retry. "
    "If it still fails, try Firefox cookies instead."
)


class MediaConverter(ABC):
    """Common interface for media conversion.

    媒体转换模块的统一接口。
    """

    @abstractmethod
    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path | None:
        """Download and convert media for a song.

        下载并转换某首歌对应的媒体文件。
        """


class NotImplementedConverter(MediaConverter):
    """Placeholder converter used before real media conversion is wired.

    真实媒体转换接入前使用的占位转换器。
    """

    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path | None:
        raise NotImplementedError("YouTube media converter is not implemented yet")


class NoMediaConverter(MediaConverter):
    """Converter that intentionally skips media download.

    明确跳过媒体下载的转换器。
    """

    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path | None:
        return None


class CommandRunner(Protocol):
    """Callable protocol used to make command execution testable.

    可替换的命令执行协议，便于在测试中模拟 yt-dlp。
    """

    def __call__(self, command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        """Run a command and return the completed process.

        运行命令并返回执行结果。
        """


class YtDlpConverter(MediaConverter):
    """Download video or extract audio with yt-dlp.

    使用 yt-dlp 下载视频，或从视频源提取音频。
    """

    def __init__(
        self,
        yt_dlp_path: str | None = None,
        ffmpeg_path: str | None = None,
        runner: CommandRunner | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
        cookies_from_browser: str | None = None,
    ) -> None:
        self.yt_dlp_path = yt_dlp_path or shutil.which("yt-dlp")
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        self.runner = runner
        self.progress_callback = progress_callback
        self.cookies_from_browser = cookies_from_browser

    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path | None:
        if not metadata.youtube_url:
            return None
        self._ensure_tools()

        song_folder.mkdir(parents=True, exist_ok=True)
        output_path = song_folder / f"{request.folder_name}.{request.media_format}"
        youtube_url = normalize_youtube_url(metadata.youtube_url)
        if self.runner is None:
            return self._convert_with_python_api(youtube_url, output_path, request.media_format)

        command = self._build_command(youtube_url, output_path, request.media_format, fallback=False)
        result = self._run(command, song_folder)
        if should_retry_with_stable_youtube_format(result):
            cleanup_partial_files(output_path)
            self._notify_progress(0, "Retrying with stable YouTube format")
            command = self._build_command(youtube_url, output_path, request.media_format, fallback=True)
            result = self._run(command, song_folder)
        if result.returncode != 0:
            cleanup_partial_files(output_path)
            raise RuntimeError(format_command_error(result))
        if not output_path.exists():
            cleanup_partial_files(output_path)
            raise FileNotFoundError(f"yt-dlp did not create expected file: {output_path}")
        return output_path

    def _convert_with_python_api(self, youtube_url: str, output_path: Path, media_format: str) -> Path:
        result = self._run_yt_dlp_api(youtube_url, output_path, media_format, fallback=False)
        if should_retry_with_stable_youtube_format(result):
            cleanup_partial_files(output_path)
            self._notify_progress(0, "Retrying with stable YouTube format")
            result = self._run_yt_dlp_api(youtube_url, output_path, media_format, fallback=True)
        if result.returncode != 0:
            cleanup_partial_files(output_path)
            raise RuntimeError(format_command_error(result))
        if not output_path.exists():
            cleanup_partial_files(output_path)
            raise FileNotFoundError(f"yt-dlp did not create expected file: {output_path}")
        return output_path

    def _run_yt_dlp_api(
        self,
        youtube_url: str,
        output_path: Path,
        media_format: str,
        fallback: bool,
    ) -> subprocess.CompletedProcess[str]:
        try:
            import yt_dlp
        except ImportError as exc:
            return subprocess.CompletedProcess(["yt_dlp", youtube_url], 1, stdout="", stderr=str(exc))

        logger = YtDlpLogCapture()
        options = self._build_ydl_options(output_path, media_format, fallback, logger)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([youtube_url])
        except Exception as exc:
            logger.error(str(exc))
            logger.debug(traceback.format_exc())
            return subprocess.CompletedProcess(
                ["yt_dlp", youtube_url],
                1,
                stdout=logger.stdout,
                stderr=logger.stderr,
            )
        return subprocess.CompletedProcess(["yt_dlp", youtube_url], 0, stdout=logger.stdout, stderr=logger.stderr)

    def _run(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if self.runner is None:
            return run_command(command, cwd=cwd, progress_callback=self.progress_callback)
        return self.runner(command, cwd=cwd)

    def _notify_progress(self, percent: int, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(percent, message)

    def _build_ydl_options(
        self,
        output_path: Path,
        media_format: str,
        fallback: bool,
        logger: object | None = None,
    ) -> dict:
        options = {
            "outtmpl": str(output_path),
            "logger": logger,
            "quiet": True,
            "no_warnings": False,
            "noplaylist": True,
            "ffmpeg_location": str(Path(self.ffmpeg_path).parent) if self.ffmpeg_path else None,
            "progress_hooks": [self._on_ytdlp_progress],
        }
        if fallback:
            options.update(
                {
                    "remote_components": [REMOTE_JS_COMPONENT],
                    "js_runtimes": {"node": {}},
                    "extractor_args": {
                        "youtube": {
                            "player_client": ["default", "mweb", "tv", "-web_safari", "-android_sdkless"],
                        },
                    },
                }
            )
        if self.cookies_from_browser:
            options["cookiesfrombrowser"] = (self.cookies_from_browser, None, None, None)
        if media_format == "mp3":
            options.update(
                {
                    "format": STABLE_YOUTUBE_FORMAT if fallback else LOWEST_AUDIO_SOURCE_FORMAT,
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "0",
                        }
                    ],
                }
            )
            return options
        if media_format == "mp4":
            options.update(
                {
                    "format": STABLE_YOUTUBE_FORMAT if fallback else LOWEST_VIDEO_FORMAT,
                    "merge_output_format": "mp4",
                }
            )
            return options
        raise ValueError("media_format must be 'mp3' or 'mp4'")

    def _on_ytdlp_progress(self, status: dict) -> None:
        if self.progress_callback is None or status.get("status") != "downloading":
            return
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        downloaded = status.get("downloaded_bytes")
        if not total or downloaded is None:
            return
        percent = max(0, min(100, int(downloaded * 100 / total)))
        self.progress_callback(percent, status.get("_percent_str", f"{percent}%").strip())

    def _build_command(
        self,
        youtube_url: str,
        output_path: Path,
        media_format: str,
        fallback: bool,
    ) -> list[str]:
        # The output path is explicit so Editor can later reference the exact file.
        # 显式指定输出路径，方便后续 Editor 精确写入 #MP3/#VIDEO 标签。
        base = [
            self.yt_dlp_path or "yt-dlp",
            "--no-playlist",
            "--no-update",
            "--ffmpeg-location",
            str(Path(self.ffmpeg_path).parent) if self.ffmpeg_path else "",
            "-o",
            str(output_path),
        ]
        if fallback:
            # Avoid clients/formats that often require YouTube PO tokens or SABR-only streams.
            # 避开经常需要 YouTube PO Token 或只提供 SABR 流的客户端/格式。
            base.extend(
                [
                    "--remote-components",
                    REMOTE_JS_COMPONENT,
                    "--no-js-runtimes",
                    "--js-runtimes",
                    "node",
                    "--extractor-args",
                    "youtube:player_client=default,mweb,tv,-web_safari,-android_sdkless",
                ]
            )
        if self.cookies_from_browser:
            # Reuse the user's browser session when YouTube rejects anonymous downloads.
            # 当 YouTube 拒绝匿名下载时，复用用户浏览器会话。
            base.extend(["--cookies-from-browser", self.cookies_from_browser])

        if media_format == "mp3":
            return [
                *base,
                "-f",
                STABLE_YOUTUBE_FORMAT if fallback else LOWEST_AUDIO_SOURCE_FORMAT,
                "-x",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "0",
                youtube_url,
            ]
        if media_format == "mp4":
            return [
                *base,
                "-f",
                STABLE_YOUTUBE_FORMAT if fallback else LOWEST_VIDEO_FORMAT,
                "--merge-output-format",
                "mp4",
                youtube_url,
            ]
        raise ValueError("media_format must be 'mp3' or 'mp4'")

    def _ensure_tools(self) -> None:
        if self.runner is not None and not self.yt_dlp_path:
            raise FileNotFoundError("yt-dlp executable was not found on PATH")
        if not self.ffmpeg_path:
            raise FileNotFoundError("ffmpeg executable was not found on PATH")


class YtDlpLogCapture:
    """Small logger adapter that captures yt-dlp Python API output.

    捕获 yt-dlp Python API 日志的小型 logger 适配器。
    """

    def __init__(self) -> None:
        self._stdout: list[str] = []
        self._stderr: list[str] = []

    @property
    def stdout(self) -> str:
        return "\n".join(self._stdout)

    @property
    def stderr(self) -> str:
        return "\n".join(self._stderr)

    def debug(self, message: str) -> None:
        self._stdout.append(str(message))

    def info(self, message: str) -> None:
        self._stdout.append(str(message))

    def warning(self, message: str) -> None:
        self._stderr.append(f"WARNING: {message}")

    def error(self, message: str) -> None:
        self._stderr.append(f"ERROR: {message}")


def run_command(
    command: list[str],
    cwd: Path | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and optionally stream yt-dlp progress.

    运行子进程，并在需要时实时解析 yt-dlp 下载进度。
    """

    if progress_callback is None:
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )

    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert process.stdout is not None
    output_parts: list[str] = []
    chunk = ""
    while True:
        char = process.stdout.read(1)
        if char == "" and process.poll() is not None:
            break
        if not char:
            continue
        output_parts.append(char)
        if char in {"\n", "\r"}:
            _emit_ytdlp_progress(chunk, progress_callback)
            chunk = ""
        else:
            chunk += char
    if chunk:
        _emit_ytdlp_progress(chunk, progress_callback)
    return subprocess.CompletedProcess(command, process.wait(), stdout="".join(output_parts), stderr="")


def format_command_error(result: subprocess.CompletedProcess[str]) -> str:
    """Build a readable error from a failed command.

    从失败的命令结果中生成便于阅读的错误信息。
    """

    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    details = stderr or stdout or "no output"
    if is_chrome_cookie_database_error(details):
        details = f"{details}\n{CHROME_COOKIE_LOCK_HINT}"
    return f"yt-dlp failed with exit code {result.returncode}: {details}"


def is_chrome_cookie_database_error(output: str) -> bool:
    """Detect yt-dlp failures caused by locked Chrome-family cookie databases.

    识别 Chrome/Edge 等浏览器 cookie 数据库被锁导致的 yt-dlp 失败。
    """

    lowered = output.lower()
    return "could not copy chrome cookie database" in lowered


def parse_ytdlp_percent(line: str) -> int | None:
    """Parse yt-dlp download percentage from one output line.

    从一行 yt-dlp 输出中解析下载百分比。
    """

    match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
    if not match:
        return None
    return max(0, min(100, int(float(match.group(1)))))


def _emit_ytdlp_progress(line: str, progress_callback: Callable[[int, str], None]) -> None:
    percent = parse_ytdlp_percent(line)
    if percent is not None:
        progress_callback(percent, line.strip())


def cleanup_partial_files(output_path: Path) -> None:
    """Remove yt-dlp partial files that match the expected output.

    清理与目标文件对应的 yt-dlp 临时 ``.part`` 文件。
    """

    patterns = [
        f"{output_path.name}.part",
        f"{output_path.stem}*.part",
        f"{output_path.name}.*.part",
    ]
    for pattern in patterns:
        for partial in output_path.parent.glob(pattern):
            if partial.is_file():
                partial.unlink(missing_ok=True)


def should_retry_with_stable_youtube_format(result: subprocess.CompletedProcess[str]) -> bool:
    """Return True when yt-dlp failed with a YouTube 403/SABR style error.

    判断 yt-dlp 是否因为 YouTube 403/SABR 类错误而值得降级重试。
    """

    output = f"{result.stdout or ''}\n{result.stderr or ''}".lower()
    return result.returncode != 0 and (
        "http error 403" in output
        or "sabr" in output
        or "po token" in output
        or "signature extraction failed" in output
        or "requested format is not available" in output
        or "only images are available" in output
    )


def normalize_youtube_url(url: str) -> str:
    """Convert YouTube embed URLs to normal watch URLs for yt-dlp.

    将 YouTube embed 链接转换成普通 watch 链接，减少解析差异。
    """

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
