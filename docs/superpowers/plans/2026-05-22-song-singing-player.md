# Song Singing Player Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 PyQt6/QFluentWidgets 桌面应用的 Song Library 中加入本地歌曲播放和歌词同步跟唱能力。

**Architecture:** 核心解析和时间轴放在 `src/ultrastar_clone/core/`，曲库扫描继续放在 `src/ultrastar_clone/services/library.py`，GUI 只负责展示和连接 Qt Multimedia。播放入口从现有 `LibraryPage` 发出信号，主窗口切到新增 `PlayerPage`，媒体结束时自动返回曲库。

**Tech Stack:** Python 3.11+, `unittest`, PyQt6, PyQt6 Qt Multimedia, PyQt6-Fluent-Widgets。

---

## 文件结构

- Create: `src/ultrastar_clone/core/song_parser.py`
  - 负责 UltraStar TXT 标签、音符行、歌词分行解析。
  - 输出不可变 dataclass：`Note`、`LyricsLine`、`Song`.

- Create: `src/ultrastar_clone/core/playback_timeline.py`
  - 负责把 UltraStar note unit 转换为毫秒。
  - 输出 `TimedLyricsLine` 和 `LyricsWindow`。
  - 提供 `build_timed_lyrics(song)` 和 `lyrics_at_position(lines, position_ms)`。

- Modify: `src/ultrastar_clone/services/library.py`
  - 扩展 `SongLibraryEntry`，保留现有 `formats` 行为。
  - 增加标题、歌手、资源路径、首选媒体、是否可播放。
  - 首选媒体规则：`mp4` 优先，缺失时使用 `mp3`。

- Modify: `src/ultrastar_clone/gui/app.py`
  - 扩展 `LibraryPage`：显示标题、歌手、资源状态和 Play 按钮。
  - 新增 `PlayerPage`：视频/音频播放、歌词三行、进度条、返回、播放/暂停。
  - 主窗口连接 Library -> Player，播放结束自动回 Library。

- Create: `tests/test_song_parser.py`
  - 覆盖 TXT 标签、音符类型、分行、`#AUDIO`、默认 `#GAP`、坏行跳过。

- Create: `tests/test_playback_timeline.py`
  - 覆盖 `15000 / BPM` 换算、上一句/当前句/下一句窗口、空歌词。

- Modify: `tests/test_library.py`
  - 保留现有测试。
  - 增加元数据、首选媒体、可播放状态测试。

---

## Task 1: UltraStar TXT 解析器

**Files:**
- Create: `src/ultrastar_clone/core/song_parser.py`
- Create: `tests/test_song_parser.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_song_parser.py`:

```python
"""Tests for UltraStar TXT parsing."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.core.song_parser import parse_ultrastar_txt


class SongParserTests(unittest.TestCase):
    def test_parse_tags_notes_and_lines(self) -> None:
        with TemporaryDirectory() as temp_dir:
            txt = Path(temp_dir) / "song.txt"
            txt.write_text(
                "\n".join(
                    [
                        "#TITLE:Yellow",
                        "#ARTIST:Coldplay",
                        "#MP3:yellow.mp3",
                        "#VIDEO:yellow.mp4",
                        "#COVER:cover.jpg",
                        "#BPM:276",
                        "#GAP:35780",
                        ": 0 4 1 Look ",
                        "* 7 3 3 at ",
                        "F 11 3 1 the ",
                        "- 16",
                        ": 20 5 4 stars",
                        "E",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            song = parse_ultrastar_txt(txt)

        self.assertEqual(song.title, "Yellow")
        self.assertEqual(song.artist, "Coldplay")
        self.assertEqual(song.audio_filename, "yellow.mp3")
        self.assertEqual(song.video_filename, "yellow.mp4")
        self.assertEqual(song.cover_filename, "cover.jpg")
        self.assertEqual(song.bpm, 276.0)
        self.assertEqual(song.gap_ms, 35780)
        self.assertEqual(len(song.lyrics), 2)
        self.assertEqual(song.lyrics[0].text, "Look at the")
        self.assertEqual([note.type for note in song.lyrics[0].notes], [":", "*", "F"])
        self.assertEqual(song.lyrics[0].start_beat, 0)
        self.assertEqual(song.lyrics[0].end_beat, 14)

    def test_audio_tag_is_audio_alias_and_missing_gap_defaults_to_zero(self) -> None:
        with TemporaryDirectory() as temp_dir:
            txt = Path(temp_dir) / "song.txt"
            txt.write_text(
                "#TITLE:Song\n#ARTIST:Artist\n#AUDIO:file.ogg\n#BPM:120\n: 0 2 1 Hi\nE\n",
                encoding="utf-8",
            )

            song = parse_ultrastar_txt(txt)

        self.assertEqual(song.audio_filename, "file.ogg")
        self.assertEqual(song.gap_ms, 0)
        self.assertEqual(song.lyrics[0].text, "Hi")

    def test_malformed_note_rows_are_skipped(self) -> None:
        with TemporaryDirectory() as temp_dir:
            txt = Path(temp_dir) / "song.txt"
            txt.write_text(
                "#TITLE:Song\n#ARTIST:Artist\n#BPM:100\n: bad row\n: 4 2 1 ok\nE\n",
                encoding="utf-8",
            )

            song = parse_ultrastar_txt(txt)

        self.assertEqual(len(song.lyrics), 1)
        self.assertEqual(song.lyrics[0].text, "ok")
        self.assertEqual(song.lyrics[0].notes[0].start_beat, 4)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败原因正确**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_song_parser -v
```

