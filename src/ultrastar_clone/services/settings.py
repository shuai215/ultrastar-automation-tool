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
    output_folder: str = ""
    download_lyrics: bool = True
    download_audio: bool = False
    download_video: bool = True
    respect_wait: bool = True


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
    return StoredPreferences(
        theme=theme,
        output_folder=str(data.get("output_folder", "")),
        download_lyrics=bool(data.get("download_lyrics", True)),
        download_audio=bool(data.get("download_audio", False)),
        download_video=bool(data.get("download_video", True)),
        respect_wait=bool(data.get("respect_wait", True)),
    )


def save_stored_preferences(
    theme: str,
    output_folder: str = "",
    download_lyrics: bool = True,
    download_audio: bool = False,
    download_video: bool = True,
    respect_wait: bool = True,
    path: Path | None = None,
) -> Path:
    target = path or preferences_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized_theme = theme.lower().strip()
    if normalized_theme not in {"auto", "light", "dark"}:
        normalized_theme = "auto"
    data = {
        "theme": normalized_theme,
        "output_folder": output_folder,
        "download_lyrics": download_lyrics,
        "download_audio": download_audio,
        "download_video": download_video,
        "respect_wait": respect_wait,
    }
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return target


def favorites_path() -> Path:
    return default_log_dir() / "favorites.json"


def load_favorites(path: Path | None = None) -> set[str]:
    target = path or favorites_path()
    if not target.exists():
        return set()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    folders = data.get("folders", [])
    if not isinstance(folders, list):
        return set()
    return {str(f) for f in folders}


def save_favorites(folders: set[str], path: Path | None = None) -> Path:
    target = path or favorites_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"folders": sorted(folders)}, indent=2),
        encoding="utf-8",
    )
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


