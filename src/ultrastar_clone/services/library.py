"""Song library scanning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ultrastar_clone.core.song_parser import Song, parse_ultrastar_txt


@dataclass(frozen=True)
class SongLibraryEntry:
    """Files found for one downloaded song folder."""

    name: str
    folder: Path
    has_txt: bool
    has_mp3: bool
    has_mp4: bool
    title: str = ""
    artist: str = ""
    txt_path: Path | None = None
    audio_path: Path | None = None
    video_path: Path | None = None
    cover_path: Path | None = None
    parse_error: str | None = None

    @property
    def formats(self) -> str:
        formats = []
        if self.has_txt:
            formats.append("txt")
        if self.has_mp3:
            formats.append("mp3")
        if self.has_mp4:
            formats.append("mp4")
        return ", ".join(formats)

    @property
    def preferred_media_path(self) -> Path | None:
        return self.video_path or self.audio_path

    @property
    def is_playable(self) -> bool:
        return self.preferred_media_path is not None

    @property
    def display_title(self) -> str:
        return self.title or self.name

    @property
    def display_artist(self) -> str:
        return self.artist


def scan_song_library(root: Path) -> list[SongLibraryEntry]:
    """Scan one song root and summarize downloaded song folders."""

    if not root.exists() or not root.is_dir():
        return []

    entries: list[SongLibraryEntry] = []
    folders = []
    for item in root.iterdir():
        try:
            if item.is_dir():
                folders.append(item)
        except OSError:
            continue

    for folder in sorted(folders, key=lambda item: item.name.lower()):
        try:
            entry = _scan_song_folder(folder)
        except OSError:
            continue
        if entry is not None:
            entries.append(entry)
    return entries


def _scan_song_folder(folder: Path) -> SongLibraryEntry | None:
    txt_path = _first_file(folder, "*.txt")
    song, parse_error = _parse_song_metadata(txt_path)
    mp3_path = _first_file(folder, "*.mp3")
    mp4_path = _first_file(folder, "*.mp4")
    audio_path = _tagged_file(folder, song.audio_filename if song else "") or mp3_path
    video_path = _tagged_file(folder, song.video_filename if song else "") or mp4_path
    cover_path = _tagged_file(folder, song.cover_filename if song else "") or _first_file(
        folder,
        "*.jpg",
        "*.jpeg",
        "*.png",
    )
    has_txt = txt_path is not None
    has_mp3 = mp3_path is not None
    has_mp4 = mp4_path is not None
    if not has_txt and audio_path is None and video_path is None:
        return None

    return SongLibraryEntry(
        name=folder.name,
        folder=folder,
        has_txt=has_txt,
        has_mp3=has_mp3,
        has_mp4=has_mp4,
        title=song.title if song else "",
        artist=song.artist if song else "",
        txt_path=txt_path,
        audio_path=audio_path,
        video_path=video_path,
        cover_path=cover_path,
        parse_error=parse_error,
    )


def _parse_song_metadata(txt_path: Path | None) -> tuple[Song | None, str | None]:
    if txt_path is None:
        return None, None

    try:
        return parse_ultrastar_txt(txt_path), None
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return None, str(exc)


def _tagged_file(folder: Path, filename: str) -> Path | None:
    if not filename:
        return None

    tagged_path = Path(filename)
    if tagged_path.is_absolute():
        return None

    base = folder.resolve()
    target = (folder / tagged_path).resolve()
    if not target.is_relative_to(base):
        return None
    if not target.is_file():
        return None
    return target


def _first_file(folder: Path, *patterns: str) -> Path | None:
    for pattern in patterns:
        matches = sorted((path for path in folder.glob(pattern) if path.is_file()), key=lambda path: path.name.lower())
        if matches:
            return matches[0]
    return None
