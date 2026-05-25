"""Reusable custom widgets for the GUI.

可复用的自定义 GUI 组件。
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QEvent,
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    QTimer,
    Qt,
    QVariantAnimation,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from ultrastar_clone.core.playback_timeline import lyric_target_index
from qfluentwidgets import ProgressBar as FluentProgressBar


class LyricDisplayWidget(QWidget):
    """Triggered smooth-scroll lyric strip.

    All lyrics are pre-rendered as a vertical strip. The current line
    stays centered and still. When playback crosses the next line's
    start time the strip animates to the new position in one motion.
    """

    _POLL_MS = 100
    _ANIM_DURATION = 300
    _VISIBLE_LINES = 3
    _ROW_HEIGHT = 34
    _LINE_SPACING = 0
    _CENTER_FONT = "font-size: 22px; font-weight: 600;"
    _EDGE_FONT = "font-size: 15px;"

    def __init__(self) -> None:
        super().__init__()
        self._labels: list[QLabel] = []
        self._line_height = self._ROW_HEIGHT
        self._target_index = 0
        self._tick_callback: object = None
        self._timed_lines: tuple = ()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self._viewport_height())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._viewport = QScrollArea()
        self._viewport.setFrameShape(QFrame.Shape.NoFrame)
        self._viewport.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._viewport.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._viewport.setWidgetResizable(False)
        self._viewport.setFixedHeight(self._viewport_height())
        self._viewport.setStyleSheet("background: transparent;")
        layout.addWidget(self._viewport)

        self._strip = QWidget()
        self._strip_layout = QVBoxLayout(self._strip)
        self._strip_layout.setContentsMargins(8, 0, 8, 0)
        self._strip_layout.setSpacing(self._LINE_SPACING)
        self._strip.setStyleSheet("background: transparent;")
        self._viewport.setWidget(self._strip)
        self._viewport.viewport().installEventFilter(self)

        self._placeholder = QLabel("", self._viewport)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("font-size: 24px; font-weight: 600;")
        self._placeholder.setVisible(False)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self._POLL_MS)
        self._poll_timer.timeout.connect(self._poll)

        self._scroll_anim = QPropertyAnimation(self._viewport.verticalScrollBar(), b"value", self)
        self._scroll_anim.setDuration(self._ANIM_DURATION)
        self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _viewport_height(self) -> int:
        return self._ROW_HEIGHT * self._VISIBLE_LINES

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_lines(self, texts: list[str]) -> None:
        """Rebuild the lyric strip with the given text lines."""
        self._poll_timer.stop()
        self._scroll_anim.stop()
        self._target_index = 0

        while self._strip_layout.count():
            item = self._strip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._labels.clear()

        self._placeholder.setVisible(not bool(texts))

        if not texts:
            self._line_height = self._ROW_HEIGHT
            self._position_strip()
            return

        for text in texts:
            label = QLabel(text or "")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            label.setFixedHeight(self._ROW_HEIGHT)
            label.setStyleSheet(self._EDGE_FONT)
            self._strip_layout.addWidget(label)
            self._labels.append(label)

        self._update_line_height()
        self._apply_line_styles(self._target_index)
        self._position_strip()

    def set_tick_callback(self, callback: object) -> None:
        """Set a callable that returns the current playback position in ms."""
        self._tick_callback = callback

    def start(self) -> None:
        self._poll_timer.start()

    def stop(self) -> None:
        self._poll_timer.stop()
        self._scroll_anim.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        if self._tick_callback is None or not self._labels:
            return
        position_ms = self._tick_callback()
        if position_ms is None or position_ms < 0:
            return

        new_idx = lyric_target_index(self._timed_lines, position_ms)
        if new_idx != self._target_index:
            self._target_index = new_idx
            self._animate_to_line(new_idx)

    def _animate_to_line(self, index: int) -> None:
        target_y = self._compute_strip_y(index)
        self._scroll_anim.stop()
        self._scroll_anim.setStartValue(self._viewport.verticalScrollBar().value())
        self._scroll_anim.setEndValue(target_y)
        self._scroll_anim.start()
        self._apply_line_styles(index)

    def _strip_total_height(self) -> int:
        """Total pixel height of the full lyric strip, computed from line count."""
        if not self._labels:
            return self._viewport_height()
        return len(self._labels) * self._line_height

    def _compute_strip_y(self, index: int) -> int:
        """Return the scrollbar value that centres *index* in the viewport."""
        if not self._labels:
            return 0
        viewport_h = self._viewport_height()
        total_h = self._strip_total_height()
        offset = (index - 1) * self._line_height
        max_offset = max(0, total_h - viewport_h)
        return max(0, min(offset, max_offset))

    def _apply_line_styles(self, center: int) -> None:
        """Style labels by discrete distance from the target index."""
        for i, label in enumerate(self._labels):
            dist = abs(i - center)
            if dist == 0:
                label.setStyleSheet(self._CENTER_FONT)
            elif dist == 1:
                color = QColor(self.palette().color(QPalette.ColorRole.WindowText))
                color.setAlpha(170)
                label.setStyleSheet(
                    f"{self._EDGE_FONT}; color: rgba("
                    f"{color.red()},{color.green()},{color.blue()},{color.alpha()});"
                )
            else:
                label.setStyleSheet(f"{self._EDGE_FONT}; color: rgba(128,128,128,100);")

    def _position_strip(self) -> None:
        """Snap strip to the current target index without animation."""
        if not self._labels:
            self._strip.resize(self._viewport.viewport().width(), self._viewport_height())
            self._viewport.verticalScrollBar().setValue(0)
            self._placeholder.resize(self._viewport.viewport().width(), self._viewport_height())
            self._placeholder.move(0, 0)
            return

        total_h = self._strip_total_height()
        viewport_w = self._viewport.viewport().width()
        self._strip.resize(viewport_w, max(total_h, self._viewport_height()))
        y = self._compute_strip_y(self._target_index)
        self._viewport.verticalScrollBar().setValue(y)

    def _update_line_height(self) -> None:
        self._line_height = self._ROW_HEIGHT
        self._viewport.setFixedHeight(self._viewport_height())
        self.setFixedHeight(self._viewport_height())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_line_height()
        self._position_strip()

    def eventFilter(self, watched, event) -> bool:
        if watched is self._viewport.viewport() and event.type() == QEvent.Type.Resize:
            self._position_strip()
        return super().eventFilter(watched, event)

    def set_timed_lines(self, lines: tuple) -> None:
        """Store timed lyrics for target-index lookups."""
        self._timed_lines = lines


class PreferredRowsTable(QTableWidget):
    def __init__(self, preferred_rows: int, rows: int, columns: int) -> None:
        super().__init__(rows, columns)
        self.preferred_rows = preferred_rows

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        row_height = self.verticalHeader().defaultSectionSize()
        header_height = self.horizontalHeader().height()
        preferred_height = header_height + row_height * self.preferred_rows + 8
        return QSize(hint.width(), max(hint.height(), preferred_height))


class AnimatedProgressBar(QWidget):
    """A progress bar that smoothly animates value changes."""

    def __init__(self) -> None:
        super().__init__()
        self._value = 0
        self._target = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.bar = FluentProgressBar()
        self.bar.setValue(0)
        layout.addWidget(self.bar)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_tick)

    def set_value_animated(self, target: int) -> None:
        target = max(0, min(100, target))
        self._target = target
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(target)
        self._anim.start()

    def set_value_instant(self, value: int) -> None:
        self._anim.stop()
        self._value = max(0, min(100, value))
        self._target = self._value
        self.bar.setValue(self._value)

    def _on_anim_tick(self, val) -> None:
        self._value = int(val)
        self.bar.setValue(self._value)


class AnimatedHeightWidget(QWidget):
    """A container that animates its height for expand/collapse transitions."""

    def __init__(self) -> None:
        super().__init__()
        self._target_height = 0
        self._anim = QPropertyAnimation(self, b"animHeight")
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(int)
    def animHeight(self):
        return self.height()

    @animHeight.setter
    def animHeight(self, value: int):
        self.setMaximumHeight(value)
        self.setMinimumHeight(0)

    def expand(self) -> None:
        self._anim.stop()
        self.show()
        hint = self.sizeHint().height()
        self._anim.setStartValue(0)
        self._anim.setEndValue(hint)
        self._anim.start()

    def collapse(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self.height())
        self._anim.setEndValue(0)
        self._anim.finished.connect(self.hide)
        self._anim.start()