Expected:

```text
ModuleNotFoundError: No module named 'ultrastar_clone.core.song_parser'
```

- [ ] **Step 3: 实现最小解析器**

Create `src/ultrastar_clone/core/song_parser.py`:

```python
"""UltraStar TXT parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Note:
    start_beat: int
    duration: int
    pitch: int
    syllable: str
    type: str = ":"


@dataclass(frozen=True)
class LyricsLine:
    start_beat: int
    end_beat: int
    text: str
    notes: tuple[Note, ...]


@dataclass(frozen=True)
class Song:
    title: str
    artist: str
    folder_path: Path
    txt_path: Path
    audio_filename: str | None
    video_filename: str | None
    cover_filename: str | None
    bpm: float | None
    gap_ms: int
    lyrics: tuple[LyricsLine, ...]


def parse_ultrastar_txt(txt_path: Path) -> Song:
    path = Path(txt_path)
    tags: dict[str, str] = {}
    lines: list[LyricsLine] = []
    current_notes: list[Note] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#") and ":" in line:
            key, value = line[1:].split(":", 1)
            tags[key.upper().strip()] = value.strip()
            continue
        marker = line[0]
        if marker in {":", "*", "F"}:
            note = _parse_note_line(raw_line, marker)
            if note is not None:
                current_notes.append(note)
            continue
        if marker == "-":
            _append_line(lines, current_notes)
            current_notes = []
            continue
        if marker == "E":
            _append_line(lines, current_notes)
            break

    if current_notes:
        _append_line(lines, current_notes)

    return Song(
        title=tags.get("TITLE", path.stem),
        artist=tags.get("ARTIST", ""),
        folder_path=path.parent,
        txt_path=path,
        audio_filename=tags.get("MP3") or tags.get("AUDIO"),
        video_filename=tags.get("VIDEO"),
        cover_filename=tags.get("COVER"),
        bpm=_parse_float(tags.get("BPM")),
        gap_ms=_parse_gap(tags.get("GAP")),
        lyrics=tuple(lines),
    )


def _parse_note_line(raw_line: str, marker: str) -> Note | None:
    try:
        _, start, duration, pitch, syllable = raw_line.split(maxsplit=4)
        return Note(
            start_beat=int(start),
            duration=int(duration),
            pitch=int(pitch),
            syllable=syllable,
            type=marker,
        )
    except (ValueError, TypeError):
        return None


def _append_line(lines: list[LyricsLine], notes: list[Note]) -> None:
    if not notes:
        return
    start = min(note.start_beat for note in notes)
    end = max(note.start_beat + note.duration for note in notes)
    text = "".join(note.syllable for note in notes).strip()
    lines.append(LyricsLine(start_beat=start, end_beat=end, text=text, notes=tuple(notes)))


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_gap(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0
```

