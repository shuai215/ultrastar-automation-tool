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

    def test_entry_uses_video_output_for_tagged_non_mp4_video(self) -> None:
        from ultrastar_clone.gui.app import entry_uses_video_output

        entry = SimpleNamespace(video_path=Path("video.webm"))

        self.assertTrue(entry_uses_video_output(entry, Path("video.webm")))
        self.assertFalse(entry_uses_video_output(entry, Path("audio.ogg")))

    def test_lyric_transition_only_runs_when_current_text_changes(self) -> None:
        from ultrastar_clone.gui.app import lyric_transition_required

        self.assertFalse(lyric_transition_required("Hello", "Hello"))
        self.assertFalse(lyric_transition_required("", ""))
        self.assertTrue(lyric_transition_required("Hello", "world"))

    def test_lyric_display_payload_keeps_previous_line_during_gap(self) -> None:
        from ultrastar_clone.gui.app import lyric_display_payload

        previous = SimpleNamespace(text="Life is sweet as honey", start_time_ms=1000, end_time_ms=2000)
        next_line = SimpleNamespace(text="Yeah this beat cha-ching", start_time_ms=3000, end_time_ms=4000)
        window = SimpleNamespace(previous=previous, current=None, next=next_line)

        self.assertEqual(
            lyric_display_payload(window, 2500),
            ("", "Life is sweet as honey", "Yeah this beat cha-ching"),
        )


if __name__ == "__main__":
    unittest.main()

