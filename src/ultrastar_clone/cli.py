"""Command-line entry point for imports.

导入功能的命令行入口。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ultrastar_clone.core.converter import NoMediaConverter, YtDlpConverter
from ultrastar_clone.core.downloader import USDBTextDownloader
from ultrastar_clone.core.scraper import USDBScraper
from ultrastar_clone.models import SongRequest
from ultrastar_clone.services.controller import ImportController
from ultrastar_clone.services.logger import build_logger
from ultrastar_clone.services.settings import AppSettings, default_log_dir, default_song_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import an UltraStar song from USDB.")
    parser.add_argument("--artist", required=True, help="Song artist as written on USDB")
    parser.add_argument("--title", required=True, help="Song title as written on USDB")
    parser.add_argument("--format", choices=["mp3", "mp4"], default="mp3", help="Media format")
    parser.add_argument("--output", type=Path, default=None, help="Target songs folder")
    parser.add_argument("--skip-media", action="store_true", help="Download only the UltraStar txt file")
    parser.add_argument("--no-wait", action="store_true", help="Skip the USDB wait timer; useful only for development")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    username = os.getenv("USDB_USER")
    password = os.getenv("USDB_PASS")
    if not username or not password:
        raise SystemExit("Set USDB_USER and USDB_PASS environment variables first.")

    output = args.output or default_song_root()
    settings = AppSettings(song_root=output, log_dir=default_log_dir())
    logger = build_logger(settings.log_dir)

    request = SongRequest(args.artist, args.title, args.format, target_root=output)
    scraper = USDBScraper(username, password)
    downloader = USDBTextDownloader(opener=scraper.opener, respect_wait=not args.no_wait)
    converter = NoMediaConverter() if args.skip_media else YtDlpConverter()
    controller = ImportController(settings, scraper, downloader, converter, logger=logger)

    result = controller.import_song(request)
    print(f"Song folder: {result.song_folder}")
    print(f"TXT file: {result.txt_path}")
    if result.media_path:
        print(f"Media file: {result.media_path}")
    else:
        print("Media file: skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