- [ ] **Step 4: 运行测试，确认通过**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_song_parser -v
```

Expected:

```text
OK
```

- [ ] **Step 5: 提交**

```powershell
git add src/ultrastar_clone/core/song_parser.py tests/test_song_parser.py
git commit -m "Add UltraStar song parser"
```

---

## Task 2: 播放歌词时间轴

**Files:**
- Create: `src/ultrastar_clone/core/playback_timeline.py`
- Create: `tests/test_playback_timeline.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_playback_timeline.py`:

```python
"""Tests for lyric playback timing."""

from __future__ import annotations

import unittest
from pathlib import Path

from ultrastar_clone.core.playback_timeline import build_timed_lyrics, lyrics_at_position
from ultrastar_clone.core.song_parser import LyricsLine, Note, Song


class PlaybackTimelineTests(unittest.TestCase):
    def test_build_timed_lyrics_uses_ultrastar_note_units(self) -> None:
        song = Song(
            title="Song",
            artist="Artist",
            folder_path=Path("songs/Song"),
            txt_path=Path("songs/Song/song.txt"),
            audio_filename=None,
            video_filename=None,
            cover_filename=None,
            bpm=150.0,
            gap_ms=1000,
            lyrics=(
                LyricsLine(
                    start_beat=0,
                    end_beat=4,
                    text="Hello",
                    notes=(Note(0, 4, 1, "Hello"),),
                ),
                LyricsLine(
                    start_beat=8,
                    end_beat=12,
                    text="World",
                    notes=(Note(8, 4, 1, "World"),),
                ),
            ),
        )

        lines = build_timed_lyrics(song)

        self.assertEqual(lines[0].start_time_ms, 1000)
        self.assertEqual(lines[0].end_time_ms, 1400)
        self.assertEqual(lines[1].start_time_ms, 1800)
        self.assertEqual(lines[1].end_time_ms, 2200)

    def test_lyrics_at_position_returns_previous_current_and_next(self) -> None:
        song = Song(
            title="Song",
            artist="Artist",
            folder_path=Path("songs/Song"),
            txt_path=Path("songs/Song/song.txt"),
            audio_filename=None,
            video_filename=None,
            cover_filename=None,
            bpm=150.0,
            gap_ms=1000,
            lyrics=(
                LyricsLine(0, 4, "Hello", (Note(0, 4, 1, "Hello"),)),
                LyricsLine(8, 12, "World", (Note(8, 4, 1, "World"),)),
            ),
        )
        lines = build_timed_lyrics(song)

        before = lyrics_at_position(lines, 900)
        current = lyrics_at_position(lines, 1100)
        between = lyrics_at_position(lines, 1600)
        after = lyrics_at_position(lines, 2300)

        self.assertIsNone(before.previous)
        self.assertIsNone(before.current)
        self.assertEqual(before.next.text, "Hello")
        self.assertEqual(current.current.text, "Hello")
        self.assertEqual(current.next.text, "World")
        self.assertEqual(between.previous.text, "Hello")
        self.assertIsNone(between.current)
        self.assertEqual(between.next.text, "World")
        self.assertEqual(after.previous.text, "World")
        self.assertIsNone(after.current)
        self.assertIsNone(after.next)

    def test_missing_bpm_or_empty_lyrics_returns_empty_timeline(self) -> None:
        song = Song(
            title="Song",
            artist="Artist",
            folder_path=Path("songs/Song"),
            txt_path=Path("songs/Song/song.txt"),
            audio_filename=None,
            video_filename=None,
            cover_filename=None,
            bpm=None,
            gap_ms=0,
            lyrics=(),
        )

        self.assertEqual(build_timed_lyrics(song), ())
        self.assertIsNone(lyrics_at_position((), 1000).current)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败原因正确**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_playback_timeline -v
```

Expected:

```text
ModuleNotFoundError: No module named 'ultrastar_clone.core.playback_timeline'
```

- [ ] **Step 3: 实现时间轴**

Create `src/ultrastar_clone/core/playback_timeline.py`:

```python
"""Playback timeline helpers for UltraStar lyrics."""

