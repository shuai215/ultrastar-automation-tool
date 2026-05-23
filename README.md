# UltraStar Clone

Clean-room rebuild of an UltraStar song import assistant.

The implementation is intentionally separate from the previous team project. We use the old project as a feature reference only.

## Current State

Implemented so far:

- Shared song data models
- Settings paths and logger
- UltraStar `.txt` editor
  - update `#MP3` and `#VIDEO`
  - read/write/adjust `#GAP`
  - create and restore `.bak` files
- USDB scraper
  - login with session cookies
  - search by artist/title
  - parse `data-songid` result rows
  - extract YouTube URL from detail page
- USDB text downloader
  - handles USDB waiting page
  - submits `wd=1`
  - extracts raw UltraStar text from `<textarea name="txt">`
  - verifies `#ARTIST` and `#TITLE`
- yt-dlp converter
  - mp3 extraction
  - mp4 download/merge
  - ffmpeg and yt-dlp path checks
- CLI demo
- QFluentWidgets GUI prototype
- Pipeline controller skeleton
- Offline unit tests for core behavior

## Run Tests

From this folder:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest discover -s tests -v
```

## Run CLI Demo

Credentials are read from environment variables, not source code:

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'
python -m ultrastar_clone.cli --artist 'Usher' --title 'U Remind Me' --output 'D:\GUI_shuai\demo_output' --skip-media
```

Remove `--skip-media` to also download/convert the YouTube media file.

## Run QFluentWidgets GUI

Install GUI dependencies first:

```powershell
pip install PyQt6 PyQt6-Fluent-Widgets
```

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'
python -m ultrastar_clone.gui_app
```

The first Fluent GUI version includes navigation, an import page, a settings page for session credentials, and a log page. In the import page, keep `Download media` checked to download a video file by default. Check `Convert to MP3 audio only` when you want the video source converted into an audio file instead.

## External Tools

The converter expects these commands on PATH:

```powershell
yt-dlp --version
ffmpeg -version
```

## Security Note

USDB credentials should not be written into source code. Use temporary environment variables or, later, the app settings UI.
