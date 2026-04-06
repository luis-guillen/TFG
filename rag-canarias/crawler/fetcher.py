"""Cliente HTTP robusto con rate limiting y reintentos.

Proporciona descarga de páginas web con backoff exponencial,
respeto de rate limiting y manejo de errores transitorios.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from types import TracebackType

import httpx

from config.settings import Settings
from storage.models import RawDocument

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Error irrecuperable al descargar una URL."""

    def __init__(self, url: str, status_code: int | None, message: str):
        self.url = url
        self.status_code = status_code
        super().__init__(f"Error fetching {url}: {message}")


# Códigos HTTP que se consideran errores transitorios y se reintentan
_TRANSIENT_STATUS_CODES = frozenset({500, 502, 503, 504})


class Fetcher:
    """Cliente HTTP robusto con rate limiting y reintentos."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.Client(
            timeout=settings.fetch_timeout_seconds,
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "text/html",
                "Accept-Language": "es,en;q=0.5",
            },
            follow_redirects=True,
        )

    def fetch(self, url: str) -> RawDocument:
        """Descarga una URL y devuelve un RawDocument.

        Respeta rate limiting, reintenta errores transitorios con backoff
        exponencial y lanza FetchError para errores irrecuperables.

        Args:
            url: URL a descargar.

        Returns:
            RawDocument con el HTML descargado y metadatos de la respuesta.

        Raises:
            FetchError: si la descarga falla tras todos los reintentos.
        """
        last_error: Exception | None = None

        for attempt in range(self._settings.fetch_max_retries + 1):
            # Rate limiting: esperar antes de cada petición
            time.sleep(self._settings.fetch_delay_seconds)

            try:
                start = time.monotonic()
                response = self._client.get(url)
                elapsed = time.monotonic() - start

                logger.debug(
                    "GET %s -> %d (%.2fs)", url, response.status_code, elapsed
                )

                # Éxito
                if response.status_code < 400:
                    return RawDocument(
                        url=url,
                        html=response.text,
                        status_code=response.status_code,
                        fetched_at=datetime.now(timezone.utc),
                        headers=dict(response.headers),
                    )

                # 429 Too Many Requests
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait = float(retry_after)
                    else:
                        wait = self._settings.fetch_delay_seconds * 2
                    logger.warning(
                        "Rate limited en %s, esperando %.1fs", url, wait
                    )
                    time.sleep(wait)
                    last_error = FetchError(url, 429, "Too Many Requests")
                    continue

                # Error transitorio (5xx): reintentar con backoff
                if response.status_code in _TRANSIENT_STATUS_CODES:
                    backoff = 2**attempt
                    logger.warning(
                        "Error transitorio %d en %s, reintento %d/%d en %ds",
                        response.status_code,
                        url,
                        attempt + 1,
                        self._settings.fetch_max_retries,
                        backoff,
                    )
                    last_error = FetchError(
                        url, response.status_code,
                        f"HTTP {response.status_code}"
                    )
                    if attempt < self._settings.fetch_max_retries:
                        time.sleep(backoff)
                    continue

                # Error irrecuperable (4xx excepto 429)
                raise FetchError(
                    url, response.status_code,
                    f"HTTP {response.status_code}"
                )

            except httpx.TimeoutException:
                logger.warning("Timeout en %s, intento %d", url, attempt + 1)
                last_error = FetchError(url, None, "Timeout")
                if attempt < self._settings.fetch_max_retries:
                    time.sleep(2**attempt)
                continue

            except FetchError:
                raise

            except httpx.HTTPError as e:
                logger.warning("Error HTTP en %s: %s", url, e)
                last_error = FetchError(url, None, str(e))
                if attempt < self._settings.fetch_max_retries:
                    time.sleep(2**attempt)
                continue

        raise last_error  # type: ignore[misc]

    def fetch_many(
        self, urls: list[str], on_error: str = "skip"
    ) -> list[RawDocument]:
        """Descarga múltiples URLs secuencialmente, respetando rate limiting.

        Args:
            urls: Lista de URLs a descargar.
            on_error: "skip" para saltar errores y continuar, "raise" para abortar.

        Returns:
            Lista de RawDocuments descargados con éxito.
        """
        results: list[RawDocument] = []
        for url in urls:
            try:
                doc = self.fetch(url)
                results.append(doc)
            except FetchError:
                if on_error == "raise":
                    raise
                logger.warning("Saltando URL fallida: %s", url)
        return results

    def close(self) -> None:
        """Cierra el cliente HTTP."""
        self._client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
