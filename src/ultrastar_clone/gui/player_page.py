"""Player page — play song media with synchronized lyrics display.

播放器页面 — 播放歌曲媒体并同步显示歌词。
"""

from __future__ import annotations

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget
from qfluentwidgets import PushButton, TitleLabel

from ultrastar_clone.core.playback_timeline import build_timed_lyrics, lyrics_at_position
from ultrastar_clone.core.song_parser import parse_ultrastar_txt
from ultrastar_clone.gui.utils import (
    describe_lyric_sync_status,
    entry_uses_video_output,
    format_media_time,
    lyric_display_payload,
)
from ultrastar_clone.gui.widgets import LyricDisplayWidget


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

        self.lyric_display = LyricDisplayWidget()
        layout.addWidget(self.lyric_display)

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
        self.lyric_display.clear()
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
                self.lyric_display.set_lyrics("", "No synchronized lyrics", "")
            else:
                lyric_status, current_text = describe_lyric_sync_status(song, self.timed_lyrics)
                self.status_label.setText(lyric_status)
                self.lyric_display.set_lyrics("", current_text, "")
        else:
            self.status_label.setText("No TXT lyrics found")
            self.lyric_display.set_lyrics("", "No synchronized lyrics", "")

        media_path = entry.preferred_media_path
        if media_path is None:
            self.status_label.setText("No playable media found")
            return

        is_video = entry_uses_video_output(entry, media_path)
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
        previous, current, next_line = lyric_display_payload(window, position)
        self.lyric_display.set_lyrics(previous, current, next_line)
