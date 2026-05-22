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

    def test_search_request_requires_artist_and_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "artist"):
            SongRequest("", "Yellow")

        with self.assertRaisesRegex(ValueError, "title"):
            SongRequest("Coldplay", "")


if __name__ == "__main__":
    unittest.main()
