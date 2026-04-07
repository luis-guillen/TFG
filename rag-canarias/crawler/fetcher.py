"""Módulo de descarga web basado en crawl4ai.

Proporciona un wrapper síncrono sobre AsyncWebCrawler de crawl4ai
para mantener la interfaz simple del proyecto.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import nest_asyncio
from crawl4ai import AsyncWebCrawler, CrawlResult as C4AResult
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode

from config.settings import Settings
from storage.models import RawDocument

# Aplicar nest_asyncio para permitir loops anidados o reutilización del loop
nest_asyncio.apply()

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Error irrecuperable al descargar una URL."""
    def __init__(self, url: str, status_code: int | None, message: str):
        self.url = url
        self.status_code = status_code
        super().__init__(f"Error fetching {url}: {message}")


class Fetcher:
    """Cliente de crawling basado en crawl4ai.
    
    Envuelve AsyncWebCrawler en una interfaz síncrona.
    Soporta renderizado JavaScript, rate limiting y reintentos.
    """
    
    def __init__(self, settings: Settings):
        """Inicializa el Fetcher con la configuración del proyecto.
        
        Args:
            settings: Configuración global del proyecto.
        """
        self.settings = settings
        self._browser_config = BrowserConfig(
            headless=True,
            user_agent=settings.user_agent,
            verbose=False,
        )
        self._last_fetch_time: float = 0.0
        self._crawler: AsyncWebCrawler | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def _get_run_config(self, **overrides) -> CrawlerRunConfig:
        """Crea la configuración de ejecución para un crawl.
        
        Args:
            **overrides: Parámetros adicionales para CrawlerRunConfig.
                Permite a los conectores personalizar css_selector,
                excluded_tags, word_count_threshold, etc.
        
        Returns:
            CrawlerRunConfig configurado.
        """
        defaults = {
            "cache_mode": CacheMode.BYPASS,
            "word_count_threshold": 5,
            "excluded_tags": ["nav", "footer", "header", "aside"],
            "exclude_external_links": False,
            "process_iframes": False,
            "remove_overlay_elements": True,
        }
        defaults.update(overrides)
        return CrawlerRunConfig(**defaults)
    
    def _rate_limit(self):
        """Aplica rate limiting entre peticiones."""
        elapsed = time.time() - self._last_fetch_time
        if elapsed < self.settings.fetch_delay_seconds:
            time.sleep(self.settings.fetch_delay_seconds - elapsed)
        self._last_fetch_time = time.time()

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Obtiene o crea un event loop de asyncio."""
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    async def _start_crawler_if_needed(self):
        if self._crawler is None:
            self._crawler = AsyncWebCrawler(config=self._browser_config)
            await self._crawler.start()

    async def _async_fetch(self, url: str, run_config: CrawlerRunConfig) -> C4AResult:
        """Ejecuta un crawl asíncrono con reintentos."""
        await self._start_crawler_if_needed()
        assert self._crawler is not None
        
        last_error = None
        for attempt in range(self.settings.fetch_max_retries + 1):
            try:
                result = await self._crawler.arun(url=url, config=run_config)
                if result.success:
                    return result
                
                status_code = result.status_code
                
                if status_code == 429:
                    wait = self.settings.fetch_delay_seconds * 2
                    logger.warning("Rate limited en %s, esperando %.1fs", url, wait)
                    time.sleep(wait)
                    last_error = FetchError(url, 429, "Too Many Requests")
                    continue
                
                if status_code and status_code in {500, 502, 503, 504}:
                    backoff = 2**attempt
                    logger.warning(
                        "Error transitorio %s en %s, reintento %d/%d en %ds",
                        status_code, url, attempt + 1, self.settings.fetch_max_retries, backoff
                    )
                    last_error = FetchError(url, status_code, f"HTTP {status_code}")
                    if attempt < self.settings.fetch_max_retries:
                        time.sleep(backoff)
                    continue
                
                raise FetchError(url, status_code, result.error_message or "Unknown error")
                
            except Exception as e:
                if isinstance(e, FetchError):
                    raise
                
                logger.warning("Error en %s: %s", url, e)
                last_error = FetchError(url, None, str(e))
                if attempt < self.settings.fetch_max_retries:
                    time.sleep(2**attempt)
                continue
                
        raise last_error  # type: ignore[misc]
    
    def fetch(self, url: str, **run_config_overrides) -> RawDocument:
        """Descarga una URL y devuelve un RawDocument.
        
        Renderiza JavaScript automáticamente vía Playwright.
        Aplica rate limiting entre peticiones consecutivas.
        Reintenta hasta max_retries veces para errores transitorios.
        
        Args:
            url: URL a descargar.
            **run_config_overrides: Parámetros opcionales para CrawlerRunConfig.
                Los conectores pueden pasar css_selector, excluded_tags, etc.
        
        Returns:
            RawDocument con el HTML renderizado.
            
        Raises:
            FetchError: si la descarga falla tras todos los reintentos.
        """
        self._rate_limit()
        run_config = self._get_run_config(**run_config_overrides)
        
        loop = self._get_loop()
        result = loop.run_until_complete(self._async_fetch(url, run_config))
        
        markdown_raw = None
        markdown_fit = None
        if result.markdown:
            if hasattr(result.markdown, 'raw_markdown'):
                markdown_raw = result.markdown.raw_markdown
            if hasattr(result.markdown, 'fit_markdown'):
                markdown_fit = result.markdown.fit_markdown
                
        headers = {}
        headers["content-type"] = "text/html"

        return RawDocument(
            url=url,
            html=result.html,
            status_code=result.status_code if result.status_code else 200,
            fetched_at=datetime.now(timezone.utc),
            headers=headers,
            markdown_raw=markdown_raw,
            markdown_fit=markdown_fit,
            links=result.links,
            media=result.media,
            extracted_content=result.extracted_content
        )

    def fetch_many(self, urls: list[str], on_error: str = "skip",
                   **run_config_overrides) -> list[RawDocument]:
        """Descarga múltiples URLs secuencialmente con rate limiting.
        
        Args:
            urls: Lista de URLs a descargar.
            on_error: "skip" para saltar errores, "raise" para abortar.
            **run_config_overrides: Parámetros para CrawlerRunConfig.
            
        Returns:
            Lista de RawDocuments descargados con éxito.
        """
        results = []
        for url in urls:
            try:
                doc = self.fetch(url, **run_config_overrides)
                results.append(doc)
            except FetchError:
                if on_error == "raise":
                    raise
                logger.warning("Saltando URL fallida: %s", url)
        return results

    def close(self):
        """Cierra el crawler y libera recursos de Playwright."""
        if self._crawler is not None:
            loop = self._get_loop()
            loop.run_until_complete(self._crawler.close())
            self._crawler = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
