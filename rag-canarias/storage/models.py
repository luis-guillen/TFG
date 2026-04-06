"""Modelos de dominio del sistema RAG Canarias.

Define las dataclasses que representan documentos en cada etapa
del pipeline: descarga, procesamiento y fragmentación.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Self
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

logger = logging.getLogger(__name__)

# Parámetros de tracking que se eliminan al canonicalizar URLs
_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source",
})


def canonicalize_url(url: str) -> str:
    """Normaliza URL: elimina fragmento, trailing slash y parámetros de tracking.

    Args:
        url: URL a normalizar.

    Returns:
        URL canónica sin fragmento, sin trailing slash inconsistente
        y sin parámetros de tracking.
    """
    parsed = urlparse(url)

    # Eliminar fragmento
    # Filtrar parámetros de tracking
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {
        k: v for k, v in query_params.items()
        if k.lower() not in _TRACKING_PARAMS
    }
    clean_query = urlencode(filtered, doseq=True)

    # Eliminar trailing slash del path (excepto si es solo "/")
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    canonical = urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        parsed.params,
        clean_query,
        "",  # sin fragmento
    ))
    return canonical


def generate_doc_id(source_id: str, url: str) -> str:
    """Genera ID determinista: SHA-256 de 'source_id|url_canónica'.

    Args:
        source_id: Identificador de la fuente de datos.
        url: URL del documento (se canonicaliza internamente).

    Returns:
        Hexdigest SHA-256 de 64 caracteres.
    """
    canonical = canonicalize_url(url)
    return hashlib.sha256(f"{source_id}|{canonical}".encode("utf-8")).hexdigest()


def generate_chunk_id(doc_id: str, chunk_index: int) -> str:
    """Genera ID determinista: SHA-256 de 'doc_id|chunk_index'.

    Args:
        doc_id: ID del documento padre.
        chunk_index: Índice ordinal del chunk.

    Returns:
        Hexdigest SHA-256 de 64 caracteres.
    """
    return hashlib.sha256(f"{doc_id}|{chunk_index}".encode("utf-8")).hexdigest()


def generate_content_hash(content: str) -> str:
    """SHA-256 del contenido para detección de cambios.

    Args:
        content: Texto del documento.

    Returns:
        Hexdigest SHA-256 de 64 caracteres.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class RawDocument:
    """Documento recién descargado, antes de cualquier procesamiento."""

    url: str
    html: str
    status_code: int
    fetched_at: datetime
    headers: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "url": self.url,
            "html": self.html,
            "status_code": self.status_code,
            "fetched_at": self.fetched_at.isoformat(),
            "headers": self.headers,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserializa desde diccionario."""
        return cls(
            url=data["url"],
            html=data["html"],
            status_code=data["status_code"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            headers=data["headers"],
        )


@dataclass
class Metadata:
    """Metadatos comunes de un documento procesado."""

    author: str | None = None
    published_date: str | None = None
    category: str | None = None
    island: str | None = None
    content_type: str = "article"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "author": self.author,
            "published_date": self.published_date,
            "category": self.category,
            "island": self.island,
            "content_type": self.content_type,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserializa desde diccionario."""
        return cls(
            author=data.get("author"),
            published_date=data.get("published_date"),
            category=data.get("category"),
            island=data.get("island"),
            content_type=data.get("content_type", "article"),
            extra=data.get("extra", {}),
        )


@dataclass
class ProcessedDocument:
    """Documento después de parsing, normalización y enriquecimiento."""

    doc_id: str
    source_id: str
    url: str
    title: str
    content: str
    content_hash: str
    language: str
    metadata: Metadata
    fetched_at: datetime
    processed_at: datetime
    connector_version: str

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "doc_id": self.doc_id,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "content_hash": self.content_hash,
            "language": self.language,
            "metadata": self.metadata.to_dict(),
            "fetched_at": self.fetched_at.isoformat(),
            "processed_at": self.processed_at.isoformat(),
            "connector_version": self.connector_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserializa desde diccionario."""
        return cls(
            doc_id=data["doc_id"],
            source_id=data["source_id"],
            url=data["url"],
            title=data["title"],
            content=data["content"],
            content_hash=data["content_hash"],
            language=data["language"],
            metadata=Metadata.from_dict(data["metadata"]),
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            processed_at=datetime.fromisoformat(data["processed_at"]),
            connector_version=data["connector_version"],
        )


@dataclass
class Chunk:
    """Fragmento de un documento, listo para indexación."""

    chunk_id: str
    doc_id: str
    chunk_index: int
    content: str
    token_count: int
    source_id: str
    url: str
    title: str
    island: str | None
    category: str | None
    content_type: str

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "token_count": self.token_count,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "island": self.island,
            "category": self.category,
            "content_type": self.content_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserializa desde diccionario."""
        return cls(
            chunk_id=data["chunk_id"],
            doc_id=data["doc_id"],
            chunk_index=data["chunk_index"],
            content=data["content"],
            token_count=data["token_count"],
            source_id=data["source_id"],
            url=data["url"],
            title=data["title"],
            island=data.get("island"),
            category=data.get("category"),
            content_type=data["content_type"],
        )
