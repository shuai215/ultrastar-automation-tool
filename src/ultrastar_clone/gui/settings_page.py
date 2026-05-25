"""Settings page for credentials, theme, and import defaults."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QUrl
from qfluentwidgets import (
    CardWidget,
    CheckBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PasswordLineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TitleLabel,
)

from ultrastar_clone.services.settings import (
    load_stored_credentials,
    load_stored_preferences,
    save_stored_credentials,
    save_stored_preferences,
)

class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("settingsPage")
        self._prefs_dirty = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(18)

        layout.addWidget(TitleLabel("Settings"))

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
        save_cred_btn = PrimaryPushButton(FIF.SAVE, "Save credentials")
        save_cred_btn.clicked.connect(self.save_credentials)
        register_btn = PushButton(FIF.HOME, "Register USDB account")
        register_btn.clicked.connect(self.open_usdb_registration)

        cred_layout.addWidget(SubtitleLabel("USDB account"))
        cred_layout.addWidget(self.user_edit)
        cred_layout.addWidget(self.pass_edit)
        cred_layout.addWidget(save_cred_btn)
        cred_layout.addWidget(register_btn)
        layout.addWidget(cred_card)

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
        layout.addWidget(dest_card)
        layout.addStretch(1)

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
            theme="auto",
            output_folder=self.output_edit.text().strip(),
            download_lyrics=self.download_lyrics.isChecked(),
            download_audio=self.download_audio.isChecked(),
            download_video=self.download_video.isChecked(),
            respect_wait=self.respect_wait.isChecked(),
        )
        self._prefs_dirty = False
        InfoBar.success("Saved", "Import defaults will be reused on future launches.", parent=self)
