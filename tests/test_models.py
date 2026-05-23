"""Tests for shared data models.

共享数据模型测试。
"""

from __future__ import annotations

import unittest

from ultrastar_clone.models import SongRequest


class ModelTests(unittest.TestCase):
    def test_direct_url_request_uses_video_id_folder_name(self) -> None:
        request = SongRequest(
            input_mode="url",
            youtube_url="https://www.youtube.com/watch?v=abc123",
            download_lyrics=False,
            download_audio=True,
            download_video=False,
        )

        self.assertEqual(request.folder_name, "YouTube - abc123")

    def test_search_request_allows_artist_or_title_only(self) -> None:
        artist_only = SongRequest("Coldplay", "")
        title_only = SongRequest("", "Yellow")

        self.assertEqual(artist_only.folder_name, "Coldplay")
        self.assertEqual(title_only.folder_name, "Yellow")

    def test_search_request_requires_artist_or_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "artist or title"):
            SongRequest("", "")


if __name__ == "__main__":
    unittest.main()
