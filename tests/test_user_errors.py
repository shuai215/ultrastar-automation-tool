"""Tests for user-facing error messages."""

import socket
import unittest
from urllib.error import HTTPError, URLError

from yt_dlp.utils import DownloadError

from ultrastar_clone.services.errors import format_user_error


class UserErrorMessageTests(unittest.TestCase):
    def test_usdb_login_failure_has_actionable_message(self) -> None:
        message = format_user_error(PermissionError("USDB login failed"))

        self.assertIn("USDB login failed", message)
        self.assertIn("Settings", message)
        self.assertIn("username and password", message)

    def test_network_failure_mentions_connection_and_retry(self) -> None:
        message = format_user_error(URLError(socket.timeout("timed out")))

        self.assertIn("Network request failed", message)
        self.assertIn("internet connection", message)
        self.assertIn("try again", message)

    def test_http_failure_includes_status_code(self) -> None:
        message = format_user_error(HTTPError("https://example.test", 503, "Service Unavailable", {}, None))

        self.assertIn("HTTP 503", message)
        self.assertIn("temporarily unavailable", message)

    def test_youtube_failure_mentions_yt_dlp_and_cookies(self) -> None:
        message = format_user_error(RuntimeError("yt-dlp failed: HTTP Error 403: Forbidden"))

        self.assertIn("YouTube download failed", message)
        self.assertIn("yt-dlp", message)
        self.assertIn("cookies", message)

    def test_chained_download_error_is_detected(self) -> None:
        try:
            raise DownloadError("Requested format is not available")
        except DownloadError as exc:
            wrapped = RuntimeError("yt-dlp failed")
            wrapped.__cause__ = exc

        message = format_user_error(wrapped)

        self.assertIn("YouTube download failed", message)
        self.assertIn("format is no longer available", message)

    def test_ffmpeg_missing_has_packaging_hint(self) -> None:
        message = format_user_error(FileNotFoundError("ffmpeg was not found"))

        self.assertIn("ffmpeg was not found", message)
        self.assertIn("re-download", message)

    def test_permission_error_mentions_output_folder_and_security_software(self) -> None:
        message = format_user_error(PermissionError("Access is denied"))

        self.assertIn("Permission denied", message)
        self.assertIn("output folder", message)
        self.assertIn("security software", message)


if __name__ == "__main__":
    unittest.main()
