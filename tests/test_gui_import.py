"""Tests for safe GUI module import.

GUI 模块安全导入测试。
"""

import unittest


class GuiImportTests(unittest.TestCase):
    def test_gui_module_imports(self) -> None:
        from ultrastar_clone.gui.app import GuiDependencyError, main

        self.assertTrue(callable(main))
        self.assertTrue(GuiDependencyError)


if __name__ == "__main__":
    unittest.main()

