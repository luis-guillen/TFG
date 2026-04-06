"""Comprobación de robots.txt antes de descargar URLs.

Cachea el contenido de robots.txt por dominio para evitar
descargas repetidas durante el crawling.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from crawler.fetcher import FetchError, Fetcher

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Comprueba robots.txt antes de descargar URLs."""

    def __init__(self, fetcher: Fetcher) -> None:
        self._fetcher = fetcher
        self._cache: dict[str, RobotFileParser] = {}

    def is_allowed(self, url: str) -> bool:
        """Comprueba si la URL está permitida según robots.txt del dominio.

        Descarga robots.txt solo la primera vez por dominio.
        Si robots.txt no existe (404) o no se puede descargar, permite todo
        (fail-open) y loguea un warning.

        Args:
            url: URL a comprobar.

        Returns:
            True si la URL está permitida, False en caso contrario.
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._get_robots_parser(domain)
        return parser.can_fetch(self._fetcher._settings.user_agent, url)

    def _get_robots_parser(self, domain: str) -> RobotFileParser:
        """Obtiene el parser de robots.txt, descargándolo si es necesario.

        Args:
            domain: Dominio base (scheme + netloc).

        Returns:
            RobotFileParser configurado para el dominio.
        """
        if domain in self._cache:
            return self._cache[domain]

        robots_url = f"{domain}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            doc = self._fetcher.fetch(robots_url)
            if doc.status_code < 400:
                parser.parse(doc.html.splitlines())
            else:
                parser.allow_all = True
        except FetchError as e:
            if e.status_code == 404:
                logger.debug("robots.txt no encontrado en %s, permitiendo todo", domain)
            else:
                logger.warning(
                    "No se pudo descargar robots.txt de %s: %s", domain, e
                )
            parser.allow_all = True

        self._cache[domain] = parser
        return parser
