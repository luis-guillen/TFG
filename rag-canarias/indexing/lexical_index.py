from __future__ import annotations

import logging
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from storage.models import Chunk

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


class LexicalIndex:
    def __init__(self, index_path: Path) -> None:
        self._path = index_path
        self._bm25: BM25Okapi | None = None
        self._chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        tokenized = [_tokenize(c.content) for c in chunks]
        self._bm25 = BM25Okapi(tokenized)
        logger.info("BM25 built: %d chunks", len(chunks))

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("wb") as fh:
            pickle.dump({"bm25": self._bm25, "chunks": self._chunks}, fh)
        logger.info("BM25 saved → %s", self._path)

    def load(self) -> None:
        with self._path.open("rb") as fh:
            data = pickle.load(fh)
        self._bm25 = data["bm25"]
        self._chunks = data["chunks"]
        logger.info("BM25 loaded: %d chunks", len(self._chunks))

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if self._bm25 is None:
            raise RuntimeError("BM25 index not built or loaded")
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        # No score threshold: BM25 IDF can be negative with small corpora.
        # Always return top-k by rank; caller decides relevance cutoff.
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            {"score": float(scores[i]), **self._chunks[i].to_dict()}
            for i in ranked
        ]
