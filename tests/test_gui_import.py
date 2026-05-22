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


if __name__ == "__main__":
    unittest.main()

