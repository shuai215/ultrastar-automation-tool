# UltraStar Clone

[中文版本](README.md)

An UltraStar song import assistant — search USDB for lyrics, download UltraStar `.txt` files, and convert YouTube media to MP3/MP4 via yt-dlp.

## Features

- **USDB Search** — Search by artist/title, select from result list
- **Direct URL** — Skip search, download media directly from a YouTube link
- **Lyrics Download** — Fetch `.txt` lyric files from USDB
- **Media Conversion** — Download and convert YouTube videos to MP3/MP4
- **Tag Editing** — Auto-update `#MP3`, `#VIDEO`, `#GAP` tags
- **Local Library** — Scan local songs and preview with built-in player
- **Persistence** — Theme, output folder, download defaults, and credentials saved to `~/.ultrastar_clone/`

## Project Structure

```
src/ultrastar_clone/
├── core/           # Domain logic (scraper, downloader, converter, editor, parser, playback)
├── services/       # Orchestration (controller, settings, library, logger)
├── gui/            # Qt UI (app.py)
├── models.py       # Shared data models
├── cli.py          # CLI entry
└── gui_app.py      # GUI launcher
tests/              # Unit tests (unittest)
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
