from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class IngestDocumentRequest(BaseModel):
    url: str
    domain: str
    html_clean: str
    title: str | None = None
    http_status: int = 200
    depth: int = 0
    fetched_at: datetime
    crawler_version: str = "csharp-webforms-1.0"


class IngestDocumentResponse(BaseModel):
    doc_id: str
    status: str  # "received" | "duplicate" | "error"
    message: str


class QueryRequest(BaseModel):
    question: str
    top_k: int = 6
    source_filter: str | None = None


class CitationDto(BaseModel):
    doc_id: str
    url: str
    title: str
    snippet: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationDto]
    latency_ms: float
