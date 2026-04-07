"""Tests para MemoriaLanzaroteConnector."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from config.settings import SourceConfig, Settings
from storage.models import RawDocument
from connectors.memoria_lanzarote import MemoriaLanzaroteConnector

@pytest.fixture
def dummy_deps():
    settings = Settings()
    source_config = SourceConfig(id="memoria_lanzarote", name="Memoria", base_url="https://memoriadelanzarote.com", connector="MemoriaLanzaroteConnector", content_selectors=["article"], discovery="sitemap", island="Lanzarote")
    fetcher = MagicMock()
    robots_checker = MagicMock()
    return source_config, settings, fetcher, robots_checker

def test_extract_title_from_fixture(dummy_deps):
    connector = MemoriaLanzaroteConnector(*dummy_deps)
    html = "<html><head><title>Título de prueba</title></head><body><h1>Título Principal</h1></body></html>"
    raw_doc = RawDocument(url="https://memoriadelanzarote.com/item/1", html=html, status_code=200, fetched_at=datetime.now(timezone.utc), headers={})
    raw_doc.markdown_raw = "# Título Principal\n\nContenido"
    
    title = connector.extract_title(raw_doc)
    assert title == "Título Principal"

def test_extract_content_from_fixture(dummy_deps):
    connector = MemoriaLanzaroteConnector(*dummy_deps)
    raw_doc = RawDocument(url="https://memoriadelanzarote.com/item/1", html="<html></html>", status_code=200, fetched_at=datetime.now(timezone.utc), headers={})
    raw_doc.markdown_raw = "Contenido raw\n\n[Volver](/)"
    raw_doc.markdown_fit = "Contenido fit\n\nTexto adicional."
    
    content = connector.extract_content(raw_doc)
    assert "Contenido fit" in content
    assert "Volver" not in content

def test_extract_metadata_from_fixture(dummy_deps):
    connector = MemoriaLanzaroteConnector(*dummy_deps)
    html = '''
    <html>
        <body>
            <p>AUTOR: Pedro Pérez</p>
            <div>FECHA: 1980</div>
            <ul class="breadcrumb"><li>Inicio</li><li>Textos</li><li>Item</li></ul>
        </body>
    </html>
    '''
    raw_doc = RawDocument(url="https://memoriadelanzarote.com/item/1", html=html, status_code=200, fetched_at=datetime.now(timezone.utc), headers={})
    
    meta = connector.extract_metadata(raw_doc)
    assert meta.island == "Lanzarote"
    assert meta.author == "Pedro Pérez"
    assert meta.published_date == "1980"
    assert meta.category == "Textos"

def test_parse_document_from_fixture(dummy_deps):
    connector = MemoriaLanzaroteConnector(*dummy_deps)
    html = "<html><body><h1>Doc 1</h1><p>Contenido largo para pasar el umbral que se necesita en el extractor. Content content content.</p></body></html>"
    raw_doc = RawDocument(url="https://memoriadelanzarote.com/item/1", html=html, status_code=200, fetched_at=datetime.now(timezone.utc), headers={})
    raw_doc.markdown_raw = "# Doc 1\n\nContenido largo para pasar el umbral que se necesita en el extractor. Content content content."
    raw_doc.markdown_fit = raw_doc.markdown_raw
    
    doc = connector.parse_document(raw_doc)
    assert doc is not None
    assert doc.title == "Doc 1"
    assert doc.source_id == "memoria_lanzarote"
    
def test_get_crawl_config_returns_valid_dict(dummy_deps):
    connector = MemoriaLanzaroteConnector(*dummy_deps)
    config = connector.get_crawl_config()
    assert "css_selector" in config
    assert "excluded_tags" in config
    assert "word_count_threshold" in config
