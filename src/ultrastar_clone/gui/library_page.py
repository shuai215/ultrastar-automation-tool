"""Library page — browse and play local song folders.

曲库页面 — 浏览和播放本地歌曲文件夹。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    FluentIcon as FIF,
    LineEdit,
    PushButton,
    TitleLabel,
)

from ultrastar_clone.services.library import scan_song_library


class LibraryPage(QWidget):
    playRequested = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("libraryPage")
        self.root = Path.cwd() / "demo_output"
        self.entries = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(14)

        layout.addWidget(TitleLabel("Song Library"))

        self.root_edit = LineEdit()
        self.root_edit.setPlaceholderText("Song library folder")
        self.root_edit.setText(str(self.root))

        root_row = QHBoxLayout()
        root_row.addWidget(self.root_edit, 1)
        browse_btn = PushButton(FIF.FOLDER, "Browse")
        browse_btn.clicked.connect(self.choose_root)
        refresh_btn = PushButton(FIF.FOLDER, "Refresh")
        refresh_btn.clicked.connect(self.refresh)
        root_row.addWidget(browse_btn)
        root_row.addWidget(refresh_btn)
        layout.addLayout(root_row)

        self.summary_label = BodyLabel("0 songs")
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Title", "Artist", "TXT", "MP3", "MP4", "Folder", "Play"])
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table, 1)

    def _on_double_click(self, row: int, _col: int) -> None:
        if 0 <= row < len(self.entries) and self.entries[row].is_playable:
            self.playRequested.emit(self.entries[row])

    def choose_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose song library folder", self.root_edit.text())
        if folder:
            self.root_edit.setText(folder)
            self.refresh()

    def set_root(self, root: Path) -> None:
        self.root = root
        self.root_edit.setText(str(root))
        self.refresh()

    def refresh(self) -> None:
        self.root = Path(self.root_edit.text().strip() or Path.cwd() / "demo_output")
        self.entries = scan_song_library(self.root)
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.display_title))
            self.table.setItem(row, 1, QTableWidgetItem(entry.display_artist))
            self.table.setItem(row, 2, QTableWidgetItem("yes" if entry.txt_path else ""))
            self.table.setItem(row, 3, QTableWidgetItem("yes" if entry.has_mp3 else ""))
            self.table.setItem(row, 4, QTableWidgetItem("yes" if entry.has_mp4 else ""))
            self.table.setItem(row, 5, QTableWidgetItem(str(entry.folder)))
            play_btn = PushButton("Play")
            play_btn.setEnabled(entry.is_playable)
            play_btn.clicked.connect(lambda _checked=False, selected=entry: self.playRequested.emit(selected))
            self.table.setCellWidget(row, 6, play_btn)
        self.summary_label.setText(f"{len(self.entries)} songs")
