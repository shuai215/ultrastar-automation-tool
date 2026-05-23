# UltraStar Clone

An UltraStar song import assistant — search USDB for lyrics, download UltraStar `.txt` files, and convert YouTube media via yt-dlp. Built with PyQt6 + QFluentWidgets.

## Features

- **USDB Search** — Search by artist/title, select from result list
- **Direct URL** — Skip search, download media directly from a YouTube link
- **Lyrics Download** — Fetch `.txt` lyric files from USDB
- **Media Conversion** — yt-dlp convert YouTube videos to MP3/MP4
- **Tag Editing** — Auto-update `#MP3`, `#VIDEO`, `#GAP` tags in lyric files
- **Local Library** — Browse imported songs with TXT/MP3/MP4 status indicators, favorites (persistent), and delete
- **Built-in Player** — 16:9 video playback with synchronized three-line lyrics display
- **System Theme** — Follows OS light/dark mode, updates at runtime
- **No Heavy Dependencies** — HTTP and HTML parsing use only Python stdlib (`urllib` + `re`)

## Requirements

- Python >= 3.11
- `yt-dlp` and `ffmpeg` on PATH

```powershell
pip install -r requirements.txt
```

## Quick Start

### CLI

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'

# Search mode (lyrics + audio)
python -m ultrastar_clone.cli --artist 'Coldplay' --title 'Yellow' --output demo_output

# Direct URL mode (download video)
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

| Page | Function |
|------|----------|
| **Import** | Search USDB or paste YouTube URL, one-click import with progress |
| **Library** | Browse local songs, favorite/delete, double-click or play button to open |
| **Player** | 16:9 video/audio playback with synced lyrics, seek, pause/resume |
| **Logs** | View import activity log |
| **Settings** | Credentials, output folder, download defaults |

## Architecture

```
src/ultrastar_clone/
├── models.py               # Shared data models (SongRequest, SongMetadata, ImportResult)
├── cli.py                  # CLI entry point
├── gui_app.py              # GUI launcher

├── core/                   # Domain logic (no GUI deps)
│   ├── scraper.py          # USDB login, search, detail-page parsing (stdlib urllib + re)
│   ├── downloader.py       # USDB lyrics download, wait-page handling
│   ├── converter.py        # yt-dlp subprocess wrapper (MP3/MP4)
│   ├── editor.py           # UltraStar txt tag editing (#MP3/#VIDEO/#GAP)
│   ├── song_parser.py      # UltraStar txt file parser → Song dataclass
│   └── playback_timeline.py # BPM → ms timeline, lyric window at playback position

├── services/               # Application orchestration (no GUI deps)
│   ├── controller.py       # Import pipeline: search → lyrics → media → tags
│   ├── settings.py         # Config paths, credentials/preferences/favorites JSON persistence
│   ├── library.py          # Local song folder scanner
│   └── logger.py           # File + console logger

├── gui/                    # Qt presentation layer
│   ├── app.py              # Entry point, theme/palette sync
│   ├── main_window.py      # FluentWindow: navigation, signal wiring, background threads
│   ├── home_page.py        # Import page (search/paste URL, results table, progress)
│   ├── library_page.py     # Library page (song table, favorites, delete)
│   ├── player_page.py      # Player page (16:9 video, synced lyrics, controls)
│   ├── settings_page.py    # Settings page (credentials, output, defaults)
│   ├── log_page.py         # Log page (import activity)
│   ├── workers.py          # QThread workers (ImportWorker, SearchWorker)
│   ├── widgets.py          # Custom widgets (LyricDisplayWidget, AnimatedProgressBar)
│   └── utils.py            # Helpers (lyric cleanup, time formatting)

tests/                      # Unit tests (unittest, no network)
```

## Tests

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest discover -s tests -v
```

Tests use fake implementations (no network calls) and `tempfile.TemporaryDirectory` for file I/O.

## Configuration

All data stored in `~/.ultrastar_clone/`:

| File | Content |
|------|---------|
| `credentials.json` | USDB username/password |
| `preferences.json` | Theme, output folder, download defaults |
| `favorites.json` | Favorite song folder paths |

Credentials can also be set via `USDB_USER` / `USDB_PASS` environment variables (takes priority).

## Notes

- **Never hardcode credentials** — use env vars or the Settings page
- Songs are saved to `demo_output/` by default; customize in Settings
- The HTML scraper uses stdlib `re` — no BeautifulSoup or Requests needed
