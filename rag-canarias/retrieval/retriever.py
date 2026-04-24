"""Orquestador de recuperación híbrida: vector + BM25 → RRF → reranking."""
from __future__ import annotations

import logging
from pathlib import Path

from indexing.embeddings import EmbeddingModel
from indexing.vector_index import VectorIndex
from retrieval.lexical_search import LexicalSearch
from retrieval.reranker import Reranker
from retrieval.vector_search import VectorSearch

logger = logging.getLogger(__name__)

_RRF_K = 60


def _rrf_fuse(vector_hits: list[dict], lexical_hits: list[dict]) -> list[dict]:
    """Reciprocal Rank Fusion sobre dos listas ordenadas."""
    scores: dict[str, float] = {}
    by_id: dict[str, dict] = {}

    for rank, hit in enumerate(vector_hits, start=1):
        cid = hit["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (_RRF_K + rank)
        by_id[cid] = hit

    for rank, hit in enumerate(lexical_hits, start=1):
        cid = hit["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (_RRF_K + rank)
        by_id.setdefault(cid, hit)

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"rrf_score": sc, **by_id[cid]} for cid, sc in fused]


class HybridRetriever:
    def __init__(
        self,
        embed_model: EmbeddingModel,
        vector_idx: VectorIndex,
        bm25_path: Path,
        reranker: Reranker | None = None,
    ) -> None:
        self._vector = VectorSearch(embed_model, vector_idx)
        self._lexical = LexicalSearch(bm25_path)
        self._reranker = reranker

    def retrieve(
        self,
        query: str,
        top_k: int = 6,
        fetch_k: int = 20,
        source_filter: str | None = None,
    ) -> list[dict]:
        vec_hits = self._vector.search(query, top_k=fetch_k, source_filter=source_filter)
        lex_hits = self._lexical.search(query, top_k=fetch_k)
        fused = _rrf_fuse(vec_hits, lex_hits)

        if self._reranker is not None:
            return self._reranker.rerank(query, fused, top_k=top_k)

        return fused[:top_k]
