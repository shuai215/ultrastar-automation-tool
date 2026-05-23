"""Settings page — credentials, theme, and import defaults.

设置页面 — 凭据、主题和导入默认值。
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QUrl
from qfluentwidgets import (
    CardWidget,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PasswordLineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    Theme,
    TitleLabel,
    setTheme,
)

from ultrastar_clone.services.settings import (
    load_stored_credentials,
    load_stored_preferences,
    save_stored_credentials,
    save_stored_preferences,
)

THEME_LABELS = {
    "auto": "Follow system",
    "light": "Light",
    "dark": "Dark",
}


def theme_from_key(theme_key: str):
    if theme_key == "light":
        return Theme.LIGHT
    if theme_key == "dark":
        return Theme.DARK
    return Theme.AUTO


def theme_key_from_label(label: str) -> str:
    normalized = label.strip().lower()
    if normalized == "light":
        return "light"
    if normalized == "dark":
        return "dark"
    return "auto"


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("settingsPage")
        self._prefs_dirty = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(18)

        layout.addWidget(TitleLabel("Settings"))

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(18)
        layout.addWidget(scroll_area, 1)

        # USDB account card
        cred_card = CardWidget(self)
        cred_layout = QVBoxLayout(cred_card)
        cred_layout.setContentsMargins(22, 20, 22, 22)
        cred_layout.setSpacing(12)

        self.user_edit = LineEdit()
        self.user_edit.setPlaceholderText("USDB_USER")
        stored = load_stored_credentials()
        self.user_edit.setText(os.getenv("USDB_USER", stored.username))
        self.pass_edit = PasswordLineEdit()
        self.pass_edit.setPlaceholderText("USDB_PASS")
        self.pass_edit.setText(os.getenv("USDB_PASS", stored.password))
        preferences = load_stored_preferences()
        self.theme_combo = ComboBox()
        self.theme_combo.addItems(list(THEME_LABELS.values()))
        self.theme_combo.setCurrentText(THEME_LABELS.get(preferences.theme, THEME_LABELS["auto"]))
        self.theme_combo.currentTextChanged.connect(self.apply_theme)

        save_cred_btn = PrimaryPushButton(FIF.SAVE, "Save credentials")
        save_cred_btn.clicked.connect(self.save_credentials)
        register_btn = PushButton(FIF.HOME, "Register USDB account")
        register_btn.clicked.connect(self.open_usdb_registration)

        cred_layout.addWidget(SubtitleLabel("USDB account"))
        cred_layout.addWidget(self.user_edit)
        cred_layout.addWidget(self.pass_edit)
        cred_layout.addWidget(save_cred_btn)
        cred_layout.addWidget(register_btn)
        cred_layout.addWidget(SubtitleLabel("Theme"))
        cred_layout.addWidget(self.theme_combo)
        scroll_layout.addWidget(cred_card)

        # Destination defaults card
        dest_card = CardWidget(self)
        dest_layout = QVBoxLayout(dest_card)
        dest_layout.setContentsMargins(22, 20, 22, 22)
        dest_layout.setSpacing(12)

        self.output_edit = LineEdit()
        self.output_edit.setPlaceholderText("Output folder")
        self.output_edit.setText(preferences.output_folder or str(Path.cwd() / "demo_output"))

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        browse_btn = PushButton(FIF.FOLDER, "Browse")
        browse_btn.clicked.connect(self._choose_output)
        output_row.addWidget(browse_btn)

        self.download_lyrics = CheckBox("Download lyrics TXT")
        self.download_lyrics.setChecked(preferences.download_lyrics)
        self.download_audio = CheckBox("Download MP3 audio")
        self.download_audio.setChecked(preferences.download_audio)
        self.download_video = CheckBox("Download video MP4")
        self.download_video.setChecked(preferences.download_video)
        self.respect_wait = CheckBox("Respect USDB wait")
        self.respect_wait.setChecked(preferences.respect_wait)

        for cb in (self.download_lyrics, self.download_audio, self.download_video, self.respect_wait):
            cb.stateChanged.connect(self._mark_prefs_dirty)

        save_prefs_btn = PrimaryPushButton(FIF.SAVE, "Save defaults")
        save_prefs_btn.clicked.connect(self.save_preferences)

        option_row = QHBoxLayout()
        option_row.addWidget(self.download_lyrics)
        option_row.addWidget(self.download_audio)
        option_row.addWidget(self.download_video)
        option_row.addStretch(1)

        wait_row = QHBoxLayout()
        wait_row.addWidget(self.respect_wait)
        wait_row.addStretch(1)

        dest_layout.addWidget(SubtitleLabel("Default import destination"))
        dest_layout.addLayout(output_row)
        dest_layout.addLayout(option_row)
        dest_layout.addLayout(wait_row)
        dest_layout.addWidget(save_prefs_btn)
        scroll_layout.addWidget(dest_card)
        scroll_layout.addStretch(1)

    def save_credentials(self) -> None:
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        os.environ["USDB_USER"] = username
        os.environ["USDB_PASS"] = password
        save_stored_credentials(username, password)
        InfoBar.success("Saved", "Credentials will be reused on future launches.", parent=self)

    def open_usdb_registration(self) -> None:
        QDesktopServices.openUrl(QUrl("https://usdb.animux.de/index.php?link=register"))

    def _choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)
            self._mark_prefs_dirty()

    def _mark_prefs_dirty(self) -> None:
        self._prefs_dirty = True

    def save_preferences(self) -> None:
        save_stored_preferences(
            theme=theme_key_from_label(self.theme_combo.currentText()),
            output_folder=self.output_edit.text().strip(),
            download_lyrics=self.download_lyrics.isChecked(),
            download_audio=self.download_audio.isChecked(),
            download_video=self.download_video.isChecked(),
            respect_wait=self.respect_wait.isChecked(),
        )
        self._prefs_dirty = False
        InfoBar.success("Saved", "Import defaults will be reused on future launches.", parent=self)

    def apply_theme(self, label: str) -> None:
        theme_key = theme_key_from_label(label)
        setTheme(theme_from_key(theme_key))
        save_stored_preferences(theme_key)
