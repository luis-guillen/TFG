from __future__ import annotations

import logging
import uuid

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from storage.models import Chunk

logger = logging.getLogger(__name__)


def _point_id(chunk_id: str) -> str:
    """Deterministic UUID from chunk_id — Qdrant accepts UUID strings."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))


class VectorIndex:
    def __init__(self, url: str, collection: str) -> None:
        self._client = QdrantClient(url=url, timeout=30)
        self._collection = collection

    def ensure_collection(self, dim: int) -> None:
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info("Created collection '%s' dim=%d", self._collection, dim)

    def upsert(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        points = [
            PointStruct(
                id=_point_id(c.chunk_id),
                vector=emb.tolist(),
                payload={
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "url": c.url,
                    "title": c.title,
                    "content": c.content,
                    "source_id": c.source_id,
                    "island": c.island,
                    "category": c.category,
                    "chunk_index": c.chunk_index,
                },
            )
            for c, emb in zip(chunks, embeddings, strict=True)
        ]
        self._client.upsert(collection_name=self._collection, points=points, wait=True)
        logger.info("Upserted %d points to Qdrant", len(points))

    def search(
        self,
        query_vec: np.ndarray,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[dict]:
        f = None
        if source_filter:
            f = Filter(must=[FieldCondition(key="source_id", match=MatchValue(value=source_filter))])
        results = self._client.search(
            collection_name=self._collection,
            query_vector=query_vec.tolist(),
            limit=top_k,
            query_filter=f,
            with_payload=True,
        )
        return [{"score": r.score, **r.payload} for r in results]

    def count(self) -> int:
        return self._client.count(collection_name=self._collection).count
