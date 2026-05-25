"""User-facing error message helpers."""

from __future__ import annotations

import socket
from urllib.error import HTTPError, URLError

from yt_dlp.utils import DownloadError


def format_user_error(error: BaseException) -> str:
    """Return an actionable message for errors shown in the GUI or CLI."""
    chain = tuple(_walk_exception_chain(error))
    text = " ".join(str(exc) for exc in chain).lower()

    http_error = _first_of_type(chain, HTTPError)
    if http_error is not None:
        return (
            f"Network request failed (HTTP {http_error.code}). "
            "The remote service may be temporarily unavailable; check your internet connection and try again later."
        )

    if "usdb login failed" in text:
        return (
            "USDB login failed. Check the username and password in Settings, then try again. "
            "If the credentials are correct, USDB may be temporarily blocking or changing the login page."
        )

    if _first_of_type(chain, URLError) is not None or _first_of_type(chain, socket.timeout) is not None:
        return "Network request failed. Check your internet connection, VPN/proxy, and try again."

    if _looks_like_youtube_error(chain, text):
        return _format_youtube_error(text)

    if "ffmpeg was not found" in text:
        return (
            "ffmpeg was not found. The release build should include ffmpeg; re-download the EXE/ZIP "
            "or rebuild with src/ultrastar_clone/bin/ffmpeg.exe included."
        )

    if isinstance(error, PermissionError) or "access is denied" in text or "permission denied" in text:
        return (
            "Permission denied. Choose a writable output folder and check whether Windows security software "
            "or Controlled Folder Access is blocking the app."
        )

    return str(error) or error.__class__.__name__


def _format_youtube_error(text: str) -> str:
    if "requested format is not available" in text or "only images are available" in text:
        detail = "The selected YouTube format is no longer available for this video."
    elif "http error 403" in text or "forbidden" in text or "po token" in text:
        detail = "YouTube rejected the request, which can happen when yt-dlp needs updated extraction logic or cookies."
    else:
        detail = "YouTube changed or rejected the media download request."
    return (
        f"YouTube download failed. {detail} Update yt-dlp in a source build, try again later, "
        "or configure browser cookies if the video requires account/session access."
    )


def _looks_like_youtube_error(chain: tuple[BaseException, ...], text: str) -> bool:
    return _first_of_type(chain, DownloadError) is not None or "yt-dlp failed" in text or "youtube" in text


def _first_of_type(chain: tuple[BaseException, ...], exc_type: type[BaseException]) -> BaseException | None:
    for exc in chain:
        if isinstance(exc, exc_type):
            return exc
    return None


def _walk_exception_chain(error: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    current: BaseException | None = error
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain
