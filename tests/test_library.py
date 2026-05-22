"""Tests for song library scanning.

曲库扫描测试。
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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

    def test_scan_song_library_uses_txt_metadata_and_prefers_video(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            song_folder = root / "folder-name"
            song_folder.mkdir()
            txt_path = song_folder / "song.txt"
            audio_path = song_folder / "audio.mp3"
            video_path = song_folder / "video.mp4"
            cover_path = song_folder / "cover.jpg"
            txt_path.write_text(
                "\n".join(
                    [
                        "#TITLE:Metadata Title",
                        "#ARTIST:Metadata Artist",
                        "#MP3:audio.mp3",
                        "#VIDEO:video.mp4",
                        "#COVER:cover.jpg",
                        "E",
                    ]
                ),
                encoding="utf-8",
            )
            audio_path.write_bytes(b"audio")
            video_path.write_bytes(b"video")
            cover_path.write_bytes(b"cover")
            (song_folder / "aaa.mp3").write_bytes(b"other audio")
            (song_folder / "aaa.mp4").write_bytes(b"other video")

            entries = scan_song_library(root)

        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.title, "Metadata Title")
        self.assertEqual(entry.artist, "Metadata Artist")
        self.assertEqual(entry.display_title, "Metadata Title")
        self.assertEqual(entry.display_artist, "Metadata Artist")
        self.assertTrue(entry.is_playable)
        self.assertEqual(entry.txt_path, txt_path)
        self.assertEqual(entry.audio_path, audio_path)
        self.assertEqual(entry.video_path, video_path)
        self.assertEqual(entry.cover_path, cover_path)
        self.assertEqual(entry.preferred_media_path, video_path)
        self.assertIsNone(entry.parse_error)

    def test_scan_song_library_allows_media_without_txt_and_disables_txt_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            media_only = root / "Artist - Media"
            media_only.mkdir()
            media_path = media_only / "track.mp3"
            media_path.write_bytes(b"audio")
            txt_only = root / "Artist - Lyrics"
            txt_only.mkdir()
            txt_path = txt_only / "lyrics.txt"
            txt_path.write_text("#TITLE:Lyrics Only\n#ARTIST:Artist\nE\n", encoding="utf-8")

            entries = scan_song_library(root)

        self.assertEqual([entry.name for entry in entries], ["Artist - Lyrics", "Artist - Media"])
        self.assertFalse(entries[0].is_playable)
        self.assertEqual(entries[0].txt_path, txt_path)
        self.assertIsNone(entries[0].preferred_media_path)
        self.assertTrue(entries[1].is_playable)
        self.assertIsNone(entries[1].txt_path)
        self.assertEqual(entries[1].audio_path, media_path)
        self.assertEqual(entries[1].preferred_media_path, media_path)

    def test_scan_song_library_records_txt_parse_error_and_keeps_fallback_media(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "Broken"
            folder.mkdir()
            txt_path = folder / "broken.txt"
            audio_path = folder / "fallback.mp3"
            txt_path.write_bytes(b"\xff\xfe\x00")
            audio_path.write_bytes(b"audio")

            entries = scan_song_library(root)

        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.txt_path, txt_path)
        self.assertEqual(entry.audio_path, audio_path)
        self.assertTrue(entry.is_playable)
        self.assertIsNotNone(entry.parse_error)

    def test_scan_song_library_does_not_report_alt_media_as_mp3_or_mp4(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "Alt Media"
            folder.mkdir()
            (folder / "song.txt").write_text(
                "\n".join(
                    [
                        "#TITLE:Alt Media",
                        "#AUDIO:audio.ogg",
                        "#VIDEO:video.webm",
                        "E",
                    ]
                ),
                encoding="utf-8",
            )
            (folder / "audio.ogg").write_bytes(b"audio")
            (folder / "video.webm").write_bytes(b"video")

            entries = scan_song_library(root)

        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.audio_path.name, "audio.ogg")
        self.assertEqual(entry.video_path.name, "video.webm")
        self.assertEqual(entry.preferred_media_path.name, "video.webm")
        self.assertTrue(entry.is_playable)
        self.assertFalse(entry.has_mp3)
        self.assertFalse(entry.has_mp4)
        self.assertEqual(entry.formats, "txt")

    def test_scan_song_library_rejects_tagged_media_paths_outside_folder(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "outside.mp3").write_bytes(b"outside")
            folder = root / "Unsafe"
            folder.mkdir()
            (folder / "song.txt").write_text(
                "\n".join(
                    [
                        "#TITLE:Unsafe",
                        "#MP3:..\\outside.mp3",
                        "E",
                    ]
                ),
                encoding="utf-8",
            )
            fallback_path = folder / "fallback.mp3"
            fallback_path.write_bytes(b"fallback")

            entries = scan_song_library(root)

        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.audio_path, fallback_path)
        self.assertEqual(entry.audio_path.name, "fallback.mp3")
        self.assertEqual(entry.preferred_media_path.name, "fallback.mp3")

    def test_scan_song_library_does_not_swallow_unexpected_parser_errors(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "Bug"
            folder.mkdir()
            (folder / "song.txt").write_text("#TITLE:Bug\nE\n", encoding="utf-8")

            with patch(
                "ultrastar_clone.services.library.parse_ultrastar_txt",
                side_effect=RuntimeError("bug"),
            ):
                with self.assertRaises(RuntimeError):
                    scan_song_library(root)

    def test_scan_missing_song_library_returns_empty_list(self) -> None:
        with TemporaryDirectory() as temp_dir:
            entries = scan_song_library(Path(temp_dir) / "missing")

        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
