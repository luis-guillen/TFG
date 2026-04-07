"""Tests de integración para MemoriaLanzaroteConnector.

Estos tests conectan con el sitio web real para verificar que
la abstracción y extracción siguen funcionando ante cambios en el HTML.
Por defecto deberían ejecutarse solo cuando se indique explícitamente.
"""

import pytest
import os
from config.settings import Settings, SourceConfig
from crawler.fetcher import Fetcher
from crawler.robots import RobotsChecker
from connectors.memoria_lanzarote import MemoriaLanzaroteConnector

# Marca para identificar tests de integración
pytestmark = pytest.mark.integration


@pytest.fixture
def real_connector():
    settings = Settings()
    all_sources = settings.load_sources()
    
    # Intentar obtener de sources.yaml, o crear un dummy config si no existe
    source_config = next((s for s in all_sources if s.id == "memoria_lanzarote"), None)
    if not source_config:
        source_config = SourceConfig(
            id="memoria_lanzarote",
            name="Memoria",
            base_url="https://memoriadelanzarote.com",
            connector="MemoriaLanzaroteConnector",
            content_selectors=["article", ".entry-content"],
            discovery="sitemap",
            island="Lanzarote"
        )
        
    fetcher = Fetcher(settings)
    robots = RobotsChecker(fetcher)
    
    connector = MemoriaLanzaroteConnector(source_config, settings, fetcher, robots)
    yield connector
    fetcher.close()


def test_discover_urls_real(real_connector):
    """Verifica que el descubrimiento mediante la API JSON sigue funcionando."""
    urls = real_connector.discover_urls(limit=5)
    
    assert len(urls) > 0, "No se extrajo ninguna URL."
    assert len(urls) <= 5, "Se extrajeron más URLs del límite permitido."
    for url in urls:
        assert url.startswith("https://memoriadelanzarote.com/item/"), f"URL inesperada: {url}"


def test_full_crawl_single_document(real_connector):
    """Descarga documentos reales y comprueba toda la extracción."""
    urls = real_connector.discover_urls(limit=20)
    if not urls:
        pytest.skip("No se han podido descubrir URLs para la prueba.")
        
    crawl_config = real_connector.get_crawl_config()
    
    found_valid = False
    for url_to_test in urls:
        raw_doc = real_connector.fetcher.fetch(url_to_test, **crawl_config)
        
        assert raw_doc.status_code == 200, f"Error HTTP al descargar {url_to_test}"
        assert raw_doc.html, "El HTML devuelto está vacío."
        
        doc = real_connector.parse_document(raw_doc)
        
        if doc is not None:
            assert doc.url == url_to_test
            assert doc.title.strip() != "", "No se extrajo título del documento."
            assert len(doc.content.strip()) > 50, "El contenido parece inválido o vacío."
            assert doc.metadata.island == "Lanzarote"
            found_valid = True
            break
            
    if not found_valid:
        pytest.skip("Se descartaron todos los 20 documentos probados por ser solo imágenes/PDFs sin texto. Test saltado pacíficamente.")
