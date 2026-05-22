"""QFluentWidgets desktop GUI for the importer.

导入器的 QFluentWidgets 桌面图形界面。
"""

from __future__ import annotations

import os
from pathlib import Path

from ultrastar_clone.core.converter import NoMediaConverter, YtDlpConverter
from ultrastar_clone.core.downloader import USDBTextDownloader
from ultrastar_clone.core.scraper import USDBScraper
from ultrastar_clone.models import SongRequest
from ultrastar_clone.services.controller import ImportController
from ultrastar_clone.services.logger import build_logger
from ultrastar_clone.services.settings import (
    AppSettings,
    default_log_dir,
    load_stored_credentials,
    save_stored_credentials,
)

try:
    from PyQt6.QtCore import QObject, QThread, pyqtSignal
    from PyQt6.QtWidgets import QApplication, QFileDialog, QFrame, QHBoxLayout, QVBoxLayout, QWidget
    from qfluentwidgets import (
        BodyLabel,
        CardWidget,
        CheckBox,
        ComboBox,
        FluentIcon as FIF,
        FluentWindow,
        InfoBar,
        InfoBarPosition,
        LineEdit,
        PasswordLineEdit,
        PrimaryPushButton,
        ProgressBar,
        PushButton,
        SubtitleLabel,
        TextEdit,
        Theme,
        TitleLabel,
        setTheme,
    )
except (ModuleNotFoundError, ImportError) as exc:  # pragma: no cover - exercised only without GUI deps
    missing_dependency_error = exc
else:
    missing_dependency_error = None


class GuiDependencyError(RuntimeError):
    pass


