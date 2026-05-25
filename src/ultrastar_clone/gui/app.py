"""GUI entry point and backward-compatible re-exports.

GUI 入口和向后兼容的重新导出。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt as QtCore
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from ultrastar_clone.gui.utils import (
    entry_uses_video_output,
    format_media_time,
)


class GuiDependencyError(RuntimeError):
    pass


def _sync_native_palette(app: QApplication) -> None:
    scheme = app.styleHints().colorScheme()
    if scheme == QtCore.ColorScheme.Dark:
        dark = QPalette()
        dark.setColor(QPalette.ColorRole.Window, QColor(25, 25, 25))
        dark.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
        dark.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        dark.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
        dark.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
        dark.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        dark.setColor(QPalette.ColorRole.ButtonText, QColor(240, 240, 240))
        dark.setColor(QPalette.ColorRole.Mid, QColor(128, 128, 128))
        dark.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(dark)
    else:
        app.setPalette(QApplication.style().standardPalette())


def main() -> None:
    """Launch the QFluentWidgets GUI."""
    try:
        from qfluentwidgets import setTheme, Theme
    except (ModuleNotFoundError, ImportError) as exc:
        raise GuiDependencyError(
            "Install PyQt6 and PyQt6-Fluent-Widgets to run the GUI."
        ) from exc

    import sys

    from ultrastar_clone.gui.main_window import UltraStarFluentWindow

    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)
    _sync_native_palette(app)
    app.styleHints().colorSchemeChanged.connect(lambda: _sync_native_palette(app))
    window = UltraStarFluentWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
