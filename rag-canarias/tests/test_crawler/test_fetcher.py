"""Tests para crawler/fetcher.py."""

from unittest.mock import patch

import httpx
import pytest
import respx

from config.settings import Settings
from crawler.fetcher import FetchError, Fetcher


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
def fetcher(settings):
    """Fetcher configurado para tests."""
    with Fetcher(settings) as f:
        yield f


class TestFetchSuccess:
    """Tests para descargas exitosas."""

    @respx.mock
    def test_fetch_success(self, fetcher):
        respx.get("https://example.com/doc").mock(
            return_value=httpx.Response(200, text="<html>OK</html>")
        )
        doc = fetcher.fetch("https://example.com/doc")
        assert doc.status_code == 200
        assert doc.html == "<html>OK</html>"
        assert doc.url == "https://example.com/doc"
        assert doc.fetched_at is not None


class TestFetchErrors:
    """Tests para manejo de errores."""

    @respx.mock
    def test_fetch_404(self, fetcher):
        respx.get("https://example.com/missing").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(FetchError) as exc_info:
            fetcher.fetch("https://example.com/missing")
        assert exc_info.value.status_code == 404

    @respx.mock
    def test_fetch_retry_on_500(self, fetcher):
        route = respx.get("https://example.com/flaky")
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(200, text="<html>OK</html>"),
        ]
        doc = fetcher.fetch("https://example.com/flaky")
        assert doc.status_code == 200
        assert route.call_count == 2

    @respx.mock
    def test_fetch_max_retries_exceeded(self, fetcher):
        respx.get("https://example.com/down").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(FetchError) as exc_info:
            fetcher.fetch("https://example.com/down")
        assert exc_info.value.status_code == 500

    @respx.mock
    def test_fetch_timeout(self, fetcher):
        respx.get("https://example.com/slow").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )
        with pytest.raises(FetchError) as exc_info:
            fetcher.fetch("https://example.com/slow")
        assert exc_info.value.status_code is None
        assert "Timeout" in str(exc_info.value)


class TestFetchMany:
    """Tests para descarga múltiple."""

    @respx.mock
    def test_fetch_many_skips_errors(self, fetcher):
        respx.get("https://example.com/ok1").mock(
            return_value=httpx.Response(200, text="<html>1</html>")
        )
        respx.get("https://example.com/fail").mock(
            return_value=httpx.Response(404)
        )
        respx.get("https://example.com/ok2").mock(
            return_value=httpx.Response(200, text="<html>2</html>")
        )
        results = fetcher.fetch_many(
            ["https://example.com/ok1", "https://example.com/fail", "https://example.com/ok2"],
            on_error="skip",
        )
        assert len(results) == 2
        assert results[0].html == "<html>1</html>"
        assert results[1].html == "<html>2</html>"


class TestRateLimiting:
    """Tests para rate limiting."""

    @respx.mock
    def test_rate_limiting_sleeps(self, settings):
        settings.fetch_delay_seconds = 0.5
        respx.get("https://example.com/a").mock(
            return_value=httpx.Response(200, text="ok")
        )
        with patch("crawler.fetcher.time.sleep") as mock_sleep:
            with Fetcher(settings) as f:
                f.fetch("https://example.com/a")
            mock_sleep.assert_called_with(0.5)
