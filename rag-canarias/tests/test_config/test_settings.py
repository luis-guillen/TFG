"""Tests para config/settings.py."""

import os
from pathlib import Path
from unittest.mock import patch

from config.settings import Settings, SourceConfig


class TestSettingsDefaults:
    """Tests para valores por defecto de Settings."""

    def setup_method(self):
        Settings.reset()

    def test_default_values(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
        assert settings.fetch_delay_seconds == 1.0
        assert settings.fetch_max_retries == 3
        assert settings.fetch_timeout_seconds == 30.0
        assert "RAG-Canarias" in settings.user_agent
        assert settings.data_dir == Path("data")
        assert settings.db_path == Path("data/rag_canarias.db")
        assert settings.chunk_max_tokens == 512
        assert settings.chunk_overlap_tokens == 64
        assert settings.log_level == "INFO"

    def test_respects_env_values(self):
        env = {
            "FETCH_DELAY_SECONDS": "2.5",
            "FETCH_MAX_RETRIES": "5",
            "FETCH_TIMEOUT_SECONDS": "60",
            "CHUNK_MAX_TOKENS": "256",
            "LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
        assert settings.fetch_delay_seconds == 2.5
        assert settings.fetch_max_retries == 5
        assert settings.fetch_timeout_seconds == 60.0
        assert settings.chunk_max_tokens == 256
        assert settings.log_level == "DEBUG"

    def test_singleton(self):
        Settings.reset()
        s1 = Settings.get()
        s2 = Settings.get()
        assert s1 is s2
        Settings.reset()


class TestLoadSources:
    """Tests para carga de sources.yaml."""

    def setup_method(self):
        Settings.reset()

    def test_load_sources(self):
        settings = Settings()
        sources = settings.load_sources()
        assert len(sources) == 6
        assert all(isinstance(s, SourceConfig) for s in sources)

    def test_memoria_lanzarote_config(self):
        settings = Settings()
        sources = settings.load_sources()
        ml = next(s for s in sources if s.id == "memoria_lanzarote")
        assert ml.name == "Memoria de Lanzarote"
        assert ml.base_url == "https://memoriadelanzarote.com/"
        assert ml.island == "Lanzarote"
        assert ml.status == "active"
        assert ml.discovery == "pagination"
        assert len(ml.content_selectors) > 0
        assert "documents_url" in ml.extra

    def test_pending_sources(self):
        settings = Settings()
        sources = settings.load_sources()
        pending = [s for s in sources if s.status == "pending"]
        assert len(pending) == 5
        Settings.reset()
