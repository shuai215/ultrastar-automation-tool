"""Song library scanning helpers.

曲库扫描工具。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SongLibraryEntry:
    """Files found for one downloaded song folder.

    单个已下载歌曲文件夹中的文件信息。
    """

    name: str
    folder: Path
    has_txt: bool
    has_mp3: bool
    has_mp4: bool

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


def scan_song_library(root: Path) -> list[SongLibraryEntry]:
    """Scan one song root and summarize downloaded song folders.

    扫描歌曲根目录，并汇总每个已下载歌曲文件夹中的文件格式。
    """

    if not root.exists() or not root.is_dir():
        return []

    entries: list[SongLibraryEntry] = []
    for folder in sorted((item for item in root.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
        has_txt = any(folder.glob("*.txt"))
        has_mp3 = any(folder.glob("*.mp3"))
        has_mp4 = any(folder.glob("*.mp4"))
        if has_txt or has_mp3 or has_mp4:
            entries.append(
                SongLibraryEntry(
                    name=folder.name,
                    folder=folder,
                    has_txt=has_txt,
                    has_mp3=has_mp3,
                    has_mp4=has_mp4,
                )
            )
    return entries
