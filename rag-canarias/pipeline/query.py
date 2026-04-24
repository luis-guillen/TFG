"""Pipeline de consulta: recuperación híbrida → reranking → generación."""
from __future__ import annotations

import logging
import time

from api.schemas import CitationDto, QueryResponse
from config.settings import Settings
from generation.generator import LLMBackend, build_generator
from generation.prompt_templates import SYSTEM_PROMPT, build_user_prompt
from indexing.embeddings import EmbeddingModel
from indexing.vector_index import VectorIndex
from retrieval.reranker import Reranker
from retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)

# Singletons cargados la primera vez (lazy) — el proceso FastAPI los reutiliza
_retriever: HybridRetriever | None = None
_generator: LLMBackend | None = None


def _get_retriever(settings: Settings) -> HybridRetriever:
    global _retriever
    if _retriever is None:
        embed = EmbeddingModel(settings.embedding_model)
        vector_idx = VectorIndex(settings.qdrant_url, settings.qdrant_collection)
        bm25_path = settings.data_dir / "bm25_index.pkl"
        reranker = Reranker() if bm25_path.exists() else None
        _retriever = HybridRetriever(embed, vector_idx, bm25_path, reranker=reranker)
        logger.info("HybridRetriever initialized (reranker=%s)", reranker is not None)
    return _retriever


def _get_generator(settings: Settings) -> LLMBackend:
    global _generator
    if _generator is None:
        _generator = build_generator(settings)
    return _generator


def run_query(
    question: str,
    top_k: int = 6,
    source_filter: str | None = None,
) -> QueryResponse:
    t0 = time.perf_counter()
    settings = Settings.get()

    retriever = _get_retriever(settings)
    hits = retriever.retrieve(question, top_k=top_k, source_filter=source_filter)

    if not hits:
        return QueryResponse(
            answer="No se han encontrado documentos relevantes en el índice para esta consulta.",
            citations=[],
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        )

    generator = _get_generator(settings)
    user_prompt = build_user_prompt(question, hits)
    answer = generator.generate(SYSTEM_PROMPT, user_prompt)

    citations = [
        CitationDto(
            doc_id=h.get("doc_id", ""),
            url=h.get("url", ""),
            title=h.get("title", "Sin título"),
            snippet=h.get("content", "")[:300],
            score=float(h.get("rerank_score", h.get("rrf_score", 0.0))),
        )
        for h in hits
    ]

    return QueryResponse(
        answer=answer,
        citations=citations,
        latency_ms=round((time.perf_counter() - t0) * 1000, 1),
    )
