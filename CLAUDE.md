# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A clean-room UltraStar song import assistant. Searches USDB (usdb.animux.de) for UltraStar `.txt` lyrics, downloads them, and uses yt-dlp to convert YouTube media (MP3/MP4).

## Environment

This project always uses conda environment **`new_for_project`**. All Python commands must run inside it:

```powershell
conda run -n new_for_project python ...
```

Never use the base conda environment or any other environment for this project.

## Commands

```powershell
# Run all tests
$env:PYTHONPATH='D:\GUI_shuai\src'
conda run -n new_for_project python -m unittest discover -s tests -v

# Or with pytest
conda run -n new_for_project pytest tests/ -v

# Run a single test file
conda run -n new_for_project python -m unittest tests.test_models -v

# Run CLI demo
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'
conda run -n new_for_project python -m ultrastar_clone.cli --artist 'Usher' --title 'U Remind Me' --output demo_output --skip-media

# Run GUI
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'
conda run -n new_for_project python -m ultrastar_clone.gui_app

# Build standalone EXE
conda run -n new_for_project pyinstaller ultrastar_clone.spec --noconfirm

# Install with dev deps
conda run -n new_for_project pip install -e ".[dev]"
```

External tools required on PATH: `yt-dlp`, `ffmpeg`.

## Architecture

Three-layer structure under `src/ultrastar_clone/`:

- **`core/`** — pure domain logic, no GUI or filesystem side-effects beyond what's explicit. Each module defines an ABC that serves as its public contract.
  - `scraper.py` — USDB login, search, detail-page parsing, YouTube URL extraction
  - `downloader.py` — USDB wait-page handling, `wd=1` form submission, txt extraction
  - `converter.py` — yt-dlp subprocess wrapper with progress streaming, retry on 403/SABR errors
  - `editor.py` — UltraStar `.txt` tag editing (`#MP3`, `#VIDEO`, `#GAP`), backup/restore

- **`services/`** — application orchestration, no GUI deps.
  - `controller.py` — `ImportController` runs the full pipeline: validate → search → download lyrics → convert media → edit txt tags. Reports progress via callbacks.
  - `settings.py` — config paths (`~/.ultrastar_clone/`), credentials/preferences JSON persistence, platform-appropriate default song root
  - `library.py` — local song-folder scanner
  - `logger.py` — file + console logger factory

- **`gui/`** — Qt presentation layer.
  - `app.py` — QFluentWidgets `FluentWindow` with Import, Library, Settings, and Log pages. `ImportWorker` runs the controller in a `QThread`.
  - `gui_app.py` — thin entry point that calls `app.main()`

- **`models.py`** — shared dataclasses: `SongRequest`, `SongMetadata`, `ImportResult`
- **`cli.py`** — argparse-based CLI entry point

## Testing conventions

Tests live in `tests/` and use `unittest` (stdlib). Dependencies are injected via ABCs — tests supply fake implementations (`FakeScraper`, `FakeDownloader`, `FakeConverter`, `FakeRunner`) rather than using `unittest.mock`. File-operation tests use `tempfile.TemporaryDirectory`. No tests hit the network.

## Credentials

USDB credentials come from env vars (`USDB_USER`, `USDB_PASS`) or `~/.ultrastar_clone/credentials.json`. Never hardcode them.
