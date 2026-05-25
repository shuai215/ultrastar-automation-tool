"""Tests for player page layout constraints."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication


class PlayerPageLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_lyrics_do_not_use_vertical_stretches_that_push_controls_out(self) -> None:
        from ultrastar_clone.gui.player_page import PlayerPage

        page = PlayerPage()
        layout = page.layout()
        lyric_index = next(
            i for i in range(layout.count()) if layout.itemAt(i).widget() is page.lyric_display
        )

        self.assertIsNotNone(layout.itemAt(lyric_index - 1).layout())
        self.assertIsNotNone(layout.itemAt(lyric_index + 1).widget())


if __name__ == "__main__":
    unittest.main()
