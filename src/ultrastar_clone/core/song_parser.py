"""Parse UltraStar TXT song files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Note:
    """A single UltraStar note row."""

    start_beat: int
    duration: int
    pitch: int
    syllable: str
    type: str = ":"

    @property
    def end_beat(self) -> int:
        return self.start_beat + self.duration


@dataclass(frozen=True)
class LyricsLine:
    """A lyric line containing one or more notes."""

    notes: tuple[Note, ...]
    text: str
    start_beat: int
    end_beat: int


@dataclass(frozen=True)
class Song:
    """Parsed UltraStar song metadata and lyrics."""

    title: str = ""
    artist: str = ""
    audio_filename: str = ""
    video_filename: str = ""
    cover_filename: str = ""
    bpm: float | None = None
    gap_ms: int = 0
    lyrics: tuple[LyricsLine, ...] = field(default_factory=tuple)


def parse_ultrastar_txt(path: str | Path) -> Song:
    """Parse an UltraStar TXT file into a Song."""

    tags: dict[str, str] = {}
    lyrics: list[LyricsLine] = []
    current_notes: list[Note] = []

    for raw_line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        stripped_line = raw_line.strip()
        if not stripped_line:
            continue

        if stripped_line.startswith("#"):
            key, separator, value = stripped_line[1:].partition(":")
            if separator:
                tags[key.upper()] = value.strip()
            continue

        line = raw_line.lstrip()
        marker = line[0]
        if marker in {":", "*", "F"}:
            note = _parse_note(line)
            if note is not None:
                current_notes.append(note)
            continue

        if marker == "-":
            _append_lyrics_line(lyrics, current_notes)
            current_notes = []
            continue

        if marker == "E":
            break

    _append_lyrics_line(lyrics, current_notes)

    return Song(
        title=tags.get("TITLE", ""),
        artist=tags.get("ARTIST", ""),
        audio_filename=tags.get("MP3", tags.get("AUDIO", "")),
        video_filename=tags.get("VIDEO", ""),
        cover_filename=tags.get("COVER", ""),
        bpm=_parse_float(tags.get("BPM", "")),
        gap_ms=_parse_int(tags.get("GAP", ""), default=0),
        lyrics=tuple(lyrics),
    )


def _parse_note(line: str) -> Note | None:
    marker, rest = line[0], line[1:].lstrip()
    parts = rest.split(maxsplit=3)
    if len(parts) < 4:
        return None

    start_beat = _parse_int(parts[0])
    duration = _parse_int(parts[1])
    pitch = _parse_int(parts[2])
    if start_beat is None or duration is None or pitch is None:
        return None

    return Note(
        start_beat=start_beat,
        duration=duration,
        pitch=pitch,
        syllable=parts[3],
        type=marker,
    )


def _append_lyrics_line(lyrics: list[LyricsLine], notes: list[Note]) -> None:
    if not notes:
        return

    text = "".join(note.syllable for note in notes).strip()
    lyrics.append(
        LyricsLine(
            notes=tuple(notes),
            text=text,
            start_beat=notes[0].start_beat,
            end_beat=max(note.end_beat for note in notes),
        )
    )


def _parse_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _parse_int(value: str, default: int | None = None) -> int | None:
    try:
        return int(value)
    except ValueError:
        return default
