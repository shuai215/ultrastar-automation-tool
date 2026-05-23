"""Library page — browse and play local song folders.

曲库页面 — 浏览和播放本地歌曲文件夹。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
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
    TransparentToolButton,
)

from ultrastar_clone.services.library import scan_song_library


ACCENT_BLUE = QColor("#0078D4")


def _format_icon(fif: FIF, enabled: bool) -> QIcon:
    pixmap = fif.icon().pixmap(20, 20)
    if enabled:
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.GlobalColor.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), ACCENT_BLUE)
        painter.end()
        return QIcon(tinted)
    dimmed = QPixmap(pixmap.size())
    dimmed.fill(Qt.GlobalColor.transparent)
    painter = QPainter(dimmed)
    painter.setOpacity(0.25)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return QIcon(dimmed)


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
        self.table.setHorizontalHeaderLabels(["Title", "Artist", "TXT", "MP3", "MP4", "Folder", ""])
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 44)
        self.table.setColumnWidth(3, 44)
        self.table.setColumnWidth(4, 44)
        self.table.setColumnWidth(6, 48)
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

            txt_item = QTableWidgetItem()
            txt_item.setIcon(_format_icon(FIF.DOCUMENT, entry.txt_path is not None))
            txt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, txt_item)

            mp3_item = QTableWidgetItem()
            mp3_item.setIcon(_format_icon(FIF.MUSIC, entry.has_mp3))
            mp3_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, mp3_item)

            mp4_item = QTableWidgetItem()
            mp4_item.setIcon(_format_icon(FIF.VIDEO, entry.has_mp4))
            mp4_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, mp4_item)

            self.table.setItem(row, 5, QTableWidgetItem(str(entry.folder)))

            play_btn = TransparentToolButton(FIF.PLAY)
            play_btn.setEnabled(entry.is_playable)
            play_btn.clicked.connect(lambda _checked=False, selected=entry: self.playRequested.emit(selected))
            self.table.setCellWidget(row, 6, play_btn)

        self.summary_label.setText(f"{len(self.entries)} songs")