from __future__ import annotations

from dataclasses import dataclass

from ultrastar_clone.core.song_parser import LyricsLine, Song


@dataclass(frozen=True)
class TimedLyricsLine:
    start_time_ms: int
    end_time_ms: int
    text: str
    source: LyricsLine


@dataclass(frozen=True)
class LyricsWindow:
    previous: TimedLyricsLine | None
    current: TimedLyricsLine | None
    next: TimedLyricsLine | None


def build_timed_lyrics(song: Song) -> tuple[TimedLyricsLine, ...]:
    if not song.bpm or song.bpm <= 0:
        return ()

    unit_duration_ms = 15000.0 / song.bpm
    timed: list[TimedLyricsLine] = []
    for line in song.lyrics:
        start = round(song.gap_ms + line.start_beat * unit_duration_ms)
        end = round(song.gap_ms + line.end_beat * unit_duration_ms)
        if end <= start:
            end = start + 1
        timed.append(
            TimedLyricsLine(
                start_time_ms=start,
                end_time_ms=end,
                text=line.text,
                source=line,
            )
        )
    return tuple(sorted(timed, key=lambda item: item.start_time_ms))


def lyrics_at_position(lines: tuple[TimedLyricsLine, ...], position_ms: int) -> LyricsWindow:
    previous: TimedLyricsLine | None = None
    current: TimedLyricsLine | None = None
    next_line: TimedLyricsLine | None = None

    for line in lines:
        if line.end_time_ms <= position_ms:
            previous = line
            continue
        if line.start_time_ms <= position_ms < line.end_time_ms:
            current = line
            continue
        if line.start_time_ms > position_ms:
            next_line = line
            break

    return LyricsWindow(previous=previous, current=current, next=next_line)
```

- [ ] **Step 4: 运行测试，确认通过**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_playback_timeline -v
```

Expected:

```text
OK
```

- [ ] **Step 5: 提交**

```powershell
git add src/ultrastar_clone/core/playback_timeline.py tests/test_playback_timeline.py
git commit -m "Add lyric playback timeline"
```

---

## Task 3: 扩展曲库扫描

**Files:**
- Modify: `src/ultrastar_clone/services/library.py`
- Modify: `tests/test_library.py`

- [ ] **Step 1: 写失败测试**

Replace `tests/test_library.py` with:

```python
"""Tests for song library scanning."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.services.library import scan_song_library


class LibraryTests(unittest.TestCase):
    def test_scan_song_library_reports_available_formats(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            yellow = root / "Coldplay - Yellow"
            yellow.mkdir()
            (yellow / "Coldplay - Yellow.txt").write_text("#TITLE:Yellow\n#ARTIST:Coldplay\n", encoding="utf-8")
            (yellow / "Coldplay - Yellow.mp4").write_bytes(b"video")
            audio = root / "Artist - Audio"
            audio.mkdir()
            (audio / "Artist - Audio.mp3").write_bytes(b"audio")
            (root / "Empty").mkdir()

            entries = scan_song_library(root)

        self.assertEqual([entry.name for entry in entries], ["Artist - Audio", "Coldplay - Yellow"])
        self.assertEqual(entries[0].formats, "mp3")
        self.assertEqual(entries[1].formats, "txt, mp4")

    def test_scan_song_library_uses_txt_metadata_and_prefers_video(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "folder-name"
            folder.mkdir()
            (folder / "song.txt").write_text(
                "#TITLE:Real Title\n#ARTIST:Real Artist\n#MP3:audio.mp3\n#VIDEO:video.mp4\n#BPM:120\n",
                encoding="utf-8",
            )
            (folder / "audio.mp3").write_bytes(b"audio")
            (folder / "video.mp4").write_bytes(b"video")

            entry = scan_song_library(root)[0]

        self.assertEqual(entry.title, "Real Title")
        self.assertEqual(entry.artist, "Real Artist")
        self.assertTrue(entry.is_playable)
        self.assertEqual(entry.preferred_media_path.name, "video.mp4")
        self.assertEqual(entry.txt_path.name, "song.txt")
        self.assertEqual(entry.audio_path.name, "audio.mp3")
        self.assertEqual(entry.video_path.name, "video.mp4")

    def test_scan_song_library_allows_media_without_txt_and_disables_txt_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            media_only = root / "Media Only"
            media_only.mkdir()
            (media_only / "song.mp3").write_bytes(b"audio")
            txt_only = root / "Txt Only"
            txt_only.mkdir()
            (txt_only / "song.txt").write_text("#TITLE:Only Text\n", encoding="utf-8")

            entries = scan_song_library(root)

        self.assertEqual([entry.name for entry in entries], ["Media Only", "Txt Only"])
        self.assertTrue(entries[0].is_playable)
        self.assertFalse(entries[1].is_playable)
        self.assertIsNone(entries[1].preferred_media_path)

    def test_scan_missing_song_library_returns_empty_list(self) -> None:
        with TemporaryDirectory() as temp_dir:
            entries = scan_song_library(Path(temp_dir) / "missing")

        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败原因正确**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_library -v
```

