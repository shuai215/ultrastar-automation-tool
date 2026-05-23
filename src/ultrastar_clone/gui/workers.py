"""Background workers for search and import operations.

搜索和导入的后台工作线程。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ultrastar_clone.core.converter import NoMediaConverter, YtDlpConverter
from ultrastar_clone.core.downloader import USDBTextDownloader
from ultrastar_clone.core.scraper import USDBScraper
from ultrastar_clone.models import SongRequest
from ultrastar_clone.services.controller import ImportController
from ultrastar_clone.services.logger import build_logger
from ultrastar_clone.services.settings import AppSettings, default_log_dir


class SignalLogger:
    def __init__(self, signal) -> None:
        self.signal = signal

    def info(self, message: str, *args) -> None:
        self._emit("INFO", message, *args)

    def warning(self, message: str, *args) -> None:
        self._emit("WARN", message, *args)

    def error(self, message: str, *args) -> None:
        self._emit("ERROR", message, *args)

    def _emit(self, level: str, message: str, *args) -> None:
        if args:
            message = message % args
        self.signal.emit(f"[{level}] {message}")


class ImportWorker(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    done = pyqtSignal(str, str, str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        username: str | None,
        password: str | None,
        request: SongRequest,
        respect_wait: bool,
    ) -> None:
        super().__init__()
        self.username = username
        self.password = password
        self.request = request
        self.respect_wait = respect_wait

    def run(self) -> None:
        try:
            output = self.request.target_root or Path.cwd() / "demo_output"
            settings = AppSettings(song_root=output, log_dir=default_log_dir())
            file_logger = build_logger(settings.log_dir)
            gui_logger = SignalLogger(self.log)

            class CombinedLogger:
                def info(_, message: str, *args) -> None:
                    file_logger.info(message, *args)
                    gui_logger.info(message, *args)

                def warning(_, message: str, *args) -> None:
                    file_logger.warning(message, *args)
                    gui_logger.warning(message, *args)

                def error(_, message: str, *args) -> None:
                    file_logger.error(message, *args)
                    gui_logger.error(message, *args)

                def progress(_, value: int, message: str) -> None:
                    self.progress.emit(value, message)

            scraper = USDBScraper(self.username, self.password) if self.username and self.password else None
            opener = scraper.opener if scraper is not None else None
            downloader = USDBTextDownloader(opener=opener, respect_wait=self.respect_wait)
            converter = (
                NoMediaConverter()
                if not self.request.download_audio and not self.request.download_video
                else YtDlpConverter(
                    progress_callback=self._media_progress,
                )
            )
            controller = ImportController(settings, scraper, downloader, converter, logger=CombinedLogger())
            result = controller.import_song(self.request)
            txt_path = str(result.txt_path) if result.txt_path else ""
            media_paths = "; ".join(str(path) for path in result.media_paths)
            self.done.emit(str(result.song_folder), txt_path, media_paths)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _media_progress(self, percent: int, message: str) -> None:
        scaled = 60 + int(percent * 0.25)
        self.progress.emit(min(scaled, 85), f"Downloading media {percent}%")


class SearchWorker(QObject):
    candidates = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, username: str, password: str, artist: str, title: str) -> None:
        super().__init__()
        self.username = username
        self.password = password
        self.artist = artist
        self.title = title

    def run(self) -> None:
        try:
            scraper = USDBScraper(self.username, self.password)
            request = SongRequest(self.artist, self.title, download_lyrics=True, download_audio=False, download_video=False)
            results = [
                {
                    "song_id": candidate.song_id,
                    "artist": candidate.artist,
                    "title": candidate.title,
                }
                for candidate in scraper.search(request)
            ]
            self.candidates.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))
