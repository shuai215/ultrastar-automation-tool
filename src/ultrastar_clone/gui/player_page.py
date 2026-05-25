"""Player page for song media and synchronized lyrics."""

from __future__ import annotations

from PyQt6.QtCore import QSize, QUrl, Qt, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PushButton, TitleLabel

from ultrastar_clone.core.playback_timeline import build_timed_lyrics
from ultrastar_clone.core.song_parser import parse_ultrastar_txt
from ultrastar_clone.gui.utils import (
    entry_uses_video_output,
    format_media_time,
)
from ultrastar_clone.gui.widgets import LyricDisplayWidget


class _PlayerContainer(QWidget):
    """16:9 video container with rounded corners and crop-to-fill."""

    def __init__(
        self,
        video_widget: QVideoWidget,
        audio_fallback: QLabel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._video = video_widget
        self._audio_fallback = audio_fallback

        inner = QVBoxLayout(self)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(video_widget)
        inner.addWidget(audio_fallback)

        video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(160)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.width() > 0:
            h = int(self.width() * 9 / 16)
            self.setMinimumHeight(h)
            self.setMaximumHeight(h)
        if not self._video.isHidden():
            self._video.resize(self.width(), self.height())


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
        layout.setContentsMargins(34, 20, 34, 20)
        layout.setSpacing(10)

        # Top bar: navigation
        top_bar = QHBoxLayout()
        self.back_btn = PushButton("Back")
        self.back_btn.clicked.connect(self.backRequested.emit)
        self.title_label = TitleLabel("Player")
        top_bar.addWidget(self.back_btn)
        top_bar.addWidget(self.title_label, 1)
        layout.addLayout(top_bar)

        # Video / audio area: 16:9 centered player with rounded corners
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        self.video_widget.hide()

        self.audio_fallback = QLabel("Audio playback")
        self.audio_fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_fallback.hide()

        self._player = _PlayerContainer(self.video_widget, self.audio_fallback, self)

        player_row = QHBoxLayout()
        player_row.addStretch(1)
        player_row.addWidget(self._player, 8)
        player_row.addStretch(1)
        layout.addLayout(player_row)

        # Lyrics: centered in the space below the video
        self.lyric_display = LyricDisplayWidget()
        layout.addWidget(self.lyric_display)

        # Status: error only
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Bottom bar: playback controls
        controls = QHBoxLayout()
        self.play_pause_btn = PushButton("Pause")
        self.play_pause_btn.clicked.connect(self.toggle_playback)
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.time_label = QLabel("00:00 / 00:00")
        controls.addWidget(self.play_pause_btn)
        controls.addWidget(self.progress_slider, 1)
        controls.addWidget(self.time_label)
        layout.addLayout(controls)

    def load_entry(self, entry) -> None:
        self.stop()
        self.timed_lyrics = ()
        self.lyric_display.stop()
        self.lyric_display.set_tick_callback(None)
        self.lyric_display.set_lines([])
        self.lyric_display.set_timed_lines(())
        self.status_label.setVisible(False)
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
                self.status_label.setVisible(True)
                self.lyric_display.set_lines(["No synchronized lyrics"])
            else:
                if self.timed_lyrics:
                    texts = [line.text for line in self.timed_lyrics]
                    self.lyric_display.set_timed_lines(self.timed_lyrics)
                    self.lyric_display.set_lines(texts)
                    self.lyric_display.set_tick_callback(self.media_player.position)
                else:
                    self.lyric_display.set_lines(["No synchronized lyrics"])
        else:
            self.status_label.setText("No TXT lyrics found")
            self.status_label.setVisible(True)
            self.lyric_display.set_lines(["No synchronized lyrics"])

        media_path = entry.preferred_media_path
        if media_path is None:
            self.status_label.setText("No playable media found")
            self.status_label.setVisible(True)
            return

        is_video = entry_uses_video_output(entry, media_path)
        self.video_widget.setVisible(is_video)
        self.audio_fallback.setVisible(not is_video)
        self.media_player.setSource(QUrl.fromLocalFile(str(media_path)))
        self.media_player.play()
        self.play_pause_btn.setText("Pause")
        self.lyric_display.start()

    def stop(self) -> None:
        self.media_player.stop()
        self.lyric_display.stop()

    def toggle_playback(self) -> None:
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.lyric_display.stop()
            self.play_pause_btn.setText("Play")
        else:
            self.media_player.play()
            self.lyric_display.start()
            self.play_pause_btn.setText("Pause")

    def _on_position_changed(self, position: int) -> None:
        if not self._slider_dragging:
            self.progress_slider.setValue(position)
        duration = self.media_player.duration()
        self.time_label.setText(f"{format_media_time(position)} / {format_media_time(duration)}")

    def _on_duration_changed(self, duration: int) -> None:
        self.progress_slider.setRange(0, max(0, duration))
        position = self.media_player.position()
        self.time_label.setText(f"{format_media_time(position)} / {format_media_time(duration)}")

    def _on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.lyric_display.stop()
            self.stop()
            self.playbackEnded.emit()

    def _on_error(self, *_args) -> None:
        self.status_label.setText(self.media_player.errorString() or "Playback error")
        self.status_label.setVisible(True)

    def _on_slider_pressed(self) -> None:
        self._slider_dragging = True

    def _on_slider_released(self) -> None:
        self._slider_dragging = False
        self.media_player.setPosition(self.progress_slider.value())
