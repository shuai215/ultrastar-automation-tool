"""Tests for media conversion helpers.

媒体转换工具测试。
"""

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ultrastar_clone.core.converter import (
    YtDlpConverter,
    cleanup_partial_files,
    format_command_error,
    normalize_youtube_url,
    parse_ytdlp_percent,
    should_retry_with_stable_youtube_format,
)
from ultrastar_clone.models import SongMetadata, SongRequest


class FakeRunner:
    def __init__(self, returncode: int = 0, create_output: bool = True) -> None:
        self.returncode = returncode
        self.create_output = create_output
        self.commands = []

    def __call__(self, command, cwd=None):
        self.commands.append(command)
        if self.create_output:
            output_path = Path(command[command.index('-o') + 1])
            output_path.write_bytes(b'media')
        return subprocess.CompletedProcess(command, self.returncode, stdout='', stderr='boom' if self.returncode else '')


class RetryRunner:
    def __init__(self) -> None:
        self.commands = []

    def __call__(self, command, cwd=None):
        self.commands.append(command)
        if len(self.commands) == 1:
            return subprocess.CompletedProcess(command, 1, stdout='HTTP Error 403: Forbidden', stderr='')
        output_path = Path(command[command.index('-o') + 1])
        output_path.write_bytes(b'media')
        return subprocess.CompletedProcess(command, 0, stdout='', stderr='')


