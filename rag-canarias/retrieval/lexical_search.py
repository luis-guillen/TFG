"""Búsqueda léxica (BM25) sobre el índice de texto completo."""
from __future__ import annotations

import logging
from pathlib import Path

from indexing.lexical_index import LexicalIndex

logger = logging.getLogger(__name__)


class LexicalSearch:
    def __init__(self, bm25_path: Path) -> None:
        self._idx = LexicalIndex(bm25_path)
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._idx.load()
            self._loaded = True

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        self._ensure_loaded()
        return self._idx.search(query, top_k=top_k)
