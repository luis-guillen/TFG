from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from api.schemas import (
    IngestDocumentRequest,
    IngestDocumentResponse,
    QueryRequest,
    QueryResponse,
)
from config.settings import Settings
from pipeline.query import run_query
from storage.models import generate_content_hash, generate_doc_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/ingest/document", response_model=IngestDocumentResponse)
async def ingest_document(req: IngestDocumentRequest) -> IngestDocumentResponse:
    settings = Settings.get()
    doc_id = generate_doc_id(req.domain, req.url)
    content_hash = generate_content_hash(req.html_clean)

    entry = {
        "doc_id": doc_id,
        "url": req.url,
        "domain": req.domain,
        "html_clean": req.html_clean,
        "title": req.title,
        "http_status": req.http_status,
        "depth": req.depth,
        "fetched_at": req.fetched_at.isoformat(),
        "crawler_version": req.crawler_version,
        "content_hash": content_hash,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    raw_queue = settings.raw_queue_path
    raw_queue.parent.mkdir(parents=True, exist_ok=True)
    with raw_queue.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info("ingested doc_id=%s url=%s", doc_id, req.url)
    return IngestDocumentResponse(
        doc_id=doc_id,
        status="received",
        message="Queued for processing",
    )


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: run_query(req.question, top_k=req.top_k, source_filter=req.source_filter),
    )
    return result
