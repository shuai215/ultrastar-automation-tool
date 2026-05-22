"""Application controller that orchestrates the import pipeline.

应用层控制器：按顺序协调搜索、下载、媒体转换和 txt 编辑流程。
"""

from __future__ import annotations

import logging
from pathlib import Path

from ultrastar_clone.core.converter import MediaConverter
from ultrastar_clone.core.downloader import TextDownloader
from ultrastar_clone.core.editor import UltraStarTextEditor
from ultrastar_clone.core.scraper import SongScraper
from ultrastar_clone.models import ImportResult, SongRequest
from ultrastar_clone.services.settings import AppSettings


class ImportController:
    """Coordinate core modules without depending on the GUI.

    协调核心模块，但不依赖任何具体 GUI 实现。
    """
    def __init__(
        self,
        settings: AppSettings,
        scraper: SongScraper,
        downloader: TextDownloader,
        converter: MediaConverter,
        editor: UltraStarTextEditor | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.scraper = scraper
        self.downloader = downloader
        self.converter = converter
        self.editor = editor or UltraStarTextEditor()
        self.logger = logger or logging.getLogger(__name__)

    def import_song(self, request: SongRequest) -> ImportResult:
        """Run the complete import pipeline for one song.

        执行单首歌曲的完整导入流程。
        """
        self.logger.info("Starting import: %s - %s", request.artist, request.title)
        self._progress(5, "Preparing import")

        song_root = request.target_root or self.settings.song_root
        song_folder = Path(song_root) / request.folder_name
        song_folder.mkdir(parents=True, exist_ok=True)

        self._progress(20, "Searching USDB")
        metadata = self.scraper.find(request)
        self.logger.info("Found song metadata: %s", metadata.song_id)

        self._progress(45, "Downloading UltraStar txt")
        txt_path = self.downloader.download_txt(request, metadata, song_folder)
        self.logger.info("Downloaded text file: %s", txt_path)

        self._progress(60, "Downloading media")
        media_path = self.converter.convert(request, metadata, song_folder)
        self.logger.info("Converted media: %s", media_path)

        self._progress(90, "Updating UltraStar tags")
        mp3_path = media_path if media_path and media_path.suffix.lower() == ".mp3" else None
        video_path = media_path if media_path and media_path.suffix.lower() == ".mp4" else None
        self.editor.update_media_tags(txt_path, mp3_path=mp3_path, video_path=video_path)
        self._progress(100, "Import complete")

        return ImportResult(
            request=request,
            song_folder=song_folder,
            txt_path=txt_path,
            media_path=media_path,
        )

    def _progress(self, value: int, message: str) -> None:
        """Forward progress events when the logger supports them.

        如果 logger 支持 progress 方法，就转发进度事件。
        """
        progress = getattr(self.logger, "progress", None)
        if callable(progress):
            progress(value, message)
