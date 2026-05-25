"""Tests for media conversion helpers."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from yt_dlp.utils import DownloadError

from ultrastar_clone.core.converter import (
    YtDlpConverter,
    _is_retryable_youtube_error,
    cleanup_partial_files,
    normalize_youtube_url,
)
from ultrastar_clone.models import SongMetadata, SongRequest


def _make_dl_mock(should_fail: bool = False) -> MagicMock:
    """Build a YoutubeDL mock that writes the output file on close."""

    def _side_effect(opts):
        output = Path(opts["outtmpl"])
        output.write_bytes(b"media")
        return None

    mock = MagicMock()
    if should_fail:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=None)
        mock_instance.download = MagicMock(side_effect=DownloadError("HTTP Error 403: Forbidden"))
        mock.return_value = mock_instance
    else:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=None)
        mock_instance.download = MagicMock(side_effect=lambda url: _side_effect(mock.call_args[0][0]))
        mock.return_value = mock_instance
    return mock


class ConverterTests(unittest.TestCase):
    def test_convert_mp3_builds_expected_opts(self) -> None:
        with patch("ultrastar_clone.core.converter.YoutubeDL") as mock_ydl:
            mock = _make_dl_mock()
            mock_ydl.side_effect = mock

            converter = YtDlpConverter(ffmpeg_path="C:/ffmpeg/bin/ffmpeg.exe")

            with TemporaryDirectory() as temp_dir:
                path = converter.convert(
                    SongRequest("Usher", "U Remind Me", "mp3"),
                    SongMetadata("6131", "https://youtube.test/watch?v=abc"),
                    Path(temp_dir),
                )

            opts = mock_ydl.call_args[0][0]
            self.assertIn("postprocessors", opts)
            self.assertEqual(opts["postprocessors"][0]["preferredcodec"], "mp3")
            self.assertEqual(opts["noplaylist"], True)
            self.assertEqual(path.name, "Usher - U Remind Me.mp3")

    def test_convert_mp4_builds_expected_opts(self) -> None:
        with patch("ultrastar_clone.core.converter.YoutubeDL") as mock_ydl:
            mock = _make_dl_mock()
            mock_ydl.side_effect = mock

            converter = YtDlpConverter(ffmpeg_path="C:/ffmpeg/bin/ffmpeg.exe")

            with TemporaryDirectory() as temp_dir:
                path = converter.convert(
                    SongRequest("Artist", "Video Song", "mp4"),
                    SongMetadata("1", "https://youtube.test/watch?v=abc"),
                    Path(temp_dir),
                )

            opts = mock_ydl.call_args[0][0]
            self.assertEqual(opts["merge_output_format"], "mp4")
            self.assertIn("bestvideo", opts["format"])
            self.assertEqual(path.name, "Artist - Video Song.mp4")

    def test_convert_can_use_browser_cookies(self) -> None:
        with patch("ultrastar_clone.core.converter.YoutubeDL") as mock_ydl:
            mock = _make_dl_mock()
            mock_ydl.side_effect = mock

            converter = YtDlpConverter(
                ffmpeg_path="C:/ffmpeg/bin/ffmpeg.exe",
                cookies_from_browser="chrome",
            )

            with TemporaryDirectory() as temp_dir:
                converter.convert(
                    SongRequest("Artist", "Video Song", "mp4"),
                    SongMetadata("1", "https://youtube.test/watch?v=abc"),
                    Path(temp_dir),
                )

            opts = mock_ydl.call_args[0][0]
            self.assertEqual(opts["cookiesfrombrowser"], ("chrome",))

    def test_convert_returns_none_without_youtube_url(self) -> None:
        converter = YtDlpConverter(ffmpeg_path="C:/ffmpeg/bin/ffmpeg.exe")

        with TemporaryDirectory() as temp_dir:
            result = converter.convert(
                SongRequest("A", "B"),
                SongMetadata("1", None),
                Path(temp_dir),
            )

        self.assertIsNone(result)

    def test_convert_raises_when_download_fails(self) -> None:
        with patch("ultrastar_clone.core.converter.YoutubeDL") as mock_ydl:
            mock = _make_dl_mock(should_fail=True)
            mock_ydl.side_effect = mock

            converter = YtDlpConverter(ffmpeg_path="C:/ffmpeg/bin/ffmpeg.exe")

            with TemporaryDirectory() as temp_dir:
                with self.assertRaisesRegex(RuntimeError, "yt-dlp failed"):
                    converter.convert(
                        SongRequest("A", "B"),
                        SongMetadata("1", "https://youtube.test/watch?v=abc"),
                        Path(temp_dir),
                    )

    def test_retry_with_stable_format_after_403(self) -> None:
        fail_instance = MagicMock()
        fail_instance.download = MagicMock(side_effect=DownloadError("HTTP Error 403: Forbidden"))
        fail_dl = MagicMock()
        fail_dl.__enter__ = MagicMock(return_value=fail_instance)
        fail_dl.__exit__ = MagicMock(return_value=None)

        success_instance = MagicMock()
        success_instance.download = MagicMock()
        success_dl = MagicMock()
        success_dl.__enter__ = MagicMock(return_value=success_instance)
        success_dl.__exit__ = MagicMock(return_value=None)

        dl_calls = [fail_dl, success_dl]

        with patch("ultrastar_clone.core.converter.YoutubeDL") as mock_ydl:
            mock_ydl.side_effect = dl_calls

            converter = YtDlpConverter(ffmpeg_path="C:/ffmpeg/bin/ffmpeg.exe")

            with TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                output = temp_dir_path / "Coldplay - Yellow.mp4"
                output.write_bytes(b"media")

                path = converter.convert(
                    SongRequest("Coldplay", "Yellow", "mp4"),
                    SongMetadata("4698", "https://www.youtube.com/embed/yKNxeF4KMsY"),
                    temp_dir_path,
                )

            self.assertEqual(path.name, "Coldplay - Yellow.mp4")
            self.assertEqual(mock_ydl.call_count, 2)
            opts2 = mock_ydl.call_args_list[1][0][0]
            self.assertIn("remote_components", opts2)
            self.assertEqual(opts2["remote_components"], "ejs:github")
            self.assertEqual(opts2["format"], "18/worst[ext=mp4][vcodec!=none]/worst[vcodec!=none]/worst")

    def test_is_retryable_youtube_error(self) -> None:
        self.assertTrue(_is_retryable_youtube_error(DownloadError("HTTP Error 403: Forbidden")))
        self.assertTrue(_is_retryable_youtube_error(
            DownloadError("Only images are available. Requested format is not available")
        ))
        self.assertFalse(_is_retryable_youtube_error(DownloadError("Connection refused")))

    def test_normalize_youtube_embed_url(self) -> None:
        self.assertEqual(
            normalize_youtube_url("https://www.youtube.com/embed/yKNxeF4KMsY"),
            "https://www.youtube.com/watch?v=yKNxeF4KMsY",
        )

    def test_cleanup_partial_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "Artist - Title.mp4"
            partial = Path(temp_dir) / "Artist - Title.mp4.part"
            partial.write_text("partial", encoding="utf-8")

            cleanup_partial_files(output)

            self.assertFalse(partial.exists())

    def test_ffmpeg_location_in_opts(self) -> None:
        with patch("ultrastar_clone.core.converter.YoutubeDL") as mock_ydl:
            mock = _make_dl_mock()
            mock_ydl.side_effect = mock

            converter = YtDlpConverter(ffmpeg_path="C:/ffmpeg/bin/ffmpeg.exe")

            with TemporaryDirectory() as temp_dir:
                converter.convert(
                    SongRequest("A", "B", "mp4"),
                    SongMetadata("1", "https://youtube.test/watch?v=abc"),
                    Path(temp_dir),
                )

            opts = mock_ydl.call_args[0][0]
            ffmpeg_dir = Path(opts["ffmpeg_location"])
            self.assertEqual(ffmpeg_dir, Path("C:/ffmpeg/bin"))


if __name__ == "__main__":
    unittest.main()