Expected:

```text
AttributeError: 'SongLibraryEntry' object has no attribute 'title'
```

- [ ] **Step 3: 扩展扫描实现**

Replace `src/ultrastar_clone/services/library.py` with:

```python
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
    preferred_media_path: Path | None = None
    parse_error: str = ""

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
    def is_playable(self) -> bool:
        return self.preferred_media_path is not None

    @property
    def display_title(self) -> str:
        return self.title or self.name

    @property
    def display_artist(self) -> str:
        return self.artist or ""


def scan_song_library(root: Path) -> list[SongLibraryEntry]:
    """Scan one song root and summarize downloaded song folders."""

    if not root.exists() or not root.is_dir():
        return []

    entries: list[SongLibraryEntry] = []
    for folder in sorted((item for item in root.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
        entry = _scan_song_folder(folder)
        if entry.has_txt or entry.has_mp3 or entry.has_mp4:
            entries.append(entry)
    return entries


def _scan_song_folder(folder: Path) -> SongLibraryEntry:
    txt_path = _first_file(folder, ("*.txt",))
    parsed_song: Song | None = None
    parse_error = ""
    if txt_path is not None:
        try:
            parsed_song = parse_ultrastar_txt(txt_path)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            parse_error = str(exc)

    audio_path = _resolve_media(folder, parsed_song.audio_filename if parsed_song else None, ("*.mp3", "*.ogg", "*.wav"))
    video_path = _resolve_media(folder, parsed_song.video_filename if parsed_song else None, ("*.mp4", "*.mkv", "*.avi", "*.mov"))
    cover_path = _resolve_media(folder, parsed_song.cover_filename if parsed_song else None, ("*.jpg", "*.jpeg", "*.png"))
    preferred = video_path or audio_path

    return SongLibraryEntry(
        name=folder.name,
        folder=folder,
        has_txt=txt_path is not None,
        has_mp3=audio_path is not None and audio_path.suffix.lower() == ".mp3",
        has_mp4=video_path is not None and video_path.suffix.lower() == ".mp4",
        title=parsed_song.title if parsed_song else folder.name,
        artist=parsed_song.artist if parsed_song else "",
        txt_path=txt_path,
        audio_path=audio_path,
        video_path=video_path,
        cover_path=cover_path,
        preferred_media_path=preferred,
        parse_error=parse_error,
    )


def _resolve_media(folder: Path, tagged_filename: str | None, patterns: tuple[str, ...]) -> Path | None:
    if tagged_filename:
        tagged_path = folder / tagged_filename
        if tagged_path.is_file():
            return tagged_path
    return _first_file(folder, patterns)


def _first_file(folder: Path, patterns: tuple[str, ...]) -> Path | None:
    for pattern in patterns:
        matches = sorted(folder.glob(pattern), key=lambda item: item.name.lower())
        if matches:
            return matches[0]
    return None
```

- [ ] **Step 4: 运行曲库测试，确认通过**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_library -v
```

Expected:

```text
OK
```

- [ ] **Step 5: 运行解析器和时间轴测试，确认没有回归**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_song_parser tests.test_playback_timeline tests.test_library -v
```

