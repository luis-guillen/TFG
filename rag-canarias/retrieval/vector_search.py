"""Búsqueda semántica sobre el índice vectorial."""
from __future__ import annotations

import logging

import numpy as np

from indexing.embeddings import EmbeddingModel
from indexing.vector_index import VectorIndex

logger = logging.getLogger(__name__)


class VectorSearch:
    def __init__(self, embed_model: EmbeddingModel, vector_idx: VectorIndex) -> None:
        self._embed = embed_model
        self._idx = vector_idx

    def search(
        self,
        query: str,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[dict]:
        vec: np.ndarray = self._embed.encode([query])[0]
        return self._idx.search(vec, top_k=top_k, source_filter=source_filter)
