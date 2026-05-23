"""Reusable custom widgets for the GUI.

可复用的自定义 GUI 组件。
"""

from __future__ import annotations

from PyQt6.QtCore import QAbstractAnimation, QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt
from PyQt6.QtWidgets import QLabel, QTableWidget, QVBoxLayout, QWidget

from ultrastar_clone.gui.utils import lyric_transition_required


class LyricDisplayWidget(QWidget):
    """Three-line lyric display with a short scroll transition."""

    def __init__(self) -> None:
        super().__init__()
        self._current_text = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._viewport = QWidget()
        self._viewport.setMinimumHeight(104)
        layout.addWidget(self._viewport)

        self._line_group = QWidget(self._viewport)
        group_layout = QVBoxLayout(self._line_group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)

        self.previous_label = QLabel("")
        self.current_label = QLabel("")
        self.next_label = QLabel("")
        for label in (self.previous_label, self.current_label, self.next_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)

        self.previous_label.setStyleSheet("color: #8a8a8a; font-size: 14px;")
        self.current_label.setStyleSheet("font-size: 24px; font-weight: 600;")
        self.next_label.setStyleSheet("color: #8a8a8a; font-size: 14px;")

        group_layout.addWidget(self.previous_label)
        group_layout.addWidget(self.current_label)
        group_layout.addWidget(self.next_label)

        self._slide_animation = QPropertyAnimation(self._line_group, b"pos", self)
        self._slide_animation.setDuration(220)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def clear(self) -> None:
        self._stop_animation()
        self._current_text = ""
        self.previous_label.clear()
        self.current_label.clear()
        self.next_label.clear()
        self._position_line_group()

    def set_lyrics(self, previous: str, current: str, next_line: str) -> None:
        previous = previous or ""
        current = current or ""
        next_line = next_line or ""
        should_animate = lyric_transition_required(self._current_text, current)
        self._current_text = current

        self.previous_label.setText(previous)
        self.current_label.setText(current)
        self.next_label.setText(next_line)
        self._position_line_group()

        if should_animate:
            self._run_transition()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_line_group()

    def _run_transition(self) -> None:
        self._stop_animation()
        self._position_line_group()
        end_pos = self._line_group.pos()
        start_pos = end_pos + QPoint(0, 18)
        self._line_group.move(start_pos)

        self._slide_animation.setStartValue(start_pos)
        self._slide_animation.setEndValue(end_pos)
        self._slide_animation.start()

    def _stop_animation(self) -> None:
        if self._slide_animation.state() == QAbstractAnimation.State.Running:
            self._slide_animation.stop()

    def _position_line_group(self) -> None:
        width = max(1, self._viewport.width())
        self._line_group.resize(width, self._line_group.sizeHint().height())
        y = max(0, (self._viewport.height() - self._line_group.height()) // 2)
        self._line_group.move(0, y)


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