Expected:

```text
OK
```

- [ ] **Step 6: 提交**

```powershell
git add src/ultrastar_clone/services/library.py tests/test_library.py
git commit -m "Extend song library scanning for playback"
```

---

## Task 4: Library 播放入口和 Player 页面

**Files:**
- Modify: `src/ultrastar_clone/gui/app.py`
- Modify: `tests/test_gui_import.py`

- [ ] **Step 1: 写失败测试**

Replace `tests/test_gui_import.py` with:

```python
"""Tests for safe GUI module import."""

import unittest


class GuiImportTests(unittest.TestCase):
    def test_gui_module_imports(self) -> None:
        from ultrastar_clone.gui.app import GuiDependencyError, main

        self.assertTrue(callable(main))
        self.assertTrue(GuiDependencyError)

    def test_media_time_formatting(self) -> None:
        from ultrastar_clone.gui.app import format_media_time

        self.assertEqual(format_media_time(0), "00:00")
        self.assertEqual(format_media_time(65_000), "01:05")
        self.assertEqual(format_media_time(3_665_000), "61:05")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败原因正确**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_gui_import -v
```

Expected:

```text
ImportError: cannot import name 'format_media_time'
```

- [ ] **Step 3: 添加 GUI 顶层 helper 和 Qt Multimedia imports**

Modify `src/ultrastar_clone/gui/app.py`.

Add imports near the top:

```python
from ultrastar_clone.core.playback_timeline import (
    TimedLyricsLine,
    build_timed_lyrics,
    lyrics_at_position,
)
from ultrastar_clone.core.song_parser import Song, parse_ultrastar_txt
```

Add this function above the `try:` block so it is importable even without GUI dependencies:

```python
def format_media_time(milliseconds: int) -> str:
    seconds = max(0, int(milliseconds // 1000))
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"
```

Update Qt imports inside the `try:` block:

```python
from PyQt6.QtCore import QObject, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
```

- [ ] **Step 4: 运行 GUI import 测试，确认 helper 通过**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_gui_import -v
```

Expected:

```text
OK
```

- [ ] **Step 5: 扩展 LibraryPage**

In `src/ultrastar_clone/gui/app.py`, update `LibraryPage`:

```python
class LibraryPage(QWidget):
    playRequested = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("libraryPage")
        self.root = Path.cwd() / "demo_output"
        self.entries = []
        self._build_ui()
        self.refresh()
```

Replace table creation in `_build_ui`:

```python
self.table = QTableWidget(0, 7)
self.table.setHorizontalHeaderLabels(["Title", "Artist", "TXT", "MP3", "MP4", "Folder", "Play"])
self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
layout.addWidget(self.table, 1)
```

Replace `refresh`:

```python
def refresh(self) -> None:
    self.root = Path(self.root_edit.text().strip() or Path.cwd() / "demo_output")
    self.entries = scan_song_library(self.root)
    self.table.setRowCount(len(self.entries))
    for row, entry in enumerate(self.entries):
        self.table.setItem(row, 0, QTableWidgetItem(entry.display_title))
        self.table.setItem(row, 1, QTableWidgetItem(entry.display_artist))
        self.table.setItem(row, 2, QTableWidgetItem("yes" if entry.has_txt else ""))
        self.table.setItem(row, 3, QTableWidgetItem("yes" if entry.has_mp3 else ""))
        self.table.setItem(row, 4, QTableWidgetItem("yes" if entry.has_mp4 else ""))
        self.table.setItem(row, 5, QTableWidgetItem(str(entry.folder)))
        play_btn = PushButton(FIF.PLAY, "Play")
        play_btn.setEnabled(entry.is_playable)
        play_btn.clicked.connect(lambda checked=False, selected=entry: self.playRequested.emit(selected))
        self.table.setCellWidget(row, 6, play_btn)
    self.summary_label.setText(f"{len(self.entries)} songs")
