# UltraStar Clone

[中文版本](README_ZH.md)

An UltraStar song import assistant — search USDB for lyrics, download UltraStar `.txt` files, and convert YouTube media via yt-dlp.

## Features

- **USDB Search** — Search by artist/title, select from result list
- **Direct URL** — Skip search, download media directly from a YouTube link
- **Lyrics Download** — Fetch `.txt` lyric files from USDB
- **Media Conversion** — yt-dlp convert YouTube videos to MP3/MP4
- **Tag Editing** — Auto-update `#MP3`, `#VIDEO`, `#GAP` tags
- **Local Library** — Scan and browse imported songs, built-in player with synced lyrics
- **Persistent Settings** — Theme, output folder, download defaults, and credentials saved to `~/.ultrastar_clone/`

## Architecture

```
src/ultrastar_clone/
├── models.py               # Shared data models (SongRequest, SongMetadata, ImportResult)
├── cli.py                  # CLI entry point
├── gui_app.py              # GUI launcher
│
├── core/                   # Domain logic (no GUI deps)
│   ├── scraper.py          # USDB login, search, detail-page parsing
│   ├── downloader.py       # USDB lyrics download, wait-page handling
│   ├── converter.py        # yt-dlp media download/convert (MP3/MP4)
│   ├── editor.py           # UltraStar txt tag editing (#MP3/#VIDEO/#GAP)
│   ├── song_parser.py      # UltraStar txt file parser
│   └── playback_timeline.py # Lyric timing calculation
│
├── services/               # Application orchestration (no GUI deps)
│   ├── controller.py       # Import pipeline (search → lyrics → media → tags)
│   ├── settings.py         # Config paths, credentials/preferences persistence
│   ├── library.py          # Local song folder scanner
│   └── logger.py           # File + console logger factory
│
├── gui/                    # Qt UI (QFluentWidgets)
│   ├── app.py              # Entry point, backward-compatible re-exports
│   ├── main_window.py      # Main window, page navigation, signal wiring
│   ├── home_page.py        # Import page (search USDB or paste YouTube URL)
│   ├── library_page.py     # Library page (browse local songs)
│   ├── player_page.py      # Player page (video/audio + synced lyrics)
│   ├── settings_page.py    # Settings page (credentials, theme, import defaults)
│   ├── log_page.py         # Log page
│   ├── workers.py          # Background workers (ImportWorker, SearchWorker)
│   ├── widgets.py          # Custom widgets (lyric display, table)
│   └── utils.py            # Helper functions (no Qt dependency)
│
tests/                      # Unit tests (unittest)
```

## Quick Start

### Install

```powershell
pip install -e ".[dev]"
```

External tools (required on PATH): `yt-dlp`, `ffmpeg`

### CLI

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'

# Search mode
python -m ultrastar_clone.cli --artist 'Coldplay' --title 'Yellow' --output demo_output

# Direct URL mode
python -m ultrastar_clone.cli --mode url --youtube-url 'https://...' --output demo_output --video

# Lyrics only
python -m ultrastar_clone.cli --artist 'Usher' --title 'U Remind Me' --output demo_output --skip-media
```

### GUI

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'
python -m ultrastar_clone.gui_app
```

Four pages:

| Page | Function |
|------|----------|
| **Import** | Search or paste YouTube URL, one-click import |
| **Library** | Browse local songs, double-click to play |
| **Settings** | Theme, output folder, download defaults, credentials |
| **Log** | View import logs |

## Tests

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest discover -s tests -v
```

## Notes

- Credentials via env vars or settings page — **never hardcode them**
- Songs save to the standard UltraStar song directory by default; customize in Settings
