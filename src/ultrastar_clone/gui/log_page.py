"""Log page — displays import activity log.

日志页面 — 显示导入活动日志。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import TextEdit, TitleLabel


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
