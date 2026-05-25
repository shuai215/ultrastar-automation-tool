"""Tests for stable lyric strip geometry."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication


class LyricDisplayWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_scroll_geometry_uses_fixed_three_line_viewport(self) -> None:
        from ultrastar_clone.gui.widgets import LyricDisplayWidget

        widget = LyricDisplayWidget()
        widget.resize(420, 180)
        widget.set_lines(["first", "second", "third", "fourth", "fifth"])

        row_h = widget._ROW_HEIGHT
        self.assertEqual(widget._line_height, row_h)
        self.assertEqual(widget._viewport.height(), row_h * widget._VISIBLE_LINES)
        self.assertEqual(widget.height(), row_h * widget._VISIBLE_LINES)

        self.assertEqual(widget._compute_strip_y(0), 0)
        self.assertEqual(widget._compute_strip_y(1), 0)
        self.assertEqual(widget._compute_strip_y(2), row_h)
        self.assertEqual(widget._compute_strip_y(4), row_h * 2)

    def test_row_height_is_compact_without_extra_blank_line(self) -> None:
        from ultrastar_clone.gui.widgets import LyricDisplayWidget

        widget = LyricDisplayWidget()

        self.assertLessEqual(widget._ROW_HEIGHT, 36)

    def test_set_lines_rebuilds_layout_without_accumulating_stretches(self) -> None:
        from ultrastar_clone.gui.widgets import LyricDisplayWidget

        widget = LyricDisplayWidget()
        widget.set_lines(["a", "b", "c"])
        first_count = widget._strip_layout.count()

        widget.set_lines(["a", "b", "c"])

        self.assertEqual(widget._strip_layout.count(), first_count)

    def test_strip_width_follows_viewport_after_initial_show(self) -> None:
        from ultrastar_clone.gui.widgets import LyricDisplayWidget

        widget = LyricDisplayWidget()
        widget.set_lines(["first", "second", "third"])
        widget.resize(420, widget.height())
        widget.show()
        self.app.processEvents()

        self.assertEqual(widget._strip.width(), widget._viewport.viewport().width())


if __name__ == "__main__":
    unittest.main()
