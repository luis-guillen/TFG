"""Tests para crawler/robots.py."""

import httpx
import respx

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

    @respx.mock
    def test_allowed_when_no_restrictions(self):
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
        )
        with _make_fetcher() as fetcher:
            checker = RobotsChecker(fetcher)
            assert checker.is_allowed("https://example.com/documentos") is True
            assert checker.is_allowed("https://example.com/admin") is True

    @respx.mock
    def test_disallowed_path(self):
        robots_txt = "User-agent: *\nDisallow: /admin/\n"
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=robots_txt)
        )
        with _make_fetcher() as fetcher:
            checker = RobotsChecker(fetcher)
            assert checker.is_allowed("https://example.com/admin/config") is False
            assert checker.is_allowed("https://example.com/documentos") is True

    @respx.mock
    def test_robots_not_found(self):
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(404)
        )
        with _make_fetcher() as fetcher:
            checker = RobotsChecker(fetcher)
            assert checker.is_allowed("https://example.com/anything") is True

    @respx.mock
    def test_caching(self):
        route = respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
        )
        with _make_fetcher() as fetcher:
            checker = RobotsChecker(fetcher)
            checker.is_allowed("https://example.com/page1")
            checker.is_allowed("https://example.com/page2")
            assert route.call_count == 1