if missing_dependency_error is None:

    class SignalLogger:
        def __init__(self, signal) -> None:
            self.signal = signal

        def info(self, message: str, *args) -> None:
            self._emit("INFO", message, *args)

        def warning(self, message: str, *args) -> None:
            self._emit("WARN", message, *args)

        def error(self, message: str, *args) -> None:
            self._emit("ERROR", message, *args)

        def _emit(self, level: str, message: str, *args) -> None:
            if args:
                message = message % args
            self.signal.emit(f"[{level}] {message}")


    class ImportWorker(QObject):
        log = pyqtSignal(str)
        progress = pyqtSignal(int, str)
        done = pyqtSignal(str, str, str)
        failed = pyqtSignal(str)

        def __init__(
            self,
            username: str,
            password: str,
            request: SongRequest,
            skip_media: bool,
            respect_wait: bool,
            cookie_browser: str | None,
        ) -> None:
            super().__init__()
            self.username = username
            self.password = password
            self.request = request
            self.skip_media = skip_media
            self.respect_wait = respect_wait
            self.cookie_browser = cookie_browser

        def run(self) -> None:
            try:
                output = self.request.target_root or Path.cwd() / "demo_output"
                settings = AppSettings(song_root=output, log_dir=default_log_dir())
                file_logger = build_logger(settings.log_dir)
                gui_logger = SignalLogger(self.log)

                class CombinedLogger:
                    def info(_, message: str, *args) -> None:
                        file_logger.info(message, *args)
                        gui_logger.info(message, *args)

                    def warning(_, message: str, *args) -> None:
                        file_logger.warning(message, *args)
                        gui_logger.warning(message, *args)

                    def error(_, message: str, *args) -> None:
                        file_logger.error(message, *args)
                        gui_logger.error(message, *args)

                    def progress(_, value: int, message: str) -> None:
                        self.progress.emit(value, message)

                scraper = USDBScraper(self.username, self.password)
                downloader = USDBTextDownloader(opener=scraper.opener, respect_wait=self.respect_wait)
                converter = (
                    NoMediaConverter()
                    if self.skip_media
                    else YtDlpConverter(
                        progress_callback=self._media_progress,
                        cookies_from_browser=self.cookie_browser,
                    )
                )
                controller = ImportController(settings, scraper, downloader, converter, logger=CombinedLogger())
                result = controller.import_song(self.request)
                media_path = str(result.media_path) if result.media_path else ""
                self.done.emit(str(result.song_folder), str(result.txt_path), media_path)
            except Exception as exc:
                self.failed.emit(str(exc))

        def _media_progress(self, percent: int, message: str) -> None:
            scaled = 60 + int(percent * 0.25)
            self.progress.emit(min(scaled, 85), f"Media download {percent}%")


    class HomePage(QWidget):
        startRequested = pyqtSignal(dict)

        def __init__(self) -> None:
            super().__init__()
            self.setObjectName("homePage")
            self._build_ui()

        def _build_ui(self) -> None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(34, 28, 34, 28)
            layout.setSpacing(18)

            title = TitleLabel("UltraStar Import")
            subtitle = BodyLabel("Search USDB, download the UltraStar txt file, and optionally convert media.")
            layout.addWidget(title)
            layout.addWidget(subtitle)

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
            self.output_edit = LineEdit()
            self.output_edit.setPlaceholderText("Output folder")
            self.output_edit.setText(str(Path.cwd() / "demo_output"))

            output_row = QHBoxLayout()
            output_row.addWidget(self.output_edit, 1)
            browse_btn = PushButton(FIF.FOLDER, "Browse")
            browse_btn.clicked.connect(self._choose_output)
            output_row.addWidget(browse_btn)

            self.download_media = CheckBox("Download media")
            self.download_media.setChecked(True)
            self.convert_mp3 = CheckBox("Convert to MP3 audio only")
            self.convert_mp3.setChecked(False)
            self.use_cookies = CheckBox("Use browser cookies")
            self.use_cookies.setChecked(False)
            self.cookie_browser = ComboBox()
            self.cookie_browser.addItems(["chrome", "edge", "firefox"])
            self.respect_wait = CheckBox("Respect USDB wait")
            self.respect_wait.setChecked(True)

            option_row = QHBoxLayout()
            option_row.addWidget(self.download_media)
            option_row.addWidget(self.convert_mp3)
            option_row.addWidget(self.use_cookies)
            option_row.addWidget(self.cookie_browser)
            option_row.addWidget(self.respect_wait)
            option_row.addStretch(1)

            self.start_btn = PrimaryPushButton(FIF.PLAY, "Start import")
            self.start_btn.clicked.connect(self._emit_start)

            self.progress = ProgressBar()
            self.progress.setValue(0)
            self.progress_label = BodyLabel("Ready")

            card_layout.addWidget(SubtitleLabel("Song"))
            card_layout.addWidget(self.artist_edit)
            card_layout.addWidget(self.title_edit)
            card_layout.addWidget(SubtitleLabel("Destination"))
            card_layout.addLayout(output_row)
            card_layout.addLayout(option_row)
            card_layout.addWidget(self.progress_label)
            card_layout.addWidget(self.progress)
            card_layout.addWidget(self.start_btn)
            layout.addWidget(card)
            layout.addStretch(1)

        def _choose_output(self) -> None:
            folder = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_edit.text())
            if folder:
                self.output_edit.setText(folder)

        def _emit_start(self) -> None:
            media_format = "mp3" if self.convert_mp3.isChecked() else "mp4"
            self.startRequested.emit(
                {
                    "artist": self.artist_edit.text().strip(),
                    "title": self.title_edit.text().strip(),
                    "output": self.output_edit.text().strip(),
                    "format": media_format,
                    "skip_media": not self.download_media.isChecked(),
                    "cookie_browser": self.cookie_browser.currentText() if self.use_cookies.isChecked() else None,
                    "respect_wait": self.respect_wait.isChecked(),
                }
            )

        def set_running(self, running: bool) -> None:
            self.start_btn.setEnabled(not running)
            self.progress.setValue(35 if running else 0)
            self.progress_label.setText("Running..." if running else "Ready")

        def set_done(self) -> None:
            self.progress.setValue(100)
            self.progress_label.setText("Import complete")
            self.start_btn.setEnabled(True)

        def set_progress(self, value: int, message: str) -> None:
            self.progress.setValue(max(0, min(100, value)))
            self.progress_label.setText(message)


    class SettingsPage(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setObjectName("settingsPage")
            layout = QVBoxLayout(self)
            layout.setContentsMargins(34, 28, 34, 28)
            layout.setSpacing(18)

            layout.addWidget(TitleLabel("Settings"))
            layout.addWidget(BodyLabel("Save your USDB login once and reuse it on future launches."))

            card = CardWidget(self)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(22, 20, 22, 22)
            card_layout.setSpacing(12)

            self.user_edit = LineEdit()
            self.user_edit.setPlaceholderText("USDB_USER")
            stored = load_stored_credentials()
            self.user_edit.setText(os.getenv("USDB_USER", stored.username))
            self.pass_edit = PasswordLineEdit()
            self.pass_edit.setPlaceholderText("USDB_PASS")
            self.pass_edit.setText(os.getenv("USDB_PASS", stored.password))

            save_btn = PrimaryPushButton(FIF.SAVE, "Save credentials")
            save_btn.clicked.connect(self.save_credentials)

            card_layout.addWidget(SubtitleLabel("USDB account"))
            card_layout.addWidget(self.user_edit)
            card_layout.addWidget(self.pass_edit)
            card_layout.addWidget(save_btn)
            layout.addWidget(card)
            layout.addStretch(1)

        def save_credentials(self) -> None:
            username = self.user_edit.text().strip()
            password = self.pass_edit.text()
            os.environ["USDB_USER"] = username
            os.environ["USDB_PASS"] = password
            save_stored_credentials(username, password)
            InfoBar.success("Saved", "Credentials will be reused on future launches.", parent=self)


    class LogPage(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setObjectName("logPage")
            layout = QVBoxLayout(self)
            layout.setContentsMargins(34, 28, 34, 28)
            layout.setSpacing(14)
            layout.addWidget(TitleLabel("Activity"))
            self.text = TextEdit()
            self.text.setReadOnly(True)
            layout.addWidget(self.text, 1)

        def append(self, message: str) -> None:
            self.text.append(message)

        def clear(self) -> None:
            self.text.clear()


    class UltraStarFluentWindow(FluentWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("UltraStar Clone")
            self.resize(1060, 720)
            self.home = HomePage()
            self.settings = SettingsPage()
            self.logs = LogPage()

            self.addSubInterface(self.home, FIF.HOME, "Import")
            self.addSubInterface(self.logs, FIF.MESSAGE, "Logs")
            self.addSubInterface(self.settings, FIF.SETTING, "Settings")

            self.home.startRequested.connect(self.start_import)
            self.thread: QThread | None = None
            self.worker: ImportWorker | None = None

        def start_import(self, payload: dict) -> None:
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
                request = SongRequest(
                    payload["artist"],
                    payload["title"],
                    payload["format"],
                    target_root=Path(payload["output"]),
                )
            except Exception as exc:
                InfoBar.error("Invalid input", str(exc), position=InfoBarPosition.TOP_RIGHT, parent=self)
                return

            self.logs.append(f"[START] {request.artist} - {request.title}")
            self.home.set_running(True)
            self.thread = QThread(self)
            self.worker = ImportWorker(
                username,
                password,
                request,
                skip_media=payload["skip_media"],
                respect_wait=payload["respect_wait"],
                cookie_browser=payload["cookie_browser"],
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

        def on_progress(self, value: int, message: str) -> None:
            self.home.set_progress(value, message)
            self.logs.append(f"[PROGRESS] {value}% - {message}")

        def on_done(self, song_folder: str, txt_path: str, media_path: str) -> None:
            self.home.set_done()
            self.logs.append(f"[DONE] Song folder: {song_folder}")
            self.logs.append(f"[DONE] TXT file: {txt_path}")
            if media_path:
                self.logs.append(f"[DONE] Media file: {media_path}")
            InfoBar.success("Import complete", song_folder, position=InfoBarPosition.TOP_RIGHT, parent=self)

        def on_failed(self, message: str) -> None:
            self.home.set_running(False)
            self.home.set_progress(0, "Import failed")
            self.logs.append(f"[ERROR] {message}")
            InfoBar.error("Import failed", message, position=InfoBarPosition.TOP_RIGHT, parent=self)


def main() -> None:
    if missing_dependency_error is not None:
        raise GuiDependencyError(
            "Install PyQt6 and PyQt6-Fluent-Widgets to run the GUI."
        ) from missing_dependency_error

    import sys

    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)
    window = UltraStarFluentWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

