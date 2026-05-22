"""Tests for USDB txt downloading helpers.

USDB txt 下载工具测试。
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.core.downloader import (
    USDBTextDownloader,
    extract_txt_from_gettxt_html,
    extract_wait_seconds,
    verify_song_text,
)
from ultrastar_clone.models import SongMetadata, SongRequest


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def read(self) -> bytes:
        return self.text.encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeOpener:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.requests = []

    def open(self, request, timeout=20):
        self.requests.append(request)
        return FakeResponse(self.responses.pop(0))


class DownloaderTests(unittest.TestCase):
    def test_extract_wait_seconds(self) -> None:
        self.assertEqual(extract_wait_seconds('<script>time = 24;</script>'), 24)
        self.assertIsNone(extract_wait_seconds('<html>No wait</html>'))

    def test_extract_txt_from_gettxt_html(self) -> None:
        html = '''
        <textarea name="txt" rows=25 cols=92>#ARTIST:Usher&#13;&#10;#TITLE:U Remind Me&#13;&#10;#GENRE:R&amp;B&#13;&#10;E</textarea>
        '''

        text = extract_txt_from_gettxt_html(html)

        self.assertIn('#ARTIST:Usher', text)
        self.assertIn('#TITLE:U Remind Me', text)
        self.assertIn('#GENRE:R&B', text)
        self.assertTrue(text.endswith('\n'))

    def test_verify_song_text_rejects_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, 'metadata mismatch'):
            verify_song_text('#ARTIST:Other\n#TITLE:Song\n', SongRequest('Artist', 'Song'))

    def test_download_txt_saves_file(self) -> None:
        wait_html = '<script>time = 24;</script><form><input name="wd" value="1"></form>'
        txt_html = '<textarea name="txt">#ARTIST:Usher\n#TITLE:U Remind Me\n#GAP:4480\nE</textarea>'
        opener = FakeOpener([wait_html, txt_html])
        downloader = USDBTextDownloader(opener=opener, respect_wait=False)

        with TemporaryDirectory() as temp_dir:
            path = downloader.download_txt(
                SongRequest('Usher', 'U Remind Me'),
                SongMetadata('6131'),
                Path(temp_dir),
            )

            self.assertTrue(path.exists())
            self.assertEqual(path.name, 'Usher - U Remind Me.txt')
            self.assertIn('#GAP:4480', path.read_text(encoding='utf-8'))
            self.assertEqual(len(opener.requests), 2)


if __name__ == '__main__':
    unittest.main()

