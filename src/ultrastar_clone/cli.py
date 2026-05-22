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
    parser.add_argument("--mode", choices=["search", "url"], default="search", help="Input mode")
    parser.add_argument("--artist", default="", help="Song artist as written on USDB")
    parser.add_argument("--title", default="", help="Song title as written on USDB")
    parser.add_argument("--youtube-url", default=None, help="Direct YouTube URL")
    parser.add_argument("--format", choices=["mp3", "mp4"], default="mp3", help="Media format")
    parser.add_argument("--output", type=Path, default=None, help="Target songs folder")
    parser.add_argument("--lyrics", action="store_true", help="Download UltraStar txt lyrics")
    parser.add_argument("--audio", action="store_true", help="Download MP3 audio")
    parser.add_argument("--video", action="store_true", help="Download MP4 video")
    parser.add_argument("--skip-media", action="store_true", help="Download only the UltraStar txt file")
    parser.add_argument("--no-wait", action="store_true", help="Skip the USDB wait timer; useful only for development")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    download_audio = args.audio or (not args.video and not args.skip_media and args.format == "mp3")
    download_video = args.video or (not args.audio and not args.skip_media and args.format == "mp4")
    download_lyrics = args.lyrics or args.skip_media or args.mode == "search"

    username = os.getenv("USDB_USER")
    password = os.getenv("USDB_PASS")
    if (args.mode == "search" or download_lyrics) and (not username or not password):
        raise SystemExit("Set USDB_USER and USDB_PASS environment variables first.")

    output = args.output or default_song_root()
    settings = AppSettings(song_root=output, log_dir=default_log_dir())
    logger = build_logger(settings.log_dir)

    request = SongRequest(
        args.artist,
        args.title,
        args.format,
        target_root=output,
        input_mode=args.mode,
        youtube_url=args.youtube_url,
        download_lyrics=download_lyrics,
        download_audio=download_audio,
        download_video=download_video,
    )
    scraper = USDBScraper(username, password) if username and password else None
    downloader = USDBTextDownloader(opener=scraper.opener if scraper else None, respect_wait=not args.no_wait)
    converter = NoMediaConverter() if not download_audio and not download_video else YtDlpConverter()
    controller = ImportController(settings, scraper, downloader, converter, logger=logger)

    result = controller.import_song(request)
    print(f"Song folder: {result.song_folder}")
    print(f"TXT file: {result.txt_path or 'skipped'}")
    if result.media_paths:
        for media_path in result.media_paths:
            print(f"Media file: {media_path}")
    else:
        print("Media file: skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

