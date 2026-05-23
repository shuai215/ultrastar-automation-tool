"""Tests for safe GUI module import.

GUI 模块安全导入测试。
"""

import unittest


class GuiImportTests(unittest.TestCase):
    def test_gui_module_imports(self) -> None:
        from ultrastar_clone.gui.app import GuiDependencyError, main

        self.assertTrue(callable(main))
        self.assertTrue(GuiDependencyError)

    def test_format_media_time(self) -> None:
        from ultrastar_clone.gui.app import format_media_time

        self.assertEqual(format_media_time(0), "00:00")
        self.assertEqual(format_media_time(65000), "01:05")
        self.assertEqual(format_media_time(3665000), "61:05")

    def test_describe_lyric_sync_status_requires_timed_lyrics_for_ready(self) -> None:
        from ultrastar_clone.core.song_parser import LyricsLine, Note, Song
        from ultrastar_clone.gui.app import describe_lyric_sync_status

        note = Note(0, 2, 1, "Hi")
        lyric = LyricsLine((note,), "Hi", 0, 2)

        self.assertEqual(
            describe_lyric_sync_status(Song(bpm=None, lyrics=(lyric,)), ()),
            ("Lyrics cannot sync because BPM is missing or invalid", "No synchronized lyrics"),
        )
        self.assertEqual(
            describe_lyric_sync_status(Song(bpm=150.0, lyrics=()), ()),
            ("No synchronized lyrics found in TXT", "No synchronized lyrics"),
        )
        self.assertEqual(
            describe_lyric_sync_status(Song(bpm=150.0, lyrics=(lyric,)), (object(),)),
            ("Ready", ""),
        )


if __name__ == "__main__":
    unittest.main()

