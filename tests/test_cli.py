"""Tests for the command-line entry point.

命令行入口测试。
"""

import os
import unittest
from unittest.mock import patch

from ultrastar_clone.cli import build_parser, main


class CliTests(unittest.TestCase):
    def test_parser_accepts_minimal_args(self) -> None:
        args = build_parser().parse_args(['--artist', 'Usher', '--title', 'U Remind Me'])

        self.assertEqual(args.artist, 'Usher')
        self.assertEqual(args.title, 'U Remind Me')
        self.assertEqual(args.format, 'mp3')
        self.assertFalse(args.skip_media)

    def test_main_requires_credentials(self) -> None:
        env = {key: value for key, value in os.environ.items() if key not in {'USDB_USER', 'USDB_PASS'}}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                main(['--artist', 'Usher', '--title', 'U Remind Me', '--skip-media'])


if __name__ == '__main__':
    unittest.main()

