"""Default application paths and settings.

默认应用路径与设置。
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    song_root: Path
    log_dir: Path


@dataclass(frozen=True)
class StoredCredentials:
    username: str = ""
    password: str = ""


@dataclass(frozen=True)
class StoredPreferences:
    theme: str = "auto"


def default_log_dir() -> Path:
    return Path.home() / ".ultrastar_clone"


def credentials_path() -> Path:
    return default_log_dir() / "credentials.json"


def preferences_path() -> Path:
    return default_log_dir() / "preferences.json"


def load_stored_credentials(path: Path | None = None) -> StoredCredentials:
    target = path or credentials_path()
    if not target.exists():
        return StoredCredentials()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return StoredCredentials()
    return StoredCredentials(
        username=str(data.get("username", "")),
        password=str(data.get("password", "")),
    )


def save_stored_credentials(username: str, password: str, path: Path | None = None) -> Path:
    target = path or credentials_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "username": username,
        "password": password,
    }
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return target


def load_stored_preferences(path: Path | None = None) -> StoredPreferences:
    target = path or preferences_path()
    if not target.exists():
        return StoredPreferences()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return StoredPreferences()
    theme = str(data.get("theme", "auto")).lower().strip()
    if theme not in {"auto", "light", "dark"}:
        theme = "auto"
    return StoredPreferences(theme=theme)


def save_stored_preferences(theme: str, path: Path | None = None) -> Path:
    target = path or preferences_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized_theme = theme.lower().strip()
    if normalized_theme not in {"auto", "light", "dark"}:
        normalized_theme = "auto"
    target.write_text(json.dumps({"theme": normalized_theme}, indent=2), encoding="utf-8")
    return target


def default_song_root() -> Path:
    system = platform.system().lower()
    home = Path.home()

    if system == "windows":
        return home / "AppData" / "Roaming" / "ultrastardx" / "songs"
    if system == "darwin":
        return home / "Library" / "Application Support" / "UltraStarDeluxe" / "songs"
    return home / ".ultrastardx" / "songs"


def load_default_settings() -> AppSettings:
    return AppSettings(song_root=default_song_root(), log_dir=default_log_dir())