```

- [ ] **Step 6: 添加 PlayerPage**

Add `PlayerPage` after `LibraryPage` in `src/ultrastar_clone/gui/app.py`:

```python
class PlayerPage(QWidget):
    backRequested = pyqtSignal()
    playbackEnded = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("playerPage")
        self.entry = None
        self.song: Song | None = None
        self.timed_lyrics: tuple[TimedLyricsLine, ...] = ()
        self._seeking = False
        self._build_ui()
        self._build_player()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(14)

        self.title_label = TitleLabel("Player")
        self.artist_label = BodyLabel("")
        layout.addWidget(self.title_label)
        layout.addWidget(self.artist_label)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(320)
        layout.addWidget(self.video_widget, 1)

        self.audio_fallback = QLabel("Audio playback")
        self.audio_fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_fallback.setMinimumHeight(180)
        self.audio_fallback.hide()
        layout.addWidget(self.audio_fallback)

        self.previous_label = BodyLabel("")
        self.current_label = SubtitleLabel("")
        self.next_label = BodyLabel("")
        layout.addWidget(self.previous_label)
        layout.addWidget(self.current_label)
        layout.addWidget(self.next_label)

        control_row = QHBoxLayout()
        self.back_btn = PushButton(FIF.RETURN, "Back")
        self.back_btn.clicked.connect(self._emit_back)
        self.play_btn = PrimaryPushButton(FIF.PLAY, "Pause")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.sliderMoved.connect(self.seek)
        self.time_label = BodyLabel("00:00 / 00:00")
        control_row.addWidget(self.back_btn)
        control_row.addWidget(self.play_btn)
        control_row.addWidget(self.position_slider, 1)
        control_row.addWidget(self.time_label)
        layout.addLayout(control_row)

        self.status_label = BodyLabel("")
        layout.addWidget(self.status_label)

    def _build_player(self) -> None:
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_error)

    def load_entry(self, entry) -> None:
        self.stop()
        self.entry = entry
        self.song = None
        self.timed_lyrics = ()
        self.title_label.setText(entry.display_title)
        self.artist_label.setText(entry.display_artist)
        self.status_label.setText("")
        self.previous_label.setText("")
        self.current_label.setText("No synchronized lyrics")
        self.next_label.setText("")

        if entry.txt_path:
            try:
                self.song = parse_ultrastar_txt(entry.txt_path)
                self.timed_lyrics = build_timed_lyrics(self.song)
                if self.timed_lyrics:
                    self.current_label.setText("Ready")
                else:
                    self.current_label.setText("Lyrics are unavailable for synchronization")
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                self.status_label.setText(f"Lyric parse failed: {exc}")

        media_path = entry.preferred_media_path
        if media_path is None:
            self.status_label.setText("No playable media file")
            return

        is_video = media_path.suffix.lower() == ".mp4"
        self.video_widget.setVisible(is_video)
        self.audio_fallback.setVisible(not is_video)
        self.audio_fallback.setText(f"{entry.display_title}\n{entry.display_artist}".strip())
        self.player.setSource(QUrl.fromLocalFile(str(media_path)))
        self.player.play()
        self.play_btn.setText("Pause")

    def toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("Play")
        else:
            self.player.play()
            self.play_btn.setText("Pause")

    def seek(self, position: int) -> None:
        self._seeking = True
        self.player.setPosition(position)
        self._seeking = False

    def stop(self) -> None:
        if hasattr(self, "player"):
            self.player.stop()
            self.player.setSource(QUrl())
        self.position_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")

    def _emit_back(self) -> None:
        self.stop()
        self.backRequested.emit()

    def _on_position_changed(self, position: int) -> None:
        if not self._seeking:
            self.position_slider.setValue(position)
        duration = self.player.duration()
        self.time_label.setText(f"{format_media_time(position)} / {format_media_time(duration)}")
        window = lyrics_at_position(self.timed_lyrics, position)
        self.previous_label.setText(window.previous.text if window.previous else "")
        self.current_label.setText(window.current.text if window.current else "")
        self.next_label.setText(window.next.text if window.next else "")

    def _on_duration_changed(self, duration: int) -> None:
        self.position_slider.setRange(0, max(0, duration))
        self.time_label.setText(f"{format_media_time(self.player.position())} / {format_media_time(duration)}")

    def _on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.stop()
            self.playbackEnded.emit()

    def _on_error(self, error, message: str) -> None:
        if message:
            self.status_label.setText(message)
