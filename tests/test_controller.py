"""Tests for pipeline orchestration.

导入流程编排测试。
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.core.converter import MediaConverter
from ultrastar_clone.core.downloader import TextDownloader
from ultrastar_clone.core.scraper import SongScraper
from ultrastar_clone.models import SongMetadata, SongRequest
from ultrastar_clone.services.controller import ImportController
from ultrastar_clone.services.settings import AppSettings


class FakeScraper(SongScraper):
    def find(self, request: SongRequest) -> SongMetadata:
        return SongMetadata(song_id="123", youtube_url="https://example.test/video")


class FakeDownloader(TextDownloader):
    def download_txt(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path:
        txt_path = song_folder / f"{request.folder_name}.txt"
        txt_path.write_text(
            f"#TITLE:{request.title}\n#ARTIST:{request.artist}\n#GAP:1000\n",
            encoding="utf-8",
        )
        return txt_path


class FakeConverter(MediaConverter):
    def convert(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path:
        media_path = song_folder / f"{request.folder_name}.{request.media_format}"
        media_path.write_bytes(b"media")
        return media_path


class ControllerTests(unittest.TestCase):
    def test_controller_imports_song_with_mp3_tag(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            settings = AppSettings(song_root=tmp_path, log_dir=tmp_path / "logs")
            controller = ImportController(settings, FakeScraper(), FakeDownloader(), FakeConverter())

            result = controller.import_song(SongRequest("Test Artist", "Test Song", "mp3"))

            self.assertEqual(result.song_folder, tmp_path / "Test Artist - Test Song")
            self.assertTrue(result.txt_path.exists())
            self.assertIsNotNone(result.media_path)
            self.assertTrue(result.media_path.exists())
            content = result.txt_path.read_text(encoding="utf-8")
            self.assertIn("#MP3:Test Artist - Test Song.mp3", content)

    def test_controller_imports_song_with_video_tag(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            settings = AppSettings(song_root=tmp_path, log_dir=tmp_path / "logs")
            controller = ImportController(settings, FakeScraper(), FakeDownloader(), FakeConverter())

            result = controller.import_song(SongRequest("A/B", "C:D", "mp4"))

            self.assertEqual(result.song_folder.name, "A_B - C_D")
            content = result.txt_path.read_text(encoding="utf-8")
            self.assertIn("#VIDEO:A_B - C_D.mp4", content)


if __name__ == "__main__":
    unittest.main()

