"""Library page — browse and play local song folders.

曲库页面 — 浏览和播放本地歌曲文件夹。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PushButton,
    TitleLabel,
    TransparentToolButton,
)

from ultrastar_clone.services.library import scan_song_library
from ultrastar_clone.services.settings import load_favorites, save_favorites


class LibraryPage(QWidget):
    playRequested = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("libraryPage")
        self.root = Path.cwd() / "demo_output"
        self.entries = []
        self.favorites: set[str] = load_favorites()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(14)

        self.title_label = TitleLabel("Song Library")
        layout.addWidget(self.title_label)

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

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Title", "Artist", "Assets", "Folder", "", "", "Play"])
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 160)
        self.table.setColumnWidth(4, 40)
        self.table.setColumnWidth(5, 40)
        self.table.setColumnWidth(6, 56)
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

    def _toggle_favorite(self, entry) -> None:
        key = str(entry.folder)
        if key in self.favorites:
            self.favorites.discard(key)
        else:
            self.favorites.add(key)
        save_favorites(self.favorites)
        self.refresh()

    def _delete_song(self, entry) -> None:
        folder = entry.folder
        reply = QMessageBox.question(
            self,
            "Delete song folder",
            f"Delete this song folder permanently?\n\n{folder}\n\nAll files in this folder will be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            shutil.rmtree(folder)
        except OSError as exc:
            InfoBar.error(
                "Delete failed",
                str(exc),
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
            return
        if str(folder) in self.favorites:
            self.favorites.discard(str(folder))
            save_favorites(self.favorites)
        self.refresh()

    def refresh(self) -> None:
        self.root = Path(self.root_edit.text().strip() or Path.cwd() / "demo_output")
        self.entries = scan_song_library(self.root)
        self.entries.sort(key=lambda e: (str(e.folder) not in self.favorites, e.display_title.lower()))
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            title_item = QTableWidgetItem(entry.display_title)
            title_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, title_item)

            artist_item = QTableWidgetItem(entry.display_artist)
            artist_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, artist_item)

            assets_widget = QWidget()
            assets_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            assets_layout = QHBoxLayout(assets_widget)
            assets_layout.setContentsMargins(0, 0, 0, 0)
            assets_layout.setSpacing(14)
            assets_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            for label_text, tooltip_label, available in [
                ("TXT", "lyrics", entry.txt_path is not None),
                ("MP3", "audio", entry.has_mp3),
                ("MP4", "video", entry.has_mp4),
            ]:
                pair = QWidget()
                pair.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                pair_layout = QHBoxLayout(pair)
                pair_layout.setContentsMargins(0, 0, 0, 0)
                pair_layout.setSpacing(3)
                dot = QLabel("●" if available else "○")
                dot.setForegroundRole(
                    QPalette.ColorRole.Highlight if available else QPalette.ColorRole.Mid
                )
                dot.setToolTip(f"{'[OK]' if available else '[Missing]'} {label_text} {tooltip_label}")
                pair_layout.addWidget(dot)
                pair_layout.addWidget(QLabel(label_text))
                assets_layout.addWidget(pair)
            self.table.setCellWidget(row, 2, assets_widget)

            folder_item = QTableWidgetItem(entry.folder.name)
            folder_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            folder_item.setToolTip(str(entry.folder))
            self.table.setItem(row, 3, folder_item)

            # Star / favorite button
            favorited = str(entry.folder) in self.favorites
            star_btn = QPushButton("★" if favorited else "☆")
            star_btn.setFlat(True)
            star_btn.setStyleSheet("background: transparent;")
            star_btn.setFixedSize(28, 28)
            star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            star_btn.setToolTip("Remove from favorites" if favorited else "Add to favorites")
            star_btn.clicked.connect(lambda _checked=False, e=entry: self._toggle_favorite(e))
            self.table.setCellWidget(row, 4, star_btn)

            # Delete button
            del_btn = QPushButton("✕")
            del_btn.setFlat(True)
            del_btn.setStyleSheet("background: transparent;")
            del_btn.setFixedSize(28, 28)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setToolTip("Delete song folder")
            del_btn.clicked.connect(lambda _checked=False, e=entry: self._delete_song(e))
            self.table.setCellWidget(row, 5, del_btn)

            play_btn = TransparentToolButton(FIF.PLAY)
            play_btn.setEnabled(entry.is_playable)
            play_btn.setToolTip("Play" if entry.is_playable else "No playable media")
            play_btn.clicked.connect(lambda _checked=False, selected=entry: self.playRequested.emit(selected))
            self.table.setCellWidget(row, 6, play_btn)

        self.title_label.setText(f"Song Library ({len(self.entries)})")
