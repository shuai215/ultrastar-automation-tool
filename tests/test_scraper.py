"""Tests for USDB parsing helpers.

USDB 解析工具测试。
"""

import unittest

from ultrastar_clone.core.scraper import (
    SearchCandidate,
    choose_exact_candidate,
    extract_song_id_from_url,
    extract_youtube_url,
    parse_search_candidates,
)
from ultrastar_clone.models import SongRequest


class ScraperParsingTests(unittest.TestCase):
    def test_extract_song_id_from_url(self) -> None:
        self.assertEqual(extract_song_id_from_url('?link=detail&id=6131'), '6131')
        self.assertEqual(extract_song_id_from_url('https://usdb.animux.de/?link=detail&songid=42'), '42')

    def test_parse_table_candidates_from_usdb_rows(self) -> None:
        html = """
        <tr class="list_tr2" data-songid="6131">
          <td onclick="show_detail(6131)">Usher</td>
          <td onclick="show_detail(6131)"><a href="?link=detail&id=6131">U Remind Me</td>
          <td onclick="show_detail(6131)">R&amp;B</td>
        </tr>
        """

        candidates = parse_search_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].song_id, '6131')
        self.assertEqual(candidates[0].artist, 'Usher')
        self.assertEqual(candidates[0].title, 'U Remind Me')
        self.assertTrue(candidates[0].url.endswith('?link=detail&id=6131'))

    def test_parse_link_candidates_fallback(self) -> None:
        html = """
        <a href='?link=detail&id=6131'>Usher - U Remind Me</a>
        <a href='?link=detail&id=7741'>Taylor Swift - Change</a>
        """

        candidates = parse_search_candidates(html)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].artist, 'Usher')
        self.assertEqual(candidates[0].title, 'U Remind Me')

    def test_choose_exact_candidate_normalizes_accents(self) -> None:
        candidates = [
            SearchCandidate('1', 'Beyonce', 'Crazy in Love', 'https://example.test/1'),
        ]

        match = choose_exact_candidate(candidates, SongRequest('Beyoncé', 'Crazy in Love'))

        self.assertIsNotNone(match)
        self.assertEqual(match.song_id, '1')

    def test_extract_youtube_url_from_iframe(self) -> None:
        html = '<iframe src="https://www.youtube.com/embed/abc123"></iframe>'

        self.assertEqual(extract_youtube_url(html), 'https://www.youtube.com/embed/abc123')


if __name__ == '__main__':
    unittest.main()

