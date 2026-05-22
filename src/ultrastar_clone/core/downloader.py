"""Download and extract UltraStar txt files from USDB.

从 USDB 下载并提取 UltraStar 的 txt 歌曲文件。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from html import unescape
from http.cookiejar import CookieJar
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

from ultrastar_clone.models import SongMetadata, SongRequest


class TextDownloader(ABC):
    @abstractmethod
    def download_txt(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path:
        """Download or create the UltraStar .txt file."""


class NotImplementedDownloader(TextDownloader):
    def download_txt(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path:
        raise NotImplementedError("USDB text downloader is not implemented yet")


class USDBTextDownloader(TextDownloader):
    base_url = "https://usdb.animux.de/"

    def __init__(
        self,
        opener=None,
        timeout: int = 20,
        respect_wait: bool = True,
        max_wait_seconds: int = 30,
    ) -> None:
        self.timeout = timeout
        self.respect_wait = respect_wait
        self.max_wait_seconds = max_wait_seconds
        self.opener = opener or build_opener(HTTPCookieProcessor(CookieJar()))

    def download_txt(self, request: SongRequest, metadata: SongMetadata, song_folder: Path) -> Path:
        song_folder.mkdir(parents=True, exist_ok=True)
        html = self._open_gettxt(metadata.song_id)
        song_text = extract_txt_from_gettxt_html(html)
        verify_song_text(song_text, request)

        txt_path = song_folder / f"{request.folder_name}.txt"
        txt_path.write_text(song_text, encoding="utf-8", newline="\n")
        return txt_path

    def _open_gettxt(self, song_id: str) -> str:
        wait_html = self._request(f"?link=gettxt&id={song_id}")
        wait_seconds = extract_wait_seconds(wait_html)
        if wait_seconds is not None and self.respect_wait:
            time.sleep(min(wait_seconds, self.max_wait_seconds))

        payload = urlencode({"wd": "1"}).encode("utf-8")
        return self._request(f"?link=gettxt&id={song_id}", data=payload)

    def _request(self, path_or_url: str, data: bytes | None = None) -> str:
        url = urljoin(self.base_url, path_or_url)
        req = Request(
            url,
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with self.opener.open(req, timeout=self.timeout) as response:
            body = response.read()
        return body.decode("utf-8", errors="replace")


def extract_wait_seconds(html: str) -> int | None:
    match = re.search(r"time\s*=\s*(\d+)\s*;", html)
    if not match:
        return None
    return int(match.group(1))


def extract_txt_from_gettxt_html(html: str) -> str:
    match = re.search(
        r"<textarea[^>]*name=['\"]?txt['\"]?[^>]*>(?P<txt>.*?)</textarea>",
        html,
        re.I | re.S,
    )
    if not match:
        raise ValueError("USDB response did not contain a txt textarea")

    text = unescape(match.group("txt"))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.strip() + "\n"
    if "#TITLE:" not in text.upper() or "#ARTIST:" not in text.upper():
        raise ValueError("downloaded txt is missing required UltraStar tags")
    return text


def verify_song_text(song_text: str, request: SongRequest) -> None:
    artist = read_tag(song_text, "ARTIST")
    title = read_tag(song_text, "TITLE")
    if artist is None or title is None:
        raise ValueError("downloaded txt is missing artist or title")
    if _normalize(artist) != _normalize(request.artist) or _normalize(title) != _normalize(request.title):
        raise ValueError(f"downloaded txt metadata mismatch: {artist} - {title}")


def read_tag(song_text: str, tag: str) -> str | None:
    prefix = f"#{tag.upper()}:"
    for line in song_text.splitlines():
        if line.upper().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value).casefold()).strip()

