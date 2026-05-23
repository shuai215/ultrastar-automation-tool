"""Import page — search USDB or enter a YouTube URL and import songs.

导入页面 — 搜索 USDB 或输入 YouTube 链接来导入歌曲。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QEasingCurve, QPropertyAnimation
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
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
    PushButton,
    SubtitleLabel,
    TitleLabel,
)

from ultrastar_clone.gui.widgets import AnimatedProgressBar, PreferredRowsTable
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
        content_layout.setSpacing(24)

        content_layout.addWidget(TitleLabel("UltraStar Import"))
        content_layout.addWidget(BodyLabel("Search USDB, download the UltraStar txt file, and optionally convert media."))

        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 22)
        card_layout.setSpacing(12)

        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["Search USDB", "Direct YouTube URL"])
        card_layout.addWidget(self.mode_combo)

        self._search_group = QWidget()
        search_layout = QVBoxLayout(self._search_group)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)

        self.artist_edit = LineEdit()
        self.artist_edit.setPlaceholderText("Artist")
        self.artist_edit.setText("Coldplay")
        self.title_edit = LineEdit()
        self.title_edit.setPlaceholderText("Title")
        self.title_edit.setText("Yellow")
        self.artist_edit.textChanged.connect(lambda _text: self.set_search_results([]))
        self.title_edit.textChanged.connect(lambda _text: self.set_search_results([]))

        search_btn = PushButton(FIF.HOME, "Search USDB")
        search_btn.clicked.connect(self._emit_search)

        search_layout.addWidget(self.artist_edit)
        search_layout.addWidget(self.title_edit)
        search_layout.addWidget(search_btn)
        card_layout.addWidget(self._search_group)

        self.url_edit = LineEdit()
        self.url_edit.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_edit.setVisible(False)
        card_layout.addWidget(self.url_edit)

        self.result_table = PreferredRowsTable(6, 0, 3)
        self.result_table.setHorizontalHeaderLabels(["ID", "Artist", "Title"])
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.result_table.setVisible(False)
        card_layout.addWidget(self.result_table)

        content_layout.addWidget(card)

        self.mode_combo.currentTextChanged.connect(self._sync_mode)
        self._sync_mode(self.mode_combo.currentText())

        self.start_btn = PrimaryPushButton(FIF.PLAY, "Start import")
        self.start_btn.clicked.connect(self._emit_start)
        content_layout.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._progress_area = QWidget()
        self._progress_area.setVisible(False)
        progress_layout = QVBoxLayout(self._progress_area)
        progress_layout.setContentsMargins(34, 0, 34, 12)
        progress_layout.setSpacing(8)

        self.progress_label = BodyLabel("")
        self.progress = AnimatedProgressBar()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress)

        content_layout.addWidget(self._progress_area)
        content_layout.addStretch(1)

    def _emit_search(self) -> None:
        self.searchRequested.emit(
            {
                "artist": self.artist_edit.text().strip(),
                "title": self.title_edit.text().strip(),
            }
        )

    def _sync_mode(self, text: str) -> None:
        is_search = text == "Search USDB"
        self._crossfade_widgets(self._search_group, is_search)
        self._crossfade_widgets(self.url_edit, not is_search)
        if not is_search:
            self.set_search_results([])
        self.result_table.setVisible(is_search and self.result_table.rowCount() > 0)

    def _crossfade_widgets(self, widget: QWidget, visible: bool) -> None:
        if widget.isVisible() == visible:
            return
        if visible:
            widget.setGraphicsEffect(None)
            widget.setVisible(True)
            return
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(1.0)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(180)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: widget.setVisible(False))
        anim.start()

    def set_search_results(self, candidates: list[dict]) -> None:
        self.result_table.setRowCount(len(candidates))
        for row, candidate in enumerate(candidates):
            self.result_table.setItem(row, 0, QTableWidgetItem(candidate["song_id"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(candidate["artist"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(candidate["title"]))
        self.result_table.setVisible(bool(candidates))
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
        if running:
            self.progress.set_value_instant(0)
            self.progress_label.setText("Starting...")
            self._progress_area.setVisible(True)
            self._animate_progress_in()
        else:
            self._animate_progress_out()

    def set_done(self) -> None:
        self.progress.set_value_instant(100)
        self.progress_label.setText("Import complete")

        self._success_flash = QPropertyAnimation(self.progress.bar, b"value")
        self._success_flash.setDuration(600)
        self._success_flash.setStartValue(95)
        self._success_flash.setEndValue(100)
        self._success_flash.setEasingCurve(QEasingCurve.Type.OutBack)
        self._success_flash.start()
        self._success_flash.finished.connect(lambda: self.progress.set_value_animated(100))

        self.start_btn.setEnabled(True)

    def set_progress(self, value: int, message: str) -> None:
        self.progress.set_value_animated(max(0, min(100, value)))
        self.progress_label.setText(message)

    def _animate_progress_in(self) -> None:
        self._progress_area.setMaximumHeight(0)
        self._progress_area.show()
        hint = self._progress_area.sizeHint().height()
        anim = QPropertyAnimation(self._progress_area, b"maximumHeight")
        anim.setDuration(350)
        anim.setStartValue(0)
        anim.setEndValue(hint + 100)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._expand_anim = anim

    def _animate_progress_out(self) -> None:
        anim = QPropertyAnimation(self._progress_area, b"maximumHeight")
        anim.setDuration(300)
        anim.setStartValue(self._progress_area.height())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self._progress_area.hide)
        anim.start()
