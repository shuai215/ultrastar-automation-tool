"""Tests for song library scanning.

曲库扫描测试。
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.services.library import scan_song_library


class LibraryTests(unittest.TestCase):
    def test_scan_song_library_reports_available_formats(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            yellow = root / "Coldplay - Yellow"
            yellow.mkdir()
            (yellow / "Coldplay - Yellow.txt").write_text("txt", encoding="utf-8")
            (yellow / "Coldplay - Yellow.mp4").write_bytes(b"video")
            audio = root / "Artist - Audio"
            audio.mkdir()
            (audio / "Artist - Audio.mp3").write_bytes(b"audio")
            (root / "Empty").mkdir()

            entries = scan_song_library(root)

        self.assertEqual([entry.name for entry in entries], ["Artist - Audio", "Coldplay - Yellow"])
        self.assertEqual(entries[0].formats, "mp3")
        self.assertEqual(entries[1].formats, "txt, mp4")

    def test_scan_missing_song_library_returns_empty_list(self) -> None:
        with TemporaryDirectory() as temp_dir:
            entries = scan_song_library(Path(temp_dir) / "missing")

        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
