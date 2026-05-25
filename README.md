# UltraStar Clone

An UltraStar song import assistant — search USDB for lyrics, download `.txt` files, and convert YouTube media. Built with PyQt6 + QFluentWidgets.

## Quick Start

Download the latest EXE from [Releases](https://github.com/shuai215/ultrastar-automation-tool/releases) and run it. No Python, no standalone yt-dlp, and no separate ffmpeg install are required for the release build.

1. Download `UltraStar-Clone.exe` from the latest release
2. Run it
3. Enter your USDB credentials in Settings

## Features

- **USDB Search** - Search by artist/title, pick from results
- **Direct URL** - Paste a YouTube link, download media directly
- **Lyrics Download** - Fetch UltraStar `.txt` files from USDB
- **Media Conversion** - YouTube to MP3/MP4 via bundled yt-dlp package and ffmpeg
- **Tag Editing** - Auto-update `#MP3`, `#VIDEO`, `#GAP` in lyric files
- **Local Library** - Browse imported songs with format indicators, favorites, and delete
- **Built-in Player** - 16:9 video playback with smooth-scrolling synced lyrics
- **System Theme** - Follows OS light/dark mode, updates at runtime

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

Release builds bundle the Python `yt-dlp` package and `src/ultrastar_clone/bin/ffmpeg.exe` through PyInstaller.

For source runs:

- `yt-dlp` is installed by `requirements.txt`.
- `ffmpeg.exe` should be available at `src/ultrastar_clone/bin/ffmpeg.exe` or on `PATH`.

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
|-- models.py                # Shared data models
|-- cli.py                   # CLI entry point
|-- gui_app.py               # GUI launcher
|-- core/                    # Domain logic, no GUI dependencies
|   |-- scraper.py           # USDB login, search, detail-page parsing
|   |-- downloader.py        # USDB lyrics download
|   |-- converter.py         # yt-dlp Python API wrapper, bundled ffmpeg support
|   |-- editor.py            # UltraStar txt tag editing
|   |-- song_parser.py       # UltraStar txt file parser
|   `-- playback_timeline.py # BPM-to-ms timeline and lyric lookup
|-- services/                # Application orchestration
|   |-- controller.py        # Import pipeline
|   |-- errors.py            # User-facing error messages
|   |-- settings.py          # Config persistence
|   |-- library.py           # Local song folder scanner
|   `-- logger.py            # File + console logger
|-- gui/                     # Qt presentation layer
|   |-- app.py               # Entry point, theme/palette sync
|   |-- main_window.py       # FluentWindow, navigation, signal wiring
|   |-- home_page.py         # Import page
|   |-- library_page.py      # Library page
|   |-- player_page.py       # Player page
|   |-- settings_page.py     # Settings page
|   |-- log_page.py          # Log page
|   |-- workers.py           # QThread workers
|   |-- widgets.py           # Custom widgets
|   `-- utils.py             # Helpers
`-- bin/                     # Bundled native tools (ffmpeg.exe)
```

## Troubleshooting

- **USDB login failed**: Check the username/password in Settings. If they are correct, USDB may be temporarily unavailable or may have changed its login page.
- **Network request failed**: Check internet access, VPN/proxy settings, and try again.
- **YouTube download failed**: YouTube extraction can break when YouTube changes. Source builds can update `yt-dlp`; release builds need a new packaged EXE.
- **ffmpeg was not found**: The release EXE should include ffmpeg. Re-download the release ZIP/EXE or rebuild with `src/ultrastar_clone/bin/ffmpeg.exe` present.
- **Permission denied**: Choose a writable output folder and check whether Windows security software or Controlled Folder Access is blocking the app.
