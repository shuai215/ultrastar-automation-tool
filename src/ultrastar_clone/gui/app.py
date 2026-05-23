"""QFluentWidgets desktop GUI for the importer.

导入器的 QFluentWidgets 桌面图形界面。
"""

from __future__ import annotations

import os
from math import isfinite
from pathlib import Path

from ultrastar_clone.core.converter import NoMediaConverter, YtDlpConverter
from ultrastar_clone.core.downloader import USDBTextDownloader
from ultrastar_clone.core.playback_timeline import build_timed_lyrics, lyrics_at_position
from ultrastar_clone.core.scraper import USDBScraper
from ultrastar_clone.core.song_parser import Song, parse_ultrastar_txt
from ultrastar_clone.models import SongRequest
from ultrastar_clone.services.controller import ImportController
from ultrastar_clone.services.library import scan_song_library
from ultrastar_clone.services.logger import build_logger
from ultrastar_clone.services.settings import (
    AppSettings,
    default_log_dir,
    load_stored_credentials,
    save_stored_credentials,
)


def format_media_time(milliseconds: int) -> str:
    total_seconds = max(0, milliseconds) // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def describe_lyric_sync_status(song: Song, timed_lyrics: tuple) -> tuple[str, str]:
    """Return status text and fallback current lyric text for parsed lyrics."""

    if timed_lyrics:
        return "Ready", ""
    if song.bpm is None or not isfinite(song.bpm) or song.bpm <= 0:
        return "Lyrics cannot sync because BPM is missing or invalid", "No synchronized lyrics"
    return "No synchronized lyrics found in TXT", "No synchronized lyrics"


