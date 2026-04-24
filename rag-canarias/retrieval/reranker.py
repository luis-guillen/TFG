"""Reranking de candidatos con CrossEncoder bge-reranker-v2-m3."""
from __future__ import annotations

import logging

import torch
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


class Reranker:
    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._model: CrossEncoder | None = None

    def _load(self) -> None:
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._model = CrossEncoder(self._model_name, device=device)
        logger.info("Reranker loaded: %s on %s", self._model_name, device)

    def rerank(self, query: str, hits: list[dict], top_k: int) -> list[dict]:
        if not hits:
            return []
        if self._model is None:
            self._load()
        pairs = [(query, h["content"]) for h in hits]
        scores = self._model.predict(pairs, convert_to_numpy=True)
        ranked = sorted(zip(scores, hits), key=lambda x: x[0], reverse=True)[:top_k]
        return [{"rerank_score": float(s), **h} for s, h in ranked]
