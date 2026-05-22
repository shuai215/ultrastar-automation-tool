"""Tests for app settings persistence.

应用设置持久化测试。
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.services.settings import (
    load_stored_credentials,
    load_stored_preferences,
    save_stored_credentials,
    save_stored_preferences,
)


class SettingsTests(unittest.TestCase):
    def test_load_missing_credentials_returns_empty_values(self) -> None:
        with TemporaryDirectory() as temp_dir:
            credentials = load_stored_credentials(Path(temp_dir) / "missing.json")

        self.assertEqual(credentials.username, "")
        self.assertEqual(credentials.password, "")

    def test_save_and_load_credentials(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "credentials.json"

            save_stored_credentials("user", "secret", path)
            credentials = load_stored_credentials(path)

        self.assertEqual(credentials.username, "user")
        self.assertEqual(credentials.password, "secret")

    def test_load_invalid_credentials_json_returns_empty_values(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "credentials.json"
            path.write_text("{", encoding="utf-8")

            credentials = load_stored_credentials(path)

        self.assertEqual(credentials.username, "")
        self.assertEqual(credentials.password, "")

    def test_save_and_load_theme_preference(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "preferences.json"

            save_stored_preferences("dark", path)
            preferences = load_stored_preferences(path)

        self.assertEqual(preferences.theme, "dark")

    def test_invalid_theme_preference_falls_back_to_auto(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "preferences.json"

            save_stored_preferences("blue", path)
            preferences = load_stored_preferences(path)

        self.assertEqual(preferences.theme, "auto")


if __name__ == "__main__":
    unittest.main()
