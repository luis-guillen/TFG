"""Tests para clase abstracta BaseConnector."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from connectors.base import BaseConnector
from config.settings import Settings, SourceConfig
from crawler.fetcher import Fetcher
from crawler.robots import RobotsChecker
from storage.models import RawDocument, Metadata, ProcessedDocument


class DummyConnector(BaseConnector):
    VERSION = "1.0"
    
    def discover_urls(self, limit=None):
        return ["https://example.com/1", "https://example.com/2"]
        
    def get_crawl_config(self):
        return {"css_selector": "article"}
        
    def extract_metadata(self, raw_doc):
        return Metadata(island="Dummy")
        
    def extract_title(self, raw_doc):
        return "Dummy Title"
        
    def extract_content(self, raw_doc):
        # Allow returning empty content if testing
        return "Dummy content that is long enough to pass the 50 char check " * 2 if "short" not in raw_doc.url else "short"


@pytest.fixture
def dummy_deps():
    settings = Settings()
    source_config = SourceConfig(id="dummy_source", name="Dummy", base_url="https://example.com", connector="DummyConnector", content_selectors=["article"], discovery="sitemap", island="Dummy")
    fetcher = MagicMock(spec=Fetcher)
    robots_checker = MagicMock(spec=RobotsChecker)
    return source_config, settings, fetcher, robots_checker


def test_base_connector_cannot_be_instantiated(dummy_deps):
    with pytest.raises(TypeError):
        BaseConnector(*dummy_deps)


def test_concrete_connector_must_implement_abstracts():
    class IncompleteConnector(BaseConnector):
        def discover_urls(self, limit=None):
            return []
            
    with pytest.raises(TypeError):
        IncompleteConnector(None, None, None, None)


def test_parse_document_produces_valid_processed_doc(dummy_deps):
    connector = DummyConnector(*dummy_deps)
    raw_doc = RawDocument(
        url="https://example.com/valid",
        html="<html></html>",
        status_code=200,
        fetched_at=datetime.now(timezone.utc),
        headers={}
    )
    doc = connector.parse_document(raw_doc)
    assert doc is not None
    assert isinstance(doc, ProcessedDocument)
    assert doc.title == "Dummy Title"
    assert doc.source_id == "dummy_source"
    assert doc.metadata.island == "Dummy"
    assert len(doc.content) > 50


def test_parse_document_discards_empty_content(dummy_deps):
    connector = DummyConnector(*dummy_deps)
    raw_doc = RawDocument(
        url="https://example.com/short",
        html="<html></html>",
        status_code=200,
        fetched_at=datetime.now(timezone.utc),
        headers={}
    )
    doc = connector.parse_document(raw_doc)
    assert doc is None


def test_run_filters_by_robots_txt(dummy_deps):
    source_config, settings, fetcher, robots_checker = dummy_deps
    # Only allow the first url
    robots_checker.is_allowed.side_effect = lambda url: "1" in url
    
    # Mock fetcher to return valid docs
    raw_doc = RawDocument(
        url="https://example.com/1", html="long content long content long content long content long content", status_code=200, fetched_at=datetime.now(timezone.utc), headers={}
    )
    fetcher.fetch.return_value = raw_doc
    
    connector = DummyConnector(*dummy_deps)
    results = list(connector.run())
    
    assert len(results) == 1
    assert results[0].url == "https://example.com/1"
    fetcher.fetch.assert_called_once_with("https://example.com/1", css_selector="article")


def test_run_continues_on_error(dummy_deps):
    source_config, settings, fetcher, robots_checker = dummy_deps
    robots_checker.is_allowed.return_value = True
    
    def fetch_mock(url, **kwargs):
        if "1" in url:
            raise Exception("Fetch failed")
        return RawDocument(
            url=url, html="long content long content long content long content long content", status_code=200, fetched_at=datetime.now(timezone.utc), headers={}
        )
        
    fetcher.fetch.side_effect = fetch_mock
    
    connector = DummyConnector(*dummy_deps)
    results = list(connector.run())
    
    assert len(results) == 1
    assert results[0].url == "https://example.com/2"
