"""Tests para crawler/fetcher.py sustituyendo httpx por mocks de crawl4ai."""

from unittest.mock import AsyncMock, patch, MagicMock
import time

import pytest

from config.settings import Settings
from crawler.fetcher import FetchError, Fetcher
from crawl4ai import CrawlResult


@pytest.fixture
def settings():
    """Settings con delays mínimos para tests rápidos."""
    s = Settings()
    s.fetch_delay_seconds = 0.0
    s.fetch_max_retries = 3
    s.fetch_timeout_seconds = 5.0
    s.user_agent = "Test/1.0"
    return s


@pytest.fixture
def mock_crawler_class():
    with patch("crawler.fetcher.AsyncWebCrawler") as mock_class:
        mock_crawler = AsyncMock()
        mock_class.return_value = mock_crawler
        yield mock_class


@pytest.fixture
def fetcher(settings, mock_crawler_class):
    """Fetcher configurado para tests con el crawler mockeado."""
    with Fetcher(settings) as f:
        yield f


class TestFetchSuccess:
    """Tests para descargas exitosas."""

    def test_fetch_success(self, fetcher, mock_crawler_class):
        mock_result = CrawlResult(
            url="https://example.com/doc",
            html="<html>OK</html>",
            success=True,
            status_code=200,
        )
        mock_result.markdown = MagicMock(raw_markdown="# OK", fit_markdown="# OK Fit")
        mock_crawler = mock_crawler_class.return_value
        mock_crawler.arun.return_value = mock_result

        doc = fetcher.fetch("https://example.com/doc")
        
        assert doc.status_code == 200
        assert doc.html == "<html>OK</html>"
        assert doc.url == "https://example.com/doc"
        assert doc.fetched_at is not None
        assert doc.markdown_raw == "# OK"
        assert doc.markdown_fit == "# OK Fit"


class TestFetchErrors:
    """Tests para manejo de errores."""

    def test_fetch_failure(self, fetcher, mock_crawler_class):
        mock_result = CrawlResult(
            url="https://example.com/missing",
            html="",
            success=False,
            status_code=404,
            error_message="Not Found"
        )
        mock_crawler = mock_crawler_class.return_value
        mock_crawler.arun.return_value = mock_result

        with pytest.raises(FetchError) as exc_info:
            fetcher.fetch("https://example.com/missing")
        assert exc_info.value.status_code == 404

    def test_fetch_retry_on_500(self, fetcher, mock_crawler_class):
        fail_result = CrawlResult(url="https://example.com/flaky", html="", success=False, status_code=500, error_message="")
        success_result = CrawlResult(url="https://example.com/flaky", html="<html>OK</html>", success=True, status_code=200)
        
        mock_crawler = mock_crawler_class.return_value
        mock_crawler.arun.side_effect = [fail_result, success_result]

        doc = fetcher.fetch("https://example.com/flaky")
        assert doc.status_code == 200
        assert mock_crawler.arun.call_count == 2

    def test_fetch_max_retries_exceeded(self, fetcher, mock_crawler_class):
        fail_result = CrawlResult(url="https://example.com/down", html="", success=False, status_code=500, error_message="Error")
        mock_crawler = mock_crawler_class.return_value
        mock_crawler.arun.return_value = fail_result

        with pytest.raises(FetchError) as exc_info:
            fetcher.fetch("https://example.com/down")
        assert exc_info.value.status_code == 500


class TestFetchMany:
    """Tests para descarga múltiple."""

    def test_fetch_many_skips_errors(self, fetcher, mock_crawler_class):
        res1 = CrawlResult(url="https://example.com/ok1", html="<html>1</html>", success=True, status_code=200)
        res_fail = CrawlResult(url="https://example.com/fail", html="", success=False, status_code=404, error_message="")
        res2 = CrawlResult(url="https://example.com/ok2", html="<html>2</html>", success=True, status_code=200)

        mock_crawler = mock_crawler_class.return_value
        mock_crawler.arun.side_effect = [res1, res_fail, res2]

        results = fetcher.fetch_many(
            ["https://example.com/ok1", "https://example.com/fail", "https://example.com/ok2"],
            on_error="skip",
        )
        assert len(results) == 2
        assert results[0].html == "<html>1</html>"
        assert results[1].html == "<html>2</html>"


class TestRateLimiting:
    """Tests para rate limiting."""

    def test_rate_limiting_sleeps(self, settings, mock_crawler_class):
        settings.fetch_delay_seconds = 0.5
        mock_result = CrawlResult(url="https://example.com/a", html="ok", success=True, status_code=200)
        mock_crawler = mock_crawler_class.return_value
        mock_crawler.arun.return_value = mock_result

        with patch("crawler.fetcher.time.sleep") as mock_sleep, patch("crawler.fetcher.time.time", side_effect=[0.0, 0.0, 0.0]):
            with Fetcher(settings) as f:
                f._last_fetch_time = 0.0
                f.fetch("https://example.com/a")
            mock_sleep.assert_called_with(0.5)

    def test_run_config_overrides(self, fetcher, mock_crawler_class):
        mock_result = CrawlResult(url="https://example.com/b", html="ok", success=True, status_code=200)
        mock_crawler = mock_crawler_class.return_value
        mock_crawler.arun.return_value = mock_result

        fetcher.fetch("https://example.com/b", css_selector=".content", word_count_threshold=20)
        
        args, kwargs = mock_crawler.arun.call_args
        run_config = kwargs["config"]
        assert run_config is not None
        assert kwargs["url"] == "https://example.com/b"
