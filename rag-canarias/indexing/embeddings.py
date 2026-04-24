from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Lazy-loaded sentence-transformers wrapper with MPS support (M4 Pro)."""

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        self._model_name = model_name
        self._model = None  # lazy

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from sentence_transformers import SentenceTransformer

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info("Loading %s on %s", self._model_name, device)
        self._model = SentenceTransformer(self._model_name, device=device)

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        self._load()
        return self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,  # unit vectors → cosine = dot product
        )

    @property
    def dimension(self) -> int:
        self._load()
        return self._model.get_sentence_embedding_dimension()
