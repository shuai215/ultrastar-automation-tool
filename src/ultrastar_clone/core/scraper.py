"""USDB login, search, and detail-page parsing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from html import unescape
from http.cookiejar import CookieJar
import re
import unicodedata
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

from ultrastar_clone.models import SongMetadata, SongRequest


class SongScraper(ABC):
    @abstractmethod
    def find(self, request: SongRequest) -> SongMetadata:
        """Find a song in an external source."""


class NotImplementedScraper(SongScraper):
    def find(self, request: SongRequest) -> SongMetadata:
        raise NotImplementedError("USDB scraper is not implemented yet")


@dataclass(frozen=True)
class SearchCandidate:
    song_id: str
    artist: str
    title: str
    url: str


class USDBScraper(SongScraper):
    base_url = "https://usdb.animux.de/"

    def __init__(self, username: str, password: str, timeout: int = 20) -> None:
        self.username = username
        self.password = password
        self.timeout = timeout
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
        self._logged_in = False

    def login(self) -> bool:
        payload = urlencode(
            {
                "user": self.username,
                "pass": self.password,
                "remember": "1",
                "login": "Login",
            }
        ).encode("utf-8")

        html = self._request("?link=login", data=payload)
        self._logged_in = "logout" in html.lower()
        return self._logged_in

    def find(self, request: SongRequest) -> SongMetadata:
        if not self._logged_in and not self.login():
            raise PermissionError("USDB login failed")

        if request.selected_song_id:
            return self.metadata_for_song_id(request.selected_song_id)

        candidates = self.search(request)
        match = choose_exact_candidate(candidates, request)
        if match is None:
            if not candidates:
                raise LookupError(f"song not found: {request.artist} - {request.title}")
            match = candidates[0]

        return self.metadata_for_candidate(match)

    def search(self, request: SongRequest) -> list[SearchCandidate]:
        if not self._logged_in and not self.login():
            raise PermissionError("USDB login failed")
        html = self._search(request)
        return parse_search_candidates(html, self.base_url)

    def metadata_for_candidate(self, candidate: SearchCandidate) -> SongMetadata:
        if not self._logged_in and not self.login():
            raise PermissionError("USDB login failed")
        detail_html = self._request(candidate.url)
        youtube_url = extract_youtube_url(detail_html)
        return SongMetadata(song_id=candidate.song_id, youtube_url=youtube_url)

    def metadata_for_song_id(self, song_id: str) -> SongMetadata:
        if not self._logged_in and not self.login():
            raise PermissionError("USDB login failed")
        detail_url = urljoin(self.base_url, f"?link=detail&id={song_id}")
        return self.metadata_for_candidate(SearchCandidate(song_id, "", "", detail_url))

    def _search(self, request: SongRequest) -> str:
        query = {
            "link": "list",
            "interpret": request.artist,
            "title": request.title,
        }
        return self._request("?" + urlencode(query))

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


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    asciiish = "".join(char for char in decomposed if not unicodedata.combining(char))
    asciiish = unescape(asciiish).lower()
    asciiish = re.sub(r"\s+", " ", asciiish)
    return asciiish.strip()


def parse_search_candidates(html: str, base_url: str = USDBScraper.base_url) -> list[SearchCandidate]:
    table_candidates = parse_table_candidates(html, base_url)
    if table_candidates:
        return table_candidates
    return parse_link_candidates(html, base_url)


def parse_table_candidates(html: str, base_url: str) -> list[SearchCandidate]:
    candidates: list[SearchCandidate] = []
    row_pattern = re.compile(
        r"<tr[^>]*data-songid=['\"]?(?P<id>\d+)['\"]?[^>]*>(?P<body>.*?)</tr>",
        re.I | re.S,
    )
    cell_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.I | re.S)

    for row in row_pattern.finditer(html):
        cells = [clean_html(cell) for cell in cell_pattern.findall(row.group("body"))]
        if len(cells) < 2:
            continue
        song_id = row.group("id")
        detail_url = extract_detail_url(row.group("body"), song_id, base_url)
        candidates.append(
            SearchCandidate(
                song_id=song_id,
                artist=cells[0],
                title=cells[1],
                url=detail_url,
            )
        )
    return candidates


def parse_link_candidates(html: str, base_url: str) -> list[SearchCandidate]:
    candidates: list[SearchCandidate] = []
    seen: set[str] = set()

    for href, label in re.findall(r"<a\s+[^>]*href=['\"]?([^'\" >]+)[^>]*>(.*?)</a>", html, re.I | re.S):
        song_id = extract_song_id_from_url(href)
        if not song_id or song_id in seen:
            continue

        text = clean_html(label)
        artist, title = split_artist_title(text)
        candidates.append(
            SearchCandidate(
                song_id=song_id,
                artist=artist,
                title=title,
                url=urljoin(base_url, href),
            )
        )
        seen.add(song_id)

    return candidates


def extract_detail_url(row_html: str, song_id: str, base_url: str) -> str:
    match = re.search(r"href=['\"]?([^'\" >]*link=detail[^'\" >]*)", row_html, re.I)
    if match:
        return urljoin(base_url, unescape(match.group(1)))
    return urljoin(base_url, f"?link=detail&id={song_id}")


def extract_song_id_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("id", "songid", "song_id"):
        if key in query and query[key]:
            return query[key][0]

    match = re.search(r"(?:id|songid|song_id)=([0-9]+)", url, re.I)
    if match:
        return match.group(1)
    return None


def extract_youtube_url(html: str) -> str | None:
    match = re.search(r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)[^'\" <]+", html, re.I)
    if not match:
        return None
    return unescape(match.group(0))


def choose_exact_candidate(candidates: list[SearchCandidate], request: SongRequest) -> SearchCandidate | None:
    expected_artist = normalize_text(request.artist)
    expected_title = normalize_text(request.title)
    for candidate in candidates:
        if normalize_text(candidate.artist) == expected_artist and normalize_text(candidate.title) == expected_title:
            return candidate
    return None


def clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(without_tags)).strip()


def split_artist_title(value: str) -> tuple[str, str]:
    for separator in (" - ", " – ", " — "):
        if separator in value:
            artist, title = value.split(separator, 1)
            return artist.strip(), title.strip()
    return "", value.strip()

