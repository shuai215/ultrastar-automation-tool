"""Tests for lyric playback timing."""

from __future__ import annotations

import unittest

from ultrastar_clone.core.playback_timeline import build_timed_lyrics, lyrics_at_position
from ultrastar_clone.core.song_parser import LyricsLine, Note, Song


class PlaybackTimelineTests(unittest.TestCase):
    def test_build_timed_lyrics_uses_ultrastar_note_units(self) -> None:
        song = Song(
            title="Song",
            artist="Artist",
            audio_filename="",
            video_filename="",
            cover_filename="",
            bpm=150.0,
            gap_ms=1000,
            lyrics=(
                LyricsLine(
                    notes=(Note(0, 4, 1, "Hello"),),
                    text="Hello",
                    start_beat=0,
                    end_beat=4,
                ),
                LyricsLine(
                    notes=(Note(8, 4, 1, "World"),),
                    text="World",
                    start_beat=8,
                    end_beat=12,
                ),
            ),
        )

        lines = build_timed_lyrics(song)

        self.assertEqual(lines[0].start_time_ms, 1000)
        self.assertEqual(lines[0].end_time_ms, 1400)
        self.assertEqual(lines[1].start_time_ms, 1800)
        self.assertEqual(lines[1].end_time_ms, 2200)

    def test_lyrics_at_position_returns_previous_current_and_next(self) -> None:
        song = Song(
            title="Song",
            artist="Artist",
            audio_filename="",
            video_filename="",
            cover_filename="",
            bpm=150.0,
            gap_ms=1000,
            lyrics=(
                LyricsLine((Note(0, 4, 1, "Hello"),), "Hello", 0, 4),
                LyricsLine((Note(8, 4, 1, "World"),), "World", 8, 12),
            ),
        )
        lines = build_timed_lyrics(song)

        before = lyrics_at_position(lines, 900)
        current = lyrics_at_position(lines, 1100)
        between = lyrics_at_position(lines, 1600)
        after = lyrics_at_position(lines, 2300)

        self.assertIsNone(before.previous)
        self.assertIsNone(before.current)
        self.assertEqual(before.next.text, "Hello")
        self.assertEqual(current.current.text, "Hello")
        self.assertEqual(current.next.text, "World")
        self.assertEqual(between.previous.text, "Hello")
        self.assertIsNone(between.current)
        self.assertEqual(between.next.text, "World")
        self.assertEqual(after.previous.text, "World")
        self.assertIsNone(after.current)
        self.assertIsNone(after.next)

    def test_missing_bpm_or_empty_lyrics_returns_empty_timeline(self) -> None:
        song = Song(
            title="Song",
            artist="Artist",
            audio_filename="",
            video_filename="",
            cover_filename="",
            bpm=None,
            gap_ms=0,
            lyrics=(),
        )

        self.assertEqual(build_timed_lyrics(song), ())
        self.assertIsNone(lyrics_at_position((), 1000).current)

    def test_non_finite_bpm_returns_empty_timeline(self) -> None:
        for bpm in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(bpm=bpm):
                song = Song(
                    title="Song",
                    artist="Artist",
                    audio_filename="",
                    video_filename="",
                    cover_filename="",
                    bpm=bpm,
                    gap_ms=1000,
                    lyrics=(
                        LyricsLine((Note(0, 4, 1, "Hello"),), "Hello", 0, 4),
                    ),
                )

                self.assertEqual(build_timed_lyrics(song), ())

    def test_lyrics_at_position_uses_start_inclusive_end_exclusive_windows(self) -> None:
        song = Song(
            title="Song",
            artist="Artist",
            audio_filename="",
            video_filename="",
            cover_filename="",
            bpm=150.0,
            gap_ms=1000,
            lyrics=(
                LyricsLine((Note(0, 4, 1, "Hello"),), "Hello", 0, 4),
                LyricsLine((Note(8, 4, 1, "World"),), "World", 8, 12),
            ),
        )
        lines = build_timed_lyrics(song)

        at_first_start = lyrics_at_position(lines, 1000)
        at_first_end = lyrics_at_position(lines, 1400)
        at_second_start = lyrics_at_position(lines, 1800)
        at_second_end = lyrics_at_position(lines, 2200)

        self.assertEqual(at_first_start.current.text, "Hello")
        self.assertIsNone(at_first_start.previous)
        self.assertEqual(at_first_end.previous.text, "Hello")
        self.assertIsNone(at_first_end.current)
        self.assertEqual(at_first_end.next.text, "World")
        self.assertEqual(at_second_start.previous.text, "Hello")
        self.assertEqual(at_second_start.current.text, "World")
        self.assertEqual(at_second_end.previous.text, "World")
        self.assertIsNone(at_second_end.current)
        self.assertIsNone(at_second_end.next)


if __name__ == "__main__":
    unittest.main()