```

- [ ] **Step 7: 连接主窗口导航**

In `UltraStarFluentWindow.__init__`, add `PlayerPage`:

```python
self.player = PlayerPage()
```

Add it after Library:

```python
self.addSubInterface(self.library, FIF.FOLDER, "Library")
self.addSubInterface(self.player, FIF.PLAY, "Player")
self.addSubInterface(self.logs, FIF.MESSAGE, "Logs")
```

Connect signals:

```python
self.library.playRequested.connect(self.open_player)
self.player.backRequested.connect(self.return_to_library)
self.player.playbackEnded.connect(self.return_to_library)
```

Add methods to `UltraStarFluentWindow`:

```python
def open_player(self, entry) -> None:
    self.player.load_entry(entry)
    self.switchTo(self.player)

def return_to_library(self) -> None:
    self.player.stop()
    self.switchTo(self.library)
```

- [ ] **Step 8: 运行 GUI import 测试**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest tests.test_gui_import -v
```

Expected:

```text
OK
```

- [ ] **Step 9: 提交**

```powershell
git add src/ultrastar_clone/gui/app.py tests/test_gui_import.py
git commit -m "Add library playback UI"
```

---

## Task 5: 全量验证和人工播放检查

**Files:**
- No planned source edits.

- [ ] **Step 1: 运行完整单元测试**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest discover -s tests -v
```

Expected:

```text
OK
```

- [ ] **Step 2: 启动 GUI**

Run:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m ultrastar_clone.gui_app
```

Expected:

```text
The desktop window opens with Import, Library, Player, Logs, and Settings navigation entries.
```

- [ ] **Step 3: 人工验证曲库播放**

Use the GUI:

1. Open `Library`.
2. Set song folder to `D:\GUI_shuai\demo_output`.
3. Click `Refresh`.
4. Confirm rows show title, artist, TXT, MP3, MP4, folder, and Play.
5. Click Play on a media-backed song.
6. Confirm the Player page opens.
7. Confirm `mp4` songs show video.
8. Confirm `mp3`-only songs show the audio fallback panel.
9. Confirm previous/current/next lyric labels update during playback when TXT has valid `#BPM`.
10. Let the media reach the end and confirm the app returns to Library automatically.

- [ ] **Step 4: 如果人工验证发现 Qt Multimedia 后端问题，记录实际错误并停止执行**

If playback fails, collect:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m ultrastar_clone.gui_app
```

Expected useful evidence:

```text
The Player page status label shows the Qt Multimedia error message, or the terminal prints a media backend error.
```

If this step exposes a playback backend defect, pause this plan and start a separate debugging pass with `superpowers:systematic-debugging`.

---

## 自检结果

- Spec coverage:
  - TXT 解析：Task 1。
  - `15000 / BPM` 歌词时间轴：Task 2。
  - 曲库扫描、标题歌手、首选 `mp4`、可播放状态：Task 3。
  - Library 播放入口、Player 页面、Qt Multimedia、歌词三行、进度条、返回：Task 4。
  - 播放结束自动返回曲库：Task 4 的 `_on_media_status_changed` 和 Task 5 的人工验证。
  - 不实现麦克风、音高、评分、排行榜等范围外功能：所有任务均未包含这些内容。

- Red-flag scan:
  - 本计划没有未定项、空洞占位说明或不确定实现分支。
  - 每个生产代码任务都有先写失败测试、验证失败、实现、验证通过、提交步骤。

- Type consistency:
  - `Song`, `LyricsLine`, `Note` 在 Task 1 定义，Task 2 和 Task 3 使用同名类型。
  - `TimedLyricsLine`, `LyricsWindow`, `build_timed_lyrics`, `lyrics_at_position` 在 Task 2 定义，Task 4 使用同名函数。
  - `SongLibraryEntry.preferred_media_path`, `display_title`, `display_artist`, `is_playable` 在 Task 3 定义，Task 4 使用同名属性。
