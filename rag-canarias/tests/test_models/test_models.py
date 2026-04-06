"""Tests para storage/models.py."""

from datetime import datetime, timezone

from storage.models import (
    Chunk,
    Metadata,
    ProcessedDocument,
    RawDocument,
    canonicalize_url,
    generate_chunk_id,
    generate_content_hash,
    generate_doc_id,
)


class TestCanonicalizeUrl:
    """Tests para la normalización de URLs."""

    def test_remove_fragment(self):
        url = "https://example.com/doc#section-2"
        assert canonicalize_url(url) == "https://example.com/doc"

    def test_remove_trailing_slash(self):
        url = "https://example.com/documentos/"
        assert canonicalize_url(url) == "https://example.com/documentos"

    def test_keep_root_slash(self):
        url = "https://example.com/"
        assert canonicalize_url(url) == "https://example.com/"

    def test_remove_utm_params(self):
        url = "https://example.com/doc?utm_source=twitter&utm_medium=social&id=42"
        result = canonicalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=42" in result

    def test_remove_fbclid(self):
        url = "https://example.com/doc?fbclid=abc123"
        assert canonicalize_url(url) == "https://example.com/doc"

    def test_combined(self):
        url = "https://memoriadelanzarote.com/doc/123/?utm_campaign=test#intro"
        result = canonicalize_url(url)
        assert result == "https://memoriadelanzarote.com/doc/123"


class TestGenerateDocId:
    """Tests para generación de IDs de documentos."""

    def test_deterministic(self):
        id1 = generate_doc_id("memoria_lanzarote", "https://example.com/doc/1")
        id2 = generate_doc_id("memoria_lanzarote", "https://example.com/doc/1")
        assert id1 == id2

    def test_different_urls_different_ids(self):
        id1 = generate_doc_id("memoria_lanzarote", "https://example.com/doc/1")
        id2 = generate_doc_id("memoria_lanzarote", "https://example.com/doc/2")
        assert id1 != id2

    def test_different_sources_different_ids(self):
        id1 = generate_doc_id("memoria_lanzarote", "https://example.com/doc/1")
        id2 = generate_doc_id("izuran", "https://example.com/doc/1")
        assert id1 != id2

    def test_hex_length(self):
        doc_id = generate_doc_id("test", "https://example.com")
        assert len(doc_id) == 64

    def test_canonicalizes_url(self):
        id1 = generate_doc_id("src", "https://example.com/doc/1/")
        id2 = generate_doc_id("src", "https://example.com/doc/1")
        assert id1 == id2


class TestGenerateContentHash:
    """Tests para generación de hashes de contenido."""

    def test_same_content_same_hash(self):
        h1 = generate_content_hash("La Cueva de los Verdes es un tubo volcánico.")
        h2 = generate_content_hash("La Cueva de los Verdes es un tubo volcánico.")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = generate_content_hash("La Cueva de los Verdes es un tubo volcánico.")
        h2 = generate_content_hash("El Charco de San Ginés es una laguna costera.")
        assert h1 != h2

    def test_hex_length(self):
        h = generate_content_hash("texto")
        assert len(h) == 64


class TestRawDocument:
    """Tests para RawDocument."""

    def test_creation(self):
        now = datetime.now(timezone.utc)
        doc = RawDocument(
            url="https://memoriadelanzarote.com/documentos/123",
            html="<html><body>Contenido</body></html>",
            status_code=200,
            fetched_at=now,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
        assert doc.url == "https://memoriadelanzarote.com/documentos/123"
        assert doc.status_code == 200

    def test_roundtrip(self):
        now = datetime.now(timezone.utc)
        doc = RawDocument(
            url="https://memoriadelanzarote.com/documentos/123",
            html="<html><body>Contenido</body></html>",
            status_code=200,
            fetched_at=now,
            headers={"Content-Type": "text/html"},
        )
        restored = RawDocument.from_dict(doc.to_dict())
        assert restored.url == doc.url
        assert restored.status_code == doc.status_code
        assert restored.fetched_at == doc.fetched_at
        assert restored.html == doc.html


class TestMetadata:
    """Tests para Metadata."""

    def test_defaults(self):
        meta = Metadata()
        assert meta.author is None
        assert meta.content_type == "article"
        assert meta.extra == {}

    def test_roundtrip(self):
        meta = Metadata(
            author="César Manrique",
            published_date="1971-1980",
            category="arquitectura",
            island="Lanzarote",
            content_type="article",
            extra={"pages": 42},
        )
        restored = Metadata.from_dict(meta.to_dict())
        assert restored.author == meta.author
        assert restored.island == meta.island
        assert restored.extra == meta.extra


class TestProcessedDocument:
    """Tests para ProcessedDocument."""

    def test_creation(self):
        now = datetime.now(timezone.utc)
        doc = ProcessedDocument(
            doc_id=generate_doc_id("memoria_lanzarote", "https://example.com/doc/1"),
            source_id="memoria_lanzarote",
            url="https://example.com/doc/1",
            title="La arquitectura de César Manrique",
            content="César Manrique transformó Lanzarote con su visión artística.",
            content_hash=generate_content_hash(
                "César Manrique transformó Lanzarote con su visión artística."
            ),
            language="es",
            metadata=Metadata(
                author="José García",
                island="Lanzarote",
                category="arquitectura",
            ),
            fetched_at=now,
            processed_at=now,
            connector_version="1.0.0",
        )
        assert doc.source_id == "memoria_lanzarote"
        assert len(doc.doc_id) == 64

    def test_roundtrip(self):
        now = datetime.now(timezone.utc)
        doc = ProcessedDocument(
            doc_id="a" * 64,
            source_id="memoria_lanzarote",
            url="https://example.com/doc/1",
            title="Título",
            content="Contenido del documento.",
            content_hash="b" * 64,
            language="es",
            metadata=Metadata(author="Autor", island="Lanzarote"),
            fetched_at=now,
            processed_at=now,
            connector_version="1.0.0",
        )
        restored = ProcessedDocument.from_dict(doc.to_dict())
        assert restored.doc_id == doc.doc_id
        assert restored.metadata.author == doc.metadata.author
        assert restored.fetched_at == doc.fetched_at


class TestChunk:
    """Tests para Chunk."""

    def test_creation(self):
        chunk = Chunk(
            chunk_id=generate_chunk_id("a" * 64, 0),
            doc_id="a" * 64,
            chunk_index=0,
            content="Fragmento sobre la historia de Teguise.",
            token_count=45,
            source_id="memoria_lanzarote",
            url="https://example.com/doc/1",
            title="Historia de Teguise",
            island="Lanzarote",
            category="historia",
            content_type="article",
        )
        assert chunk.chunk_index == 0
        assert len(chunk.chunk_id) == 64

    def test_roundtrip(self):
        chunk = Chunk(
            chunk_id="c" * 64,
            doc_id="a" * 64,
            chunk_index=2,
            content="Texto del chunk.",
            token_count=20,
            source_id="izuran",
            url="https://example.com/entry/5",
            title="Entrada de diccionario",
            island=None,
            category="lingüística",
            content_type="dictionary_entry",
        )
        restored = Chunk.from_dict(chunk.to_dict())
        assert restored.chunk_id == chunk.chunk_id
        assert restored.island is None
        assert restored.category == chunk.category
