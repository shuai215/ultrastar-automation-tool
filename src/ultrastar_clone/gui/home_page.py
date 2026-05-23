"""Import page — search USDB or enter a YouTube URL and import songs.

导入页面 — 搜索 USDB 或输入 YouTube 链接来导入歌曲。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon as FIF,
    LineEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SubtitleLabel,
    TitleLabel,
)

from ultrastar_clone.gui.widgets import PreferredRowsTable
from ultrastar_clone.services.settings import load_stored_preferences


class HomePage(QWidget):
    startRequested = pyqtSignal(dict)
    searchRequested = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("homePage")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout.addWidget(scroll_area)
        scroll_area.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(34, 28, 34, 28)
        content_layout.setSpacing(18)

        title = TitleLabel("UltraStar Import")
        subtitle = BodyLabel("Search USDB, download the UltraStar txt file, and optionally convert media.")
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)

        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 22)
        card_layout.setSpacing(14)

        self.artist_edit = LineEdit()
        self.artist_edit.setPlaceholderText("Artist")
        self.artist_edit.setText("Coldplay")
        self.title_edit = LineEdit()
        self.title_edit.setPlaceholderText("Title")
        self.title_edit.setText("Yellow")
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["Search USDB", "Direct YouTube URL"])
        self.url_edit = LineEdit()
        self.url_edit.setPlaceholderText("YouTube URL")

        search_btn = PushButton(FIF.HOME, "Search USDB")
        search_btn.clicked.connect(self._emit_search)

        self.start_btn = PrimaryPushButton(FIF.PLAY, "Start import")
        self.start_btn.clicked.connect(self._emit_start)

        self.progress = ProgressBar()
        self.progress.setValue(0)
        self.progress_label = BodyLabel("Ready")
        self.txt_progress = ProgressBar()
        self.txt_progress.setValue(0)
        self.txt_progress_label = BodyLabel("TXT download 0%")
        self.media_progress = ProgressBar()
        self.media_progress.setValue(0)
        self.media_progress_label = BodyLabel("Media download 0%")

        card_layout.addWidget(SubtitleLabel("Song"))
        card_layout.addWidget(self.mode_combo)
        card_layout.addWidget(self.artist_edit)
        card_layout.addWidget(self.title_edit)
        card_layout.addWidget(self.url_edit)
        card_layout.addWidget(search_btn)
        self.result_table = PreferredRowsTable(6, 0, 3)
        self.result_table.setHorizontalHeaderLabels(["ID", "Artist", "Title"])
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        row_height = self.result_table.verticalHeader().defaultSectionSize()
        header_height = self.result_table.horizontalHeader().height()
        self.result_table.setFixedHeight(header_height + row_height * 6 + 8)
        card_layout.addWidget(self.result_table)
        self.artist_edit.textChanged.connect(lambda _text: self.set_search_results([]))
        self.title_edit.textChanged.connect(lambda _text: self.set_search_results([]))
        card_layout.addWidget(self.start_btn)
        card_layout.addWidget(self.progress_label)
        card_layout.addWidget(self.progress)
        card_layout.addWidget(self.txt_progress_label)
        card_layout.addWidget(self.txt_progress)
        card_layout.addWidget(self.media_progress_label)
        card_layout.addWidget(self.media_progress)
        content_layout.addWidget(card)
        content_layout.addStretch(1)

    def _emit_search(self) -> None:
        self.searchRequested.emit(
            {
                "artist": self.artist_edit.text().strip(),
                "title": self.title_edit.text().strip(),
            }
        )

    def set_search_results(self, candidates: list[dict]) -> None:
        self.result_table.setRowCount(len(candidates))
        for row, candidate in enumerate(candidates):
            self.result_table.setItem(row, 0, QTableWidgetItem(candidate["song_id"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(candidate["artist"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(candidate["title"]))
        if candidates:
            self.result_table.selectRow(0)

    def selected_candidate(self) -> dict | None:
        row = self.result_table.currentRow()
        if row < 0:
            return None
        return {
            "song_id": self.result_table.item(row, 0).text(),
            "artist": self.result_table.item(row, 1).text(),
            "title": self.result_table.item(row, 2).text(),
        }

    def _emit_start(self) -> None:
        prefs = load_stored_preferences()
        input_mode = "url" if self.mode_combo.currentText() == "Direct YouTube URL" else "search"
        selected = self.selected_candidate() if input_mode == "search" else None
        artist = selected["artist"] if selected else self.artist_edit.text().strip()
        title = selected["title"] if selected else self.title_edit.text().strip()
        download_lyrics = prefs.download_lyrics if input_mode == "search" else False
        media_format = "mp3" if prefs.download_audio and not prefs.download_video else "mp4"
        output = prefs.output_folder or str(Path.cwd() / "demo_output")
        self.startRequested.emit(
            {
                "input_mode": input_mode,
                "artist": artist,
                "title": title,
                "selected_song_id": selected["song_id"] if selected else None,
                "youtube_url": self.url_edit.text().strip(),
                "output": output,
                "format": media_format,
                "download_lyrics": download_lyrics,
                "download_audio": prefs.download_audio,
                "download_video": prefs.download_video,
                "respect_wait": prefs.respect_wait,
            }
        )

    def set_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.progress.setValue(35 if running else 0)
        self.progress_label.setText("Running..." if running else "Ready")
        self.txt_progress.setValue(0)
        self.txt_progress_label.setText("TXT download 0%")
        self.media_progress.setValue(0)
        self.media_progress_label.setText("Media download 0%")

    def set_done(self) -> None:
        self.progress.setValue(100)
        self.progress_label.setText("Import complete")
        self.start_btn.setEnabled(True)

    def set_progress(self, value: int, message: str) -> None:
        self.progress.setValue(max(0, min(100, value)))
        self.progress_label.setText(message)

    def set_txt_progress(self, value: int, message: str) -> None:
        percent = max(0, min(100, value))
        self.txt_progress.setValue(percent)
        self.txt_progress_label.setText(f"TXT download {percent}%")

    def set_media_progress(self, value: int, message: str) -> None:
        percent = max(0, min(100, value))
        self.media_progress.setValue(percent)
        self.media_progress_label.setText(f"Media download {percent}%")
