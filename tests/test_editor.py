"""Tests for UltraStar txt editing.

UltraStar txt 编辑测试。
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.core.editor import UltraStarTextEditor


class EditorTests(unittest.TestCase):
    def test_update_media_tags_replaces_existing_tags(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            txt = tmp_path / "Song.txt"
            txt.write_text(
                "#TITLE:Song\n#ARTIST:Artist\n#MP3:old.mp3\n#VIDEO:old.mp4\n#GAP:1000\n",
                encoding="utf-8",
            )
            mp3 = tmp_path / "Artist - Song.mp3"
            mp4 = tmp_path / "Artist - Song.mp4"
            mp3.write_bytes(b"mp3")
            mp4.write_bytes(b"mp4")

            UltraStarTextEditor().update_media_tags(txt, mp3, mp4)

            content = txt.read_text(encoding="utf-8")
            self.assertIn("#MP3:Artist - Song.mp3", content)
            self.assertIn("#VIDEO:Artist - Song.mp4", content)

    def test_gap_can_be_read_written_and_adjusted(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            txt = tmp_path / "Song.txt"
            txt.write_text("#TITLE:Song\n#GAP:1200\n", encoding="utf-8")
            editor = UltraStarTextEditor()

            self.assertEqual(editor.read_gap(txt), 1200)
            editor.write_gap(txt, 900)
            self.assertEqual(editor.read_gap(txt), 900)
            self.assertEqual(editor.adjust_gap(txt, -1000), 0)
            self.assertTrue((tmp_path / "Song.txt.bak").exists())

    def test_missing_gap_raises_clear_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            txt = Path(temp_dir) / "Song.txt"
            txt.write_text("#TITLE:Song\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing #GAP"):
                UltraStarTextEditor().read_gap(txt)


if __name__ == "__main__":
    unittest.main()

