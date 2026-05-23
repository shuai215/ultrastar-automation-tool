"""Reusable custom widgets for the GUI.

可复用的自定义 GUI 组件。
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QSize,
    Qt,
    QVariantAnimation,
    pyqtProperty,
)
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QLabel, QProgressBar, QTableWidget, QVBoxLayout, QWidget
from qfluentwidgets import ProgressBar as FluentProgressBar

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

        self.previous_label.setStyleSheet("font-size: 14px;")
        self.previous_label.setForegroundRole(QPalette.ColorRole.Mid)
        self.current_label.setStyleSheet("font-size: 24px; font-weight: 600;")
        self.next_label.setStyleSheet("font-size: 14px;")
        self.next_label.setForegroundRole(QPalette.ColorRole.Mid)

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
