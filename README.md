# UltraStar Clone

An UltraStar song import assistant — search USDB for lyrics, download `.txt` files, and convert YouTube media. Built with PyQt6 + QFluentWidgets.

## Quick Start

Download the latest EXE from [Releases](https://github.com/shuai215/ultrastar-automation-tool/releases) and run it. No Python, no ffmpeg, no dependencies — everything is bundled.

1. Download `UltraStar-Clone.exe` from the latest release
2. Run it
3. Enter your USDB credentials in Settings

## Features

- **USDB Search** — Search by artist/title, pick from results
- **Direct URL** — Paste a YouTube link, download media directly
- **Lyrics Download** — Fetch UltraStar `.txt` files from USDB
- **Media Conversion** — YouTube to MP3/MP4 via built-in yt-dlp + ffmpeg
- **Tag Editing** — Auto-update `#MP3`, `#VIDEO`, `#GAP` in lyric files
- **Local Library** — Browse imported songs with format indicators, favorites, and delete
- **Built-in Player** — 16:9 video playback with smooth-scrolling synced lyrics
- **System Theme** — Follows OS light/dark mode, updates at runtime

| Page | Function |
|------|----------|
| **Import** | Search USDB or paste YouTube URL, one-click import with progress |
| **Library** | Browse local songs, favorite/delete, double-click to play |
| **Player** | 16:9 video/audio playback with synced lyrics, seek, pause/resume |
| **Logs** | View import activity log |
| **Settings** | Credentials, output folder, download defaults |

## Configuration

All data stored in `~/.ultrastar_clone/`:

| File | Content |
|------|---------|
| `credentials.json` | USDB username/password (or use `USDB_USER` / `USDB_PASS` env vars) |
| `preferences.json` | Theme, output folder, download defaults |
| `favorites.json` | Favorite song folder paths |

## Development

Requires Python >= 3.11 and a conda environment.

```powershell
conda create -n new_for_project python=3.11
conda activate new_for_project
pip install -r requirements.txt
```

yt-dlp and ffmpeg are bundled via PyInstaller at build time. During development, ensure `yt-dlp` and `ffmpeg` are on PATH, or place `ffmpeg.exe` in `src/ultrastar_clone/bin/`.

### Run from source

```powershell
$env:PYTHONPATH = 'D:\GUI_shuai\src'
$env:USDB_USER   = 'your_user'
$env:USDB_PASS   = 'your_password'

# GUI
python -m ultrastar_clone.gui_app

# CLI
python -m ultrastar_clone.cli --artist 'Coldplay' --title 'Yellow' --output demo_output
```

### Tests

```powershell
$env:PYTHONPATH = 'D:\GUI_shuai\src'
python -m pytest tests/ -v
```

### Build EXE

```powershell
pyinstaller ultrastar_clone.spec --noconfirm
```

## Architecture

```
src/ultrastar_clone/
├── models.py               # Shared data models
├── cli.py                  # CLI entry point
├── gui_app.py              # GUI launcher
├── core/                   # Domain logic (no GUI deps)
│   ├── scraper.py          # USDB login, search, detail-page parsing
│   ├── downloader.py       # USDB lyrics download
│   ├── converter.py        # yt-dlp Python API wrapper (MP3/MP4)
│   ├── editor.py           # UltraStar txt tag editing
│   ├── song_parser.py      # UltraStar txt file parser
│   └── playback_timeline.py # BPM → ms timeline, lyric position lookup
├── services/               # Application orchestration
│   ├── controller.py       # Import pipeline
│   ├── settings.py         # Config persistence
│   ├── library.py          # Local song folder scanner
│   └── logger.py           # File + console logger
├── gui/                    # Qt presentation layer
│   ├── app.py              # Entry point, theme/palette sync
│   ├── main_window.py      # FluentWindow, navigation, signal wiring
│   ├── home_page.py        # Import page
│   ├── library_page.py     # Library page
│   ├── player_page.py      # Player page
│   ├── settings_page.py    # Settings page
│   ├── log_page.py         # Log page
│   ├── workers.py          # QThread workers
│   ├── widgets.py          # Custom widgets (lyric display, progress bar)
│   └── utils.py            # Helpers
└── bin/                    # Bundled native tools (ffmpeg.exe)
```