class ConverterTests(unittest.TestCase):
    def test_convert_mp3_builds_expected_command(self) -> None:
        runner = FakeRunner()
        converter = YtDlpConverter(yt_dlp_path='yt-dlp', ffmpeg_path='C:/ffmpeg/bin/ffmpeg.exe', runner=runner)

        with TemporaryDirectory() as temp_dir:
            path = converter.convert(
                SongRequest('Usher', 'U Remind Me', 'mp3'),
                SongMetadata('6131', 'https://youtube.test/watch?v=abc'),
                Path(temp_dir),
            )

        command = runner.commands[0]
        self.assertIn('-x', command)
        self.assertIn('--audio-format', command)
        self.assertIn('mp3', command)
        self.assertEqual(path.name, 'Usher - U Remind Me.mp3')

    def test_convert_mp4_builds_expected_command(self) -> None:
        runner = FakeRunner()
        converter = YtDlpConverter(yt_dlp_path='yt-dlp', ffmpeg_path='C:/ffmpeg/bin/ffmpeg.exe', runner=runner)

        with TemporaryDirectory() as temp_dir:
            path = converter.convert(
                SongRequest('Artist', 'Video Song', 'mp4'),
                SongMetadata('1', 'https://youtube.test/watch?v=abc'),
                Path(temp_dir),
            )

        command = runner.commands[0]
        self.assertIn('--merge-output-format', command)
        self.assertIn('mp4', command)
        self.assertIn('worst[ext=mp4][vcodec!=none]/18/worst[vcodec!=none]/worst', command)
        self.assertEqual(path.name, 'Artist - Video Song.mp4')

    def test_convert_can_use_browser_cookies(self) -> None:
        runner = FakeRunner()
        converter = YtDlpConverter(
            yt_dlp_path='yt-dlp',
            ffmpeg_path='C:/ffmpeg/bin/ffmpeg.exe',
            runner=runner,
            cookies_from_browser='chrome',
        )

        with TemporaryDirectory() as temp_dir:
            converter.convert(
                SongRequest('Artist', 'Video Song', 'mp4'),
                SongMetadata('1', 'https://youtube.test/watch?v=abc'),
                Path(temp_dir),
            )

        command = runner.commands[0]
        self.assertIn('--cookies-from-browser', command)
        self.assertIn('chrome', command)

    def test_convert_returns_none_without_youtube_url(self) -> None:
        runner = FakeRunner()
        converter = YtDlpConverter(yt_dlp_path='yt-dlp', ffmpeg_path='C:/ffmpeg/bin/ffmpeg.exe', runner=runner)

        with TemporaryDirectory() as temp_dir:
            result = converter.convert(SongRequest('A', 'B'), SongMetadata('1', None), Path(temp_dir))

        self.assertIsNone(result)
        self.assertEqual(runner.commands, [])

    def test_convert_raises_when_command_fails(self) -> None:
        runner = FakeRunner(returncode=1, create_output=False)
        converter = YtDlpConverter(yt_dlp_path='yt-dlp', ffmpeg_path='C:/ffmpeg/bin/ffmpeg.exe', runner=runner)

        with TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(RuntimeError, 'yt-dlp failed'):
                converter.convert(
                    SongRequest('A', 'B'),
                    SongMetadata('1', 'https://youtube.test/watch?v=abc'),
                    Path(temp_dir),
                )

    def test_format_command_error_uses_stderr(self) -> None:
        result = subprocess.CompletedProcess(['yt-dlp'], 1, stdout='out', stderr='err')

        self.assertIn('err', format_command_error(result))

    def test_format_command_error_explains_locked_browser_cookies(self) -> None:
        result = subprocess.CompletedProcess(
            ['yt-dlp'],
            1,
            stdout='',
            stderr='ERROR: Could not copy Chrome cookie database.',
        )

        error = format_command_error(result)

        self.assertIn('Close all Chrome/Edge windows', error)
        self.assertIn('Firefox cookies', error)

    def test_parse_ytdlp_percent(self) -> None:
        self.assertEqual(parse_ytdlp_percent('[download]  42.7% of 1.00MiB'), 42)
        self.assertEqual(parse_ytdlp_percent('[download] 100% of 1.00MiB'), 100)
        self.assertIsNone(parse_ytdlp_percent('[ffmpeg] Destination: file.mp3'))

    def test_retry_with_stable_format_after_403(self) -> None:
        runner = RetryRunner()
        converter = YtDlpConverter(yt_dlp_path='yt-dlp', ffmpeg_path='C:/ffmpeg/bin/ffmpeg.exe', runner=runner)

        with TemporaryDirectory() as temp_dir:
            path = converter.convert(
                SongRequest('Coldplay', 'Yellow', 'mp4'),
                SongMetadata('4698', 'https://www.youtube.com/embed/yKNxeF4KMsY'),
                Path(temp_dir),
            )

        self.assertEqual(path.name, 'Coldplay - Yellow.mp4')
        self.assertEqual(len(runner.commands), 2)
        self.assertIn('18', runner.commands[1][runner.commands[1].index('-f') + 1])
        self.assertIn('--extractor-args', runner.commands[1])
        self.assertIn('--remote-components', runner.commands[1])
        self.assertIn('ejs:github', runner.commands[1])
        self.assertIn('--js-runtimes', runner.commands[1])
        self.assertIn('node', runner.commands[1])

    def test_should_retry_with_stable_youtube_format(self) -> None:
        result = subprocess.CompletedProcess(['yt-dlp'], 1, stdout='HTTP Error 403: Forbidden', stderr='')

        self.assertTrue(should_retry_with_stable_youtube_format(result))

    def test_should_retry_when_youtube_formats_are_missing(self) -> None:
        result = subprocess.CompletedProcess(
            ['yt-dlp'],
            1,
            stdout='Only images are available for download. Requested format is not available.',
            stderr='',
        )

        self.assertTrue(should_retry_with_stable_youtube_format(result))

    def test_normalize_youtube_embed_url(self) -> None:
        self.assertEqual(
            normalize_youtube_url('https://www.youtube.com/embed/yKNxeF4KMsY'),
            'https://www.youtube.com/watch?v=yKNxeF4KMsY',
        )

    def test_cleanup_partial_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / 'Artist - Title.mp4'
            partial = Path(temp_dir) / 'Artist - Title.mp4.part'
            partial.write_text('partial', encoding='utf-8')

            cleanup_partial_files(output)

            self.assertFalse(partial.exists())


if __name__ == '__main__':
    unittest.main()

