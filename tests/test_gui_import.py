"""Tests for safe GUI module import.

GUI 模块安全导入测试。
"""

import unittest
from pathlib import Path
from types import SimpleNamespace


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

    def test_entry_uses_video_output_for_tagged_non_mp4_video(self) -> None:
        from ultrastar_clone.gui.app import entry_uses_video_output

        entry = SimpleNamespace(video_path=Path("video.webm"))

        self.assertTrue(entry_uses_video_output(entry, Path("video.webm")))
        self.assertFalse(entry_uses_video_output(entry, Path("audio.ogg")))

    def test_lyric_target_index_discrete(self) -> None:
        from ultrastar_clone.core.playback_timeline import TimedLyricsLine, lyric_target_index

        line0 = TimedLyricsLine(start_time_ms=0, end_time_ms=3000, text="line 0",
                                source=None)  # type: ignore[arg-type]
        line1 = TimedLyricsLine(start_time_ms=3000, end_time_ms=6000, text="line 1",
                                source=None)  # type: ignore[arg-type]
        lines = (line0, line1)

        # position 0 — still on line 0
        self.assertEqual(lyric_target_index(lines, 0), 0)
        # position 2999 — still on line 0 (hasn't reached line 1 start)
        self.assertEqual(lyric_target_index(lines, 2999), 0)
        # position 3000 — crosses into line 1
        self.assertEqual(lyric_target_index(lines, 3000), 1)
        # position 5999 — still on line 1
        self.assertEqual(lyric_target_index(lines, 5999), 1)

    def test_lyric_target_index_before_first_line(self) -> None:
        from ultrastar_clone.core.playback_timeline import TimedLyricsLine, lyric_target_index

        line0 = TimedLyricsLine(start_time_ms=500, end_time_ms=1000, text="line 0",
                                source=None)  # type: ignore[arg-type]
        self.assertEqual(lyric_target_index((line0,), 0), 0)

    def test_lyric_target_index_after_last_line(self) -> None:
        from ultrastar_clone.core.playback_timeline import TimedLyricsLine, lyric_target_index

        line0 = TimedLyricsLine(start_time_ms=0, end_time_ms=1000, text="line 0",
                                source=None)  # type: ignore[arg-type]
        self.assertEqual(lyric_target_index((line0,), 1500), 0)

    def test_lyric_target_index_empty(self) -> None:
        from ultrastar_clone.core.playback_timeline import lyric_target_index

        self.assertEqual(lyric_target_index((), 500), 0)


if __name__ == "__main__":
    unittest.main()