try:
    from PyQt6.QtCore import QObject, Qt, QThread, QUrl, pyqtSignal
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    from PyQt6.QtWidgets import (
        QApplication,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QSlider,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
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
        txtProgress = pyqtSignal(int, str)
        mediaProgress = pyqtSignal(int, str)
        done = pyqtSignal(str, str, str)
        failed = pyqtSignal(str)

        def __init__(
            self,
            username: str | None,
            password: str | None,
            request: SongRequest,
            respect_wait: bool,
            cookie_browser: str | None,
        ) -> None:
            super().__init__()
            self.username = username
            self.password = password
            self.request = request
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
                        self._emit_txt_progress(value, message)

                scraper = USDBScraper(self.username, self.password) if self.username and self.password else None
                opener = scraper.opener if scraper is not None else None
                downloader = USDBTextDownloader(opener=opener, respect_wait=self.respect_wait)
                converter = (
                    NoMediaConverter()
                    if not self.request.download_audio and not self.request.download_video
                    else YtDlpConverter(
                        progress_callback=self._media_progress,
                        cookies_from_browser=self.cookie_browser,
                    )
                )
                controller = ImportController(settings, scraper, downloader, converter, logger=CombinedLogger())
                result = controller.import_song(self.request)
                txt_path = str(result.txt_path) if result.txt_path else ""
                media_paths = "; ".join(str(path) for path in result.media_paths)
                self.done.emit(str(result.song_folder), txt_path, media_paths)
            except Exception as exc:
                self.failed.emit(str(exc))

        def _media_progress(self, percent: int, message: str) -> None:
            scaled = 60 + int(percent * 0.25)
            self.progress.emit(min(scaled, 85), f"Media download {percent}%")
            self.mediaProgress.emit(percent, message)

        def _emit_txt_progress(self, value: int, message: str) -> None:
            if not self.request.download_lyrics:
                return
            if value < 45:
                self.txtProgress.emit(0, "TXT download 0%")
            elif value == 45:
                self.txtProgress.emit(20, message)
            elif value >= 60:
                self.txtProgress.emit(100, "TXT download complete")


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
            self.mode_combo = ComboBox()
            self.mode_combo.addItems(["Search USDB", "Direct YouTube URL"])
            self.mode_combo.currentTextChanged.connect(self._sync_input_mode)
            self.url_edit = LineEdit()
            self.url_edit.setPlaceholderText("YouTube URL")
            self.output_edit = LineEdit()
            self.output_edit.setPlaceholderText("Output folder")
            self.output_edit.setText(str(Path.cwd() / "demo_output"))

            output_row = QHBoxLayout()
            output_row.addWidget(self.output_edit, 1)
            browse_btn = PushButton(FIF.FOLDER, "Browse")
            browse_btn.clicked.connect(self._choose_output)
            output_row.addWidget(browse_btn)

            self.download_lyrics = CheckBox("Download lyrics TXT")
            self.download_lyrics.setChecked(True)
            self.download_audio = CheckBox("Download MP3 audio")
            self.download_audio.setChecked(False)
            self.download_video = CheckBox("Download video MP4")
            self.download_video.setChecked(True)
            self.use_cookies = CheckBox("Use browser cookies")
            self.use_cookies.setChecked(False)
            self.cookie_browser = ComboBox()
            self.cookie_browser.addItems(["chrome", "edge", "firefox"])
            self.respect_wait = CheckBox("Respect USDB wait")
            self.respect_wait.setChecked(True)

            option_row = QHBoxLayout()
            option_row.addWidget(self.download_lyrics)
            option_row.addWidget(self.download_audio)
            option_row.addWidget(self.download_video)
            option_row.addStretch(1)

            media_option_row = QHBoxLayout()
            media_option_row.addWidget(self.use_cookies)
            media_option_row.addWidget(self.cookie_browser)
            media_option_row.addWidget(self.respect_wait)
            media_option_row.addStretch(1)

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
            card_layout.addWidget(SubtitleLabel("Destination"))
            card_layout.addLayout(output_row)
            card_layout.addLayout(option_row)
            card_layout.addLayout(media_option_row)
            card_layout.addWidget(self.progress_label)
            card_layout.addWidget(self.progress)
            card_layout.addWidget(self.txt_progress_label)
            card_layout.addWidget(self.txt_progress)
            card_layout.addWidget(self.media_progress_label)
            card_layout.addWidget(self.media_progress)
            card_layout.addWidget(self.start_btn)
            layout.addWidget(card)
            layout.addStretch(1)
            self._sync_input_mode()

        def _choose_output(self) -> None:
            folder = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_edit.text())
            if folder:
                self.output_edit.setText(folder)

        def _sync_input_mode(self) -> None:
            direct_url = self.mode_combo.currentText() == "Direct YouTube URL"
            self.download_lyrics.setEnabled(not direct_url)
            if direct_url:
                self.download_lyrics.setChecked(False)

        def _emit_start(self) -> None:
            input_mode = "url" if self.mode_combo.currentText() == "Direct YouTube URL" else "search"
            media_format = "mp3" if self.download_audio.isChecked() and not self.download_video.isChecked() else "mp4"
            self.startRequested.emit(
                {
                    "input_mode": input_mode,
                    "artist": self.artist_edit.text().strip(),
                    "title": self.title_edit.text().strip(),
                    "youtube_url": self.url_edit.text().strip(),
                    "output": self.output_edit.text().strip(),
                    "format": media_format,
                    "download_lyrics": self.download_lyrics.isChecked(),
                    "download_audio": self.download_audio.isChecked(),
                    "download_video": self.download_video.isChecked(),
                    "cookie_browser": self.cookie_browser.currentText() if self.use_cookies.isChecked() else None,
                    "respect_wait": self.respect_wait.isChecked(),
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
            register_btn = PushButton(FIF.HOME, "Register USDB account")
            register_btn.clicked.connect(self.open_usdb_registration)

            card_layout.addWidget(SubtitleLabel("USDB account"))
            card_layout.addWidget(self.user_edit)
            card_layout.addWidget(self.pass_edit)
            card_layout.addWidget(save_btn)
            card_layout.addWidget(register_btn)
            layout.addWidget(card)
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
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.table, 1)

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


    class PlayerPage(QWidget):
        backRequested = pyqtSignal()
        playbackEnded = pyqtSignal()

        def __init__(self) -> None:
            super().__init__()
            self.setObjectName("playerPage")
            self.media_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.media_player.setAudioOutput(self.audio_output)
            self.timed_lyrics = ()
            self._slider_dragging = False
            self._build_ui()
            self.media_player.positionChanged.connect(self._on_position_changed)
            self.media_player.durationChanged.connect(self._on_duration_changed)
            self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
            self.media_player.errorOccurred.connect(self._on_error)

        def _build_ui(self) -> None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(34, 28, 34, 28)
            layout.setSpacing(14)

            self.title_label = TitleLabel("Player")
            self.status_label = QLabel("No song loaded")
            layout.addWidget(self.title_label)
            layout.addWidget(self.status_label)

            self.video_widget = QVideoWidget()
            self.media_player.setVideoOutput(self.video_widget)
            layout.addWidget(self.video_widget, 4)

            self.audio_fallback = QLabel("Audio playback")
            self.audio_fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.audio_fallback, 4)
            self.video_widget.hide()

            self.previous_label = QLabel("")
            self.current_label = QLabel("")
            self.next_label = QLabel("")
            self.previous_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.next_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.current_label.setStyleSheet("font-size: 24px; font-weight: 600;")
            layout.addWidget(self.previous_label)
            layout.addWidget(self.current_label)
            layout.addWidget(self.next_label)

            controls = QHBoxLayout()
            self.back_btn = PushButton("Back")
            self.back_btn.clicked.connect(self.backRequested.emit)
            self.play_pause_btn = PushButton("Pause")
            self.play_pause_btn.clicked.connect(self.toggle_playback)
            self.progress_slider = QSlider(Qt.Orientation.Horizontal)
            self.progress_slider.setRange(0, 0)
            self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
            self.progress_slider.sliderReleased.connect(self._on_slider_released)
            self.time_label = QLabel("00:00 / 00:00")
            controls.addWidget(self.back_btn)
            controls.addWidget(self.play_pause_btn)
            controls.addWidget(self.progress_slider, 1)
            controls.addWidget(self.time_label)
            layout.addLayout(controls)

        def load_entry(self, entry) -> None:
            self.stop()
            self.timed_lyrics = ()
            self.previous_label.clear()
            self.current_label.clear()
            self.next_label.clear()
            title = entry.display_title
            if entry.display_artist:
                title = f"{entry.display_artist} - {title}"
            self.title_label.setText(title)

            if entry.txt_path:
                try:
                    song = parse_ultrastar_txt(entry.txt_path)
                    self.timed_lyrics = build_timed_lyrics(song)
                except (OSError, UnicodeDecodeError, ValueError) as exc:
                    self.status_label.setText(f"Lyrics unavailable: {exc}")
                    self.current_label.setText("No synchronized lyrics")
                else:
                    lyric_status, current_text = describe_lyric_sync_status(song, self.timed_lyrics)
                    self.status_label.setText(lyric_status)
                    self.current_label.setText(current_text)
            else:
                self.status_label.setText("No TXT lyrics found")
                self.current_label.setText("No synchronized lyrics")

            media_path = entry.preferred_media_path
            if media_path is None:
                self.status_label.setText("No playable media found")
                return

            is_video = media_path.suffix.lower() == ".mp4"
            self.video_widget.setVisible(is_video)
            self.audio_fallback.setVisible(not is_video)
            self.media_player.setSource(QUrl.fromLocalFile(str(media_path)))
            self.media_player.play()
            self.play_pause_btn.setText("Pause")

        def stop(self) -> None:
            self.media_player.stop()

        def toggle_playback(self) -> None:
            if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.pause()
                self.play_pause_btn.setText("Play")
            else:
                self.media_player.play()
                self.play_pause_btn.setText("Pause")

        def _on_position_changed(self, position: int) -> None:
            if not self._slider_dragging:
                self.progress_slider.setValue(position)
            duration = self.media_player.duration()
            self.time_label.setText(f"{format_media_time(position)} / {format_media_time(duration)}")
            self._update_lyrics(position)

        def _on_duration_changed(self, duration: int) -> None:
            self.progress_slider.setRange(0, max(0, duration))
            position = self.media_player.position()
            self.time_label.setText(f"{format_media_time(position)} / {format_media_time(duration)}")

        def _on_media_status_changed(self, status) -> None:
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                self.stop()
                self.playbackEnded.emit()

        def _on_error(self, *_args) -> None:
            self.status_label.setText(self.media_player.errorString() or "Playback error")

        def _on_slider_pressed(self) -> None:
            self._slider_dragging = True

        def _on_slider_released(self) -> None:
            self._slider_dragging = False
            self.media_player.setPosition(self.progress_slider.value())

        def _update_lyrics(self, position: int) -> None:
            window = lyrics_at_position(self.timed_lyrics, position)
            self.previous_label.setText(window.previous.text if window.previous else "")
            self.current_label.setText(window.current.text if window.current else "")
            self.next_label.setText(window.next.text if window.next else "")


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
            self.library.playRequested.connect(self.open_player)
            self.player.backRequested.connect(self.return_to_library)
            self.player.playbackEnded.connect(self.return_to_library)
            self.thread: QThread | None = None
            self.worker: ImportWorker | None = None

        def open_player(self, entry) -> None:
            self.player.load_entry(entry)
            self.switchTo(self.player)

        def return_to_library(self) -> None:
            self.player.stop()
            self.switchTo(self.library)

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
                cookie_browser=payload["cookie_browser"],
            )
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.log.connect(self.logs.append)
            self.worker.progress.connect(self.on_progress)
            self.worker.txtProgress.connect(self.on_txt_progress)
            self.worker.mediaProgress.connect(self.on_media_progress)
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

        def on_txt_progress(self, value: int, message: str) -> None:
            self.home.set_txt_progress(value, message)
            self.logs.append(f"[TXT] {value}% - {message}")

        def on_media_progress(self, value: int, message: str) -> None:
            self.home.set_media_progress(value, message)
            self.logs.append(f"[MEDIA] {value}% - {message}")

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

