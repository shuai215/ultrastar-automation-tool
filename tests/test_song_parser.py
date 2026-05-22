"""Tests for UltraStar TXT parsing."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.core.song_parser import parse_ultrastar_txt


class SongParserTests(unittest.TestCase):
    def test_parse_tags_notes_and_lines(self) -> None:
        with TemporaryDirectory() as temp_dir:
            txt = Path(temp_dir) / "song.txt"
            txt.write_text(
                "\n".join(
                    [
                        "#TITLE:Yellow",
                        "#ARTIST:Coldplay",
                        "#MP3:yellow.mp3",
                        "#VIDEO:yellow.mp4",
                        "#COVER:cover.jpg",
                        "#BPM:276",
                        "#GAP:35780",
                        ": 0 4 1 Look ",
                        "* 7 3 3 at ",
                        "F 11 3 1 the ",
                        "- 16",
                        ": 20 5 4 stars",
                        "E",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            song = parse_ultrastar_txt(txt)

        self.assertEqual(song.title, "Yellow")
        self.assertEqual(song.artist, "Coldplay")
        self.assertEqual(song.audio_filename, "yellow.mp3")
        self.assertEqual(song.video_filename, "yellow.mp4")
        self.assertEqual(song.cover_filename, "cover.jpg")
        self.assertEqual(song.bpm, 276.0)
        self.assertEqual(song.gap_ms, 35780)
        self.assertEqual(len(song.lyrics), 2)
        self.assertEqual(song.lyrics[0].text, "Look at the")
        self.assertEqual([note.type for note in song.lyrics[0].notes], [":", "*", "F"])
        self.assertEqual(song.lyrics[0].start_beat, 0)
        self.assertEqual(song.lyrics[0].end_beat, 14)

    def test_audio_tag_is_audio_alias_and_missing_gap_defaults_to_zero(self) -> None:
        with TemporaryDirectory() as temp_dir:
            txt = Path(temp_dir) / "song.txt"
            txt.write_text(
                "#TITLE:Song\n#ARTIST:Artist\n#AUDIO:file.ogg\n#BPM:120\n: 0 2 1 Hi\nE\n",
                encoding="utf-8",
            )

            song = parse_ultrastar_txt(txt)

        self.assertEqual(song.audio_filename, "file.ogg")
        self.assertEqual(song.gap_ms, 0)
        self.assertEqual(song.lyrics[0].text, "Hi")

    def test_malformed_note_rows_are_skipped(self) -> None:
        with TemporaryDirectory() as temp_dir:
            txt = Path(temp_dir) / "song.txt"
            txt.write_text(
                "#TITLE:Song\n#ARTIST:Artist\n#BPM:100\n: bad row\n: 4 2 1 ok\nE\n",
                encoding="utf-8",
            )

            song = parse_ultrastar_txt(txt)

        self.assertEqual(len(song.lyrics), 1)
        self.assertEqual(song.lyrics[0].text, "ok")
        self.assertEqual(song.lyrics[0].notes[0].start_beat, 4)


if __name__ == "__main__":
    unittest.main()
