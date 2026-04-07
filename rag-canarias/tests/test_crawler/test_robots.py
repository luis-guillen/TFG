"""Tests para crawler/robots.py (ahora usa urllib.request)."""

from unittest.mock import patch, MagicMock
import urllib.error

from config.settings import Settings
from crawler.fetcher import Fetcher
from crawler.robots import RobotsChecker


def _make_fetcher() -> Fetcher:
    """Crea un Fetcher con configuración mínima para tests."""
    s = Settings()
    s.fetch_delay_seconds = 0.0
    s.fetch_max_retries = 0
    s.fetch_timeout_seconds = 5.0
    s.user_agent = "TestBot/1.0"
    return Fetcher(s)


class TestRobotsChecker:
    """Tests para RobotsChecker."""

    @patch("urllib.request.urlopen")
    def test_allowed_when_no_restrictions(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"User-agent: *\nAllow: /\n"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with _make_fetcher() as fetcher:
            checker = RobotsChecker(fetcher)
            assert checker.is_allowed("https://example.com/documentos") is True
            assert checker.is_allowed("https://example.com/admin") is True

    @patch("urllib.request.urlopen")
    def test_disallowed_path(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"User-agent: *\nDisallow: /admin/\n"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with _make_fetcher() as fetcher:
            checker = RobotsChecker(fetcher)
            assert checker.is_allowed("https://example.com/admin/config") is False
            assert checker.is_allowed("https://example.com/documentos") is True

    @patch("urllib.request.urlopen")
    def test_robots_not_found(self, mock_urlopen):
        # 404 HTTP Error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com/robots.txt", 404, "Not Found", {}, None
        )

        with _make_fetcher() as fetcher:
            checker = RobotsChecker(fetcher)
            assert checker.is_allowed("https://example.com/anything") is True

    @patch("urllib.request.urlopen")
    def test_caching(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"User-agent: *\nAllow: /\n"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with _make_fetcher() as fetcher:
            checker = RobotsChecker(fetcher)
            checker.is_allowed("https://example.com/page1")
            checker.is_allowed("https://example.com/page2")
            assert mock_urlopen.call_count == 1
