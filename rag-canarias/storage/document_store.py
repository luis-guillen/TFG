from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from storage.models import Chunk

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_docs (
    doc_id       TEXT PRIMARY KEY,
    url          TEXT NOT NULL,
    domain       TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    chunk_count  INTEGER DEFAULT 0,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id     TEXT PRIMARY KEY,
    doc_id       TEXT NOT NULL,
    url          TEXT NOT NULL,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    source_id    TEXT NOT NULL,
    island       TEXT,
    category     TEXT,
    content_type TEXT NOT NULL,
    chunk_index  INTEGER NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES processed_docs(doc_id)
);
"""


class DocumentStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info("DocumentStore → %s", db_path)

    # ── document tracking ──────────────────────────────────────────────────

    def is_processed(self, doc_id: str, content_hash: str) -> bool:
        row = self._conn.execute(
            "SELECT content_hash FROM processed_docs WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            return False
        return row[0] == content_hash  # hash changed → reprocess

    def mark_processed(
        self,
        doc_id: str,
        url: str,
        domain: str,
        content_hash: str,
        chunk_count: int,
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO processed_docs
               (doc_id, url, domain, content_hash, chunk_count, processed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (doc_id, url, domain, content_hash, chunk_count,
             datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    # ── chunk storage (for BM25 rebuild) ──────────────────────────────────

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        rows = [
            (c.chunk_id, c.doc_id, c.url, c.title, c.content, c.source_id,
             c.island, c.category, c.content_type, c.chunk_index)
            for c in chunks
        ]
        self._conn.executemany(
            """INSERT OR REPLACE INTO chunks
               (chunk_id, doc_id, url, title, content, source_id,
                island, category, content_type, chunk_index)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        self._conn.commit()

    def load_all_chunks(self) -> list[Chunk]:
        rows = self._conn.execute(
            "SELECT chunk_id, doc_id, url, title, content, source_id, "
            "island, category, content_type, chunk_index FROM chunks"
        ).fetchall()
        return [
            Chunk(
                chunk_id=r[0], doc_id=r[1], url=r[2], title=r[3],
                content=r[4], token_count=len(r[4].split()),
                source_id=r[5], island=r[6], category=r[7],
                content_type=r[8], chunk_index=r[9],
            )
            for r in rows
        ]

    def stats(self) -> dict:
        docs = self._conn.execute("SELECT COUNT(*) FROM processed_docs").fetchone()[0]
        chunks = self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        return {"documents": docs, "chunks": chunks}

    def close(self) -> None:
        self._conn.close()
