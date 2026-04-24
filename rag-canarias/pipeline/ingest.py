from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from config.settings import Settings
from indexing.embeddings import EmbeddingModel
from indexing.lexical_index import LexicalIndex
from indexing.vector_index import VectorIndex
from processing.chunker import chunk_document
from processing.enricher import enrich
from processing.normalizer import html_to_text
from storage.document_store import DocumentStore
from storage.models import Metadata, ProcessedDocument, generate_content_hash

logger = logging.getLogger(__name__)


def run_ingest(reindex: bool = False) -> dict:
    """Read raw_queue.jsonl → normalize → enrich → chunk → embed → index.

    Args:
        reindex: If True, reprocess all documents even if already indexed.

    Returns:
        Summary dict with processed/skipped/error counts.
    """
    settings = Settings.get()

    raw_queue: Path = settings.raw_queue_path
    if not raw_queue.exists():
        logger.warning("raw_queue not found: %s", raw_queue)
        return {"processed": 0, "skipped": 0, "errors": 0, "total_chunks": 0}

    store = DocumentStore(settings.db_path)
    vector_idx = VectorIndex(settings.qdrant_url, settings.qdrant_collection)
    embed_model = EmbeddingModel(settings.embedding_model)

    bm25_path = settings.data_dir / "bm25_index.pkl"
    lexical_idx = LexicalIndex(bm25_path)

    stats = {"processed": 0, "skipped": 0, "errors": 0, "total_chunks": 0}

    # Ensure Qdrant collection exists (we need the embedding dim)
    collection_ready = False

    entries = _load_queue(raw_queue)
    logger.info("Entries in queue: %d", len(entries))

    for entry in entries:
        doc_id: str = entry["doc_id"]
        content_hash: str = entry["content_hash"]

        if not reindex and store.is_processed(doc_id, content_hash):
            stats["skipped"] += 1
            continue

        try:
            doc = _build_processed_doc(entry)
            if doc is None:
                stats["errors"] += 1
                continue

            chunks = chunk_document(doc)
            if not chunks:
                logger.warning("No chunks for %s — skipping", entry["url"])
                stats["errors"] += 1
                continue

            embeddings = embed_model.encode([c.content for c in chunks])

            if not collection_ready:
                vector_idx.ensure_collection(embed_model.dimension)
                collection_ready = True

            vector_idx.upsert(chunks, embeddings)
            store.upsert_chunks(chunks)
            store.mark_processed(
                doc_id=doc_id,
                url=entry["url"],
                domain=entry["domain"],
                content_hash=content_hash,
                chunk_count=len(chunks),
            )

            stats["processed"] += 1
            stats["total_chunks"] += len(chunks)
            logger.info("✓ %s  (%d chunks)", entry["url"], len(chunks))

        except Exception:
            logger.exception("Error processing %s", entry.get("url"))
            stats["errors"] += 1

    # Rebuild BM25 from ALL chunks in the store (full corpus)
    all_chunks = store.load_all_chunks()
    if all_chunks:
        lexical_idx.build(all_chunks)
        lexical_idx.save()

    store.close()
    db_stats = store.stats() if False else {}  # store already closed; stats logged above
    logger.info(
        "Ingest done — processed=%d skipped=%d errors=%d chunks=%d",
        stats["processed"], stats["skipped"], stats["errors"], stats["total_chunks"],
    )
    return stats


def _load_queue(path: Path) -> list[dict]:
    entries = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning("Malformed JSON line: %s", e)
    return entries


def _build_processed_doc(entry: dict) -> ProcessedDocument | None:
    html_clean: str = entry.get("html_clean", "")
    url: str = entry["url"]

    content = html_to_text(html_clean, url=url)
    if not content or len(content.strip()) < 80:
        logger.warning("Too short after normalization: %s", url)
        return None

    metadata = enrich(
        domain=entry.get("domain", ""),
        title=entry.get("title") or "",
        content=content,
    )

    return ProcessedDocument(
        doc_id=entry["doc_id"],
        source_id=entry.get("domain", "unknown"),
        url=url,
        title=entry.get("title") or _extract_title(content),
        content=content,
        content_hash=generate_content_hash(content),
        language="es",
        metadata=metadata,
        fetched_at=datetime.fromisoformat(entry["fetched_at"]),
        processed_at=datetime.now(timezone.utc),
        connector_version="pipeline-ingest-1.0",
    )


def _extract_title(content: str) -> str:
    """Best-effort title from first non-empty line."""
    for line in content.splitlines():
        line = line.strip()
        if line and len(line) < 200:
            return line
    return "Sin título"
