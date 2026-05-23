"""GUI entry point and backward-compatible re-exports.

GUI 入口和向后兼容的重新导出。
"""

from __future__ import annotations

from ultrastar_clone.gui.utils import (
    describe_lyric_sync_status,
    entry_uses_video_output,
    format_media_time,
    lyric_display_payload,
    lyric_transition_required,
)


class GuiDependencyError(RuntimeError):
    pass


def main() -> None:
    """Launch the QFluentWidgets GUI."""
    try:
        from PyQt6.QtWidgets import QApplication
        from qfluentwidgets import setTheme
    except (ModuleNotFoundError, ImportError) as exc:
        raise GuiDependencyError(
            "Install PyQt6 and PyQt6-Fluent-Widgets to run the GUI."
        ) from exc

    import sys

    from ultrastar_clone.gui.main_window import UltraStarFluentWindow
    from ultrastar_clone.gui.settings_page import theme_from_key
    from ultrastar_clone.services.settings import load_stored_preferences

    app = QApplication(sys.argv)
    setTheme(theme_from_key(load_stored_preferences().theme))
    window = UltraStarFluentWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
