"""Configuración central del sistema RAG Canarias.

Carga variables de entorno desde .env y proporciona valores por defecto.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Configuración de una fuente de datos."""

    id: str
    name: str
    base_url: str
    connector: str
    content_selectors: list[str]
    discovery: str
    island: str | None
    status: str = "active"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Crea una instancia desde un diccionario YAML."""
        return cls(
            id=data["id"],
            name=data["name"],
            base_url=data["base_url"],
            connector=data.get("connector", ""),
            content_selectors=data.get("content_selectors", []),
            discovery=data.get("discovery", ""),
            island=data.get("island"),
            status=data.get("status", "active"),
            extra=data.get("extra", {}),
        )


class Settings:
    """Configuración singleton del sistema.

    Carga valores desde variables de entorno (.env) con fallbacks sensatos.
    """

    _instance: Settings | None = None

    def __init__(self) -> None:
        load_dotenv()

        # Fetcher
        self.fetch_delay_seconds: float = float(
            os.getenv("FETCH_DELAY_SECONDS", "1.0")
        )
        self.fetch_max_retries: int = int(os.getenv("FETCH_MAX_RETRIES", "3"))
        self.fetch_timeout_seconds: float = float(
            os.getenv("FETCH_TIMEOUT_SECONDS", "30.0")
        )
        self.user_agent: str = os.getenv(
            "USER_AGENT", "RAG-Canarias-TFG/1.0 (Trabajo Fin de Grado)"
        )

        # Paths
        self.data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
        self.db_path: Path = Path(os.getenv("DB_PATH", "data/rag_canarias.db"))

        # Chunking
        self.chunk_max_tokens: int = int(os.getenv("CHUNK_MAX_TOKENS", "512"))
        self.chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "64"))

        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def get(cls) -> Settings:
        """Devuelve la instancia singleton de Settings."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reinicia el singleton (útil para tests)."""
        cls._instance = None

    def load_sources(self) -> list[SourceConfig]:
        """Carga y parsea la configuración de fuentes desde sources.yaml.

        Returns:
            Lista de SourceConfig con las fuentes definidas.
        """
        sources_path = Path(__file__).parent / "sources.yaml"
        with open(sources_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return [SourceConfig.from_dict(s) for s in data.get("sources", [])]
