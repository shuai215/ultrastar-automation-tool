"""Application controller that orchestrates the import pipeline.

应用层控制器：按顺序协调搜索、下载、媒体转换和 txt 编辑流程。
"""

from __future__ import annotations

from dataclasses import replace
import logging
from pathlib import Path

from ultrastar_clone.core.converter import MediaConverter
from ultrastar_clone.core.downloader import TextDownloader
from ultrastar_clone.core.editor import UltraStarTextEditor
from ultrastar_clone.core.scraper import SongScraper
from ultrastar_clone.models import ImportResult, SongMetadata, SongRequest
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
        self._validate_request(request)
        self._progress(5, "Preparing import")

        song_root = request.target_root or self.settings.song_root
        song_folder = Path(song_root) / request.folder_name
        song_folder.mkdir(parents=True, exist_ok=True)

        txt_path = None
        media_paths: list[Path] = []

        if request.input_mode == "search":
            self._progress(20, "Searching USDB")
            if request.selected_song_id:
                metadata_loader = getattr(self.scraper, "metadata_for_song_id", None)
                if not callable(metadata_loader):
                    raise ValueError("Selected USDB results require song-id metadata lookup")
                metadata = metadata_loader(request.selected_song_id)
            else:
                metadata = self.scraper.find(request)
            self.logger.info("Found song metadata: %s", metadata.song_id)
        else:
            metadata = SongMetadata(song_id="direct-url", youtube_url=request.youtube_url)
            self.logger.info("Using direct YouTube URL")

        if request.download_lyrics:
            self._progress(45, "Downloading UltraStar txt")
            txt_path = self.downloader.download_txt(request, metadata, song_folder)
            self.logger.info("Downloaded text file: %s", txt_path)

        self._progress(60, "Downloading media")
        if request.download_audio:
            media_path = self.converter.convert(replace(request, media_format="mp3"), metadata, song_folder)
            if media_path:
                media_paths.append(media_path)
                self.logger.info("Converted audio: %s", media_path)
        if request.download_video:
            media_path = self.converter.convert(replace(request, media_format="mp4"), metadata, song_folder)
            if media_path:
                media_paths.append(media_path)
                self.logger.info("Converted video: %s", media_path)

        if txt_path is not None:
            self._progress(90, "Updating UltraStar tags")
            mp3_path = next((path for path in media_paths if path.suffix.lower() == ".mp3"), None)
            video_path = next((path for path in media_paths if path.suffix.lower() == ".mp4"), None)
            self.editor.update_media_tags(txt_path, mp3_path=mp3_path, video_path=video_path)
        self._progress(100, "Import complete")

        return ImportResult(
            request=request,
            song_folder=song_folder,
            txt_path=txt_path,
            media_path=media_paths[0] if media_paths else None,
            media_paths=tuple(media_paths),
        )

    def _validate_request(self, request: SongRequest) -> None:
        """Validate input mode and selected download tasks.

        校验输入模式和用户选择的下载任务。
        """

        if not request.download_lyrics and not request.download_audio and not request.download_video:
            raise ValueError("Select lyrics, MP3 audio, video, or a combination before importing")
        if request.input_mode == "url" and request.download_lyrics:
            raise ValueError("Direct URL imports cannot download USDB lyrics; use search mode for lyrics")
        if request.input_mode == "search" and self.scraper is None:
            raise ValueError("Search imports require a USDB scraper")

    def _progress(self, value: int, message: str) -> None:
        """Forward progress events when the logger supports them.

        如果 logger 支持 progress 方法，就转发进度事件。
        """
        progress = getattr(self.logger, "progress", None)
        if callable(progress):
            progress(value, message)
