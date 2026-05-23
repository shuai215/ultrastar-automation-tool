"""Build lyric timing windows for playback."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from ultrastar_clone.core.song_parser import LyricsLine, Song


@dataclass(frozen=True)
class TimedLyricsLine:
    """A lyric line with playback timestamps."""

    start_time_ms: int
    end_time_ms: int
    text: str
    source: LyricsLine


@dataclass(frozen=True)
class LyricsWindow:
    """The lyric context around a playback position."""

    previous: TimedLyricsLine | None
    current: TimedLyricsLine | None
    next: TimedLyricsLine | None


def build_timed_lyrics(song: Song) -> tuple[TimedLyricsLine, ...]:
    """Convert UltraStar beat-based lyric lines to playback timestamps."""

    if song.bpm is None or not isfinite(song.bpm) or song.bpm <= 0 or not song.lyrics:
        return ()

    unit_duration_ms = 15000.0 / song.bpm
    timed_lines = []
    for line in song.lyrics:
        start_time_ms = round(song.gap_ms + line.start_beat * unit_duration_ms)
        end_time_ms = round(song.gap_ms + line.end_beat * unit_duration_ms)
        if end_time_ms <= start_time_ms:
            end_time_ms = start_time_ms + 1
        timed_lines.append(
            TimedLyricsLine(
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                text=line.text,
                source=line,
            )
        )

    return tuple(sorted(timed_lines, key=lambda line: line.start_time_ms))


def lyrics_at_position(
    lines: Sequence[TimedLyricsLine],
    position_ms: int,
) -> LyricsWindow:
    """Return previous, current, and next lyric lines for a playback position."""

    previous = None
    current = None
    next_line = None

    for line in lines:
        if line.start_time_ms <= position_ms < line.end_time_ms:
            current = line
            continue
        if line.end_time_ms <= position_ms:
            previous = line
            continue
        if line.start_time_ms > position_ms and next_line is None:
            next_line = line
            break

    if current is not None:
        next_line = _next_after(lines, current)

    return LyricsWindow(previous=previous, current=current, next=next_line)


def _next_after(
    lines: Sequence[TimedLyricsLine],
    current: TimedLyricsLine,
) -> TimedLyricsLine | None:
    for line in lines:
        if line.start_time_ms > current.start_time_ms:
            return line
    return None
