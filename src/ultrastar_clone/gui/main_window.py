"""Main window — navigation, page switching, signal wiring.

主窗口 — 页面导航、切换和信号连接。
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QThread
from qfluentwidgets import FluentIcon as FIF, FluentWindow, InfoBar, InfoBarPosition

from ultrastar_clone.gui.home_page import HomePage
from ultrastar_clone.gui.library_page import LibraryPage
from ultrastar_clone.gui.log_page import LogPage
from ultrastar_clone.gui.player_page import PlayerPage
from ultrastar_clone.gui.settings_page import SettingsPage
from ultrastar_clone.gui.workers import ImportWorker, SearchWorker
from ultrastar_clone.models import SongRequest
from ultrastar_clone.services.settings import load_stored_credentials


class UltraStarFluentWindow(FluentWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UltraStar Clone")
        self.resize(1060, 720)
        self.home = HomePage()
        self.library = LibraryPage()
        self.player = PlayerPage()
        self.settings = SettingsPage()
        self.logs = LogPage()

        self.addSubInterface(self.home, FIF.HOME, "Import")
        self.addSubInterface(self.library, FIF.FOLDER, "Library")
        self.addSubInterface(self.player, FIF.PLAY, "Player")
        self.addSubInterface(self.logs, FIF.MESSAGE, "Logs")
        self.addSubInterface(self.settings, FIF.SETTING, "Settings")

        self.home.startRequested.connect(self.start_import)
        self.home.searchRequested.connect(self.search_usdb)
        self.library.playRequested.connect(self.open_player)
        self.player.backRequested.connect(self.return_to_library)
        self.player.playbackEnded.connect(self.return_to_library)
        self.thread: QThread | None = None
        self.worker: ImportWorker | None = None
        self.search_thread: QThread | None = None
        self.search_worker: SearchWorker | None = None

    def open_player(self, entry) -> None:
        self.player.load_entry(entry)
        self.switchTo(self.player)

    def return_to_library(self) -> None:
        self.player.stop()
        self.switchTo(self.library)

    def search_usdb(self, payload: dict) -> None:
        stored = load_stored_credentials()
        username = os.getenv("USDB_USER") or stored.username
        password = os.getenv("USDB_PASS") or stored.password
        if not username or not password:
            InfoBar.error(
                "Missing credentials",
                "Save your USDB username and password in Settings first.",
                orient=None,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
            return
        try:
            SongRequest(payload["artist"], payload["title"], download_lyrics=True, download_audio=False, download_video=False)
        except Exception as exc:
            InfoBar.error("Invalid search", str(exc), position=InfoBarPosition.TOP_RIGHT, parent=self)
            return

        self.logs.append(f"[SEARCH] {payload['artist']} - {payload['title']}")
        self.search_thread = QThread(self)
        self.search_worker = SearchWorker(username, password, payload["artist"], payload["title"])
        self.search_worker.moveToThread(self.search_thread)
        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.candidates.connect(self.on_search_results)
        self.search_worker.failed.connect(self.on_search_failed)
        self.search_worker.candidates.connect(self.search_thread.quit)
        self.search_worker.failed.connect(self.search_thread.quit)
        self.search_thread.finished.connect(self.search_worker.deleteLater)
        self.search_thread.finished.connect(self.search_thread.deleteLater)
        self.search_thread.start()

    def start_import(self, payload: dict) -> None:
        stored = load_stored_credentials()
        username = os.getenv("USDB_USER") or stored.username
        password = os.getenv("USDB_PASS") or stored.password
        needs_usdb = payload["input_mode"] == "search" or payload["download_lyrics"]
        if needs_usdb and (not username or not password):
            InfoBar.error(
                "Missing credentials",
                "Save your USDB username and password in Settings first.",
                orient=None,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
            return
        try:
            request = SongRequest(
                payload["artist"],
                payload["title"],
                payload["format"],
                target_root=Path(payload["output"]),
                input_mode=payload["input_mode"],
                youtube_url=payload["youtube_url"],
                selected_song_id=payload["selected_song_id"],
                download_lyrics=payload["download_lyrics"],
                download_audio=payload["download_audio"],
                download_video=payload["download_video"],
            )
        except Exception as exc:
            InfoBar.error("Invalid input", str(exc), position=InfoBarPosition.TOP_RIGHT, parent=self)
            return

        self.logs.append(f"[START] {request.artist} - {request.title}")
        self.home.set_running(True)
        self.library.set_root(request.target_root or Path.cwd() / "demo_output")
        self.thread = QThread(self)
        self.worker = ImportWorker(
            username,
            password,
            request,
            respect_wait=payload["respect_wait"],
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.logs.append)
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_search_results(self, candidates: list) -> None:
        self.home.set_search_results(candidates)
        self.logs.append(f"[SEARCH] Found {len(candidates)} result(s)")
        if not candidates:
            InfoBar.warning("No results", "No USDB songs matched that search.", position=InfoBarPosition.TOP_RIGHT, parent=self)

    def on_search_failed(self, message: str) -> None:
        self.logs.append(f"[ERROR] Search failed: {message}")
        InfoBar.error("Search failed", message, position=InfoBarPosition.TOP_RIGHT, parent=self)

    def on_progress(self, value: int, message: str) -> None:
        self.home.set_progress(value, message)
        self.logs.append(f"[PROGRESS] {value}% - {message}")

    def on_done(self, song_folder: str, txt_path: str, media_path: str) -> None:
        self.home.set_done()
        self.logs.append(f"[DONE] Song folder: {song_folder}")
        if txt_path:
            self.logs.append(f"[DONE] TXT file: {txt_path}")
        if media_path:
            self.logs.append(f"[DONE] Media file: {media_path}")
        self.library.refresh()
        InfoBar.success("Import complete", song_folder, position=InfoBarPosition.TOP_RIGHT, parent=self)

    def on_failed(self, message: str) -> None:
        self.home.set_running(False)
        self.home.set_progress(0, "Import failed")
        self.logs.append(f"[ERROR] {message}")
        InfoBar.error("Import failed", message, position=InfoBarPosition.TOP_RIGHT, parent=self)
