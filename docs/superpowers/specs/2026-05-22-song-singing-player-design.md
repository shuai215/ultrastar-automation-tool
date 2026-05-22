# Song Singing Player MVP Design

Date: 2026-05-22

## Goal

Build the first song singing feature directly into the current desktop app by extending the existing Song Library page. This phase is a lightweight UltraStar-style player and sing-along view. It plays prepared local video or audio files and synchronizes UltraStar lyrics. It does not implement microphone input, pitch detection, scoring, rankings, multiplayer, themes, plugins, camera features, or party mode.

## Confirmed Decisions

- Keep the current `PyQt6` and `PyQt6-Fluent-Widgets` stack for this phase.
- Extend the existing `Song Library` page instead of creating a separate app package.
- Add a focused player page behind the Library page.
- Prefer `mp4` video when both `mp4` and `mp3` are available for the same song.
- Play `mp3` as a fallback when no video is available.
- Keep parsing, scanning, playback timeline, and media control separated from UI widgets.

## Current Project Fit

The repository is currently an UltraStar import assistant with:

- Shared request/result models in `src/ultrastar_clone/models.py`
- Import pipeline services in `src/ultrastar_clone/services/`
- UltraStar TXT editing helpers in `src/ultrastar_clone/core/editor.py`
- A QFluentWidgets GUI in `src/ultrastar_clone/gui/app.py`
- A simple library scanner in `src/ultrastar_clone/services/library.py`

The player MVP should build on this structure rather than introduce a new top-level `app/` package.

## Architecture

Add core playback-oriented modules:

- `src/ultrastar_clone/core/song_parser.py`
  - Parses UltraStar TXT metadata and note rows.
  - Supports tags used by this MVP: `#TITLE`, `#ARTIST`, `#MP3`, `#AUDIO`, `#VIDEO`, `#COVER`, `#BPM`, and `#GAP`.
  - Supports note markers `:`, `*`, and `F`; line breaks `-`; and end marker `E`.
  - Treats `*` and `F` as note types but does not give them special gameplay behavior.

- `src/ultrastar_clone/core/playback_timeline.py`
  - Converts note beats into millisecond lyric line windows using `BPM` and `GAP`.
  - Returns previous, current, and next lyric lines for a given playback position.
  - Handles missing or empty lyrics without crashing the UI.

Extend service scanning:

- `src/ultrastar_clone/services/library.py`
  - Continue scanning song folders.
  - Include resolved paths for TXT, MP3, MP4, and cover files.
  - Include parsed title and artist when TXT metadata exists.
  - Include the preferred playable media path, with `mp4` before `mp3`.
  - Mark entries as playable only when a preferred media path exists.

Extend GUI:

- `src/ultrastar_clone/gui/app.py`
  - Update `LibraryPage` to show title, artist, resource status, and a Play action.
  - Add `PlayerPage` as a `FluentWindow` sub-interface named `Player` and switch to it programmatically when a Library row is played.
  - Use Qt Multimedia for playback.
  - Show video when playing `mp4`.
  - Show an audio fallback panel when playing `mp3`.
  - Display previous, current, and next lyric lines.
  - Provide Back, Play/Pause, and progress slider controls.
  - Return to the Library page automatically when playback reaches the end of the media.

## Data Model

Use small immutable domain objects in `src/ultrastar_clone/core/song_parser.py` for the MVP:

- `Song`
  - `title`
  - `artist`
  - `folder_path`
  - `txt_path`
  - `audio_path`
  - `video_path`
  - `cover_path`
  - `bpm`
  - `gap`
  - `lyrics`

- `LyricsLine`
  - `start_time_ms`
  - `end_time_ms`
  - `text`
  - `notes`

- `Note`
  - `start_beat`
  - `duration`
  - `pitch`
  - `syllable`
  - `type`

If these models grow after the MVP, move them into `core/song_model.py` in a later refactor.

## User Flow

1. User opens the existing Library page.
2. User chooses or keeps a song root folder.
3. Library scans child song folders.
4. Each row shows title, artist, TXT availability, MP3 availability, MP4 availability, and whether it can be played.
5. User clicks Play for a playable entry.
6. App switches to the Player page.
7. Player opens the preferred media path.
8. During playback, a timer reads the current media position and updates previous, current, and next lyrics.
9. User can pause, resume, scrub, or return to Library.
10. When the media finishes, the app stops the player and switches back to the Library page automatically.

## Playback Rules

- If both `mp4` and `mp3` exist, play the `mp4`.
- If only `mp3` exists, play the `mp3` and show a non-video fallback panel.
- If only TXT exists, do not enable Play because there is no media.
- If no TXT exists but media exists, allow playback and show a clear no-lyrics state.
- If TXT exists but cannot be parsed, allow media playback and show a clear lyric parse error state.
- If `#BPM` is missing or invalid, allow media playback but disable synchronized lyrics.
- If `#GAP` is missing, default to `0` milliseconds.
- When Qt Multimedia reports end-of-media, stop lyric timer updates, clear transient player state, and switch back to the Library page.

## UltraStar Timing

UltraStar TXT note start and duration values are beat-based, with four note units per musical beat. The MVP should convert UltraStar note units to milliseconds with:

```text
unit_duration_ms = 15000 / bpm
note_start_ms = gap_ms + start_beat * unit_duration_ms
note_end_ms = gap_ms + (start_beat + duration) * unit_duration_ms
```

If real sample files expose a mismatch with UltraStar Deluxe timing conventions, adjust this in `playback_timeline.py` behind tests rather than scattering timing math through the UI.

## Error Handling

- Library scanning should skip unreadable folders and continue scanning the rest.
- TXT parsing should ignore malformed lyric rows and preserve valid rows.
- Missing files referenced by TXT tags should not crash scanning; scanner can fall back to globbed media files in the folder.
- Player should show an in-page error for media load or playback errors and keep the Back action usable.
- User-facing errors should be concise and actionable.

## Testing Strategy

Use TDD for behavior-bearing code:

- Parser tests:
  - Parses tags.
  - Parses normal, golden, and freestyle notes.
  - Groups notes into lyric lines on `-`.
  - Handles `#AUDIO` as an audio alias.
  - Defaults missing `#GAP` to `0`.

- Timeline tests:
  - Converts notes to lyric windows.
  - Returns previous, current, and next lines for a media position.
  - Handles positions before the first line and after the last line.
  - Handles no lyrics.

- Library tests:
  - Reports title and artist from TXT metadata.
  - Resolves preferred media as `mp4` before `mp3`.
  - Marks media-only songs playable.
  - Marks TXT-only songs not playable.

- GUI tests:
  - Keep import-safety tests lightweight.
  - Avoid relying on real Qt media playback in unit tests.

## Implementation Boundaries

Do not implement these in the MVP:

- Microphone capture
- Pitch detection
- Scoring
- Note track rendering
- Rankings
- Playlists
- Multiplayer
- Theme system
- Lua or plugin support
- Packaging

The design should leave a place for a future note track, but the MVP lyric display is previous/current/next text only.
