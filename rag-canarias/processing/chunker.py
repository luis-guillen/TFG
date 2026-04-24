from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from storage.models import Chunk, ProcessedDocument, generate_chunk_id

# ~300-token chunks at ~4 chars/token; enough context, fits bge-m3 comfortably
_CHUNK_SIZE = 1200
_CHUNK_OVERLAP = 150
_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def chunk_document(
    doc: ProcessedDocument,
    chunk_size: int = _CHUNK_SIZE,
    chunk_overlap: int = _CHUNK_OVERLAP,
) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_SEPARATORS,
        length_function=len,
    )
    texts = splitter.split_text(doc.content)
    return [
        Chunk(
            chunk_id=generate_chunk_id(doc.doc_id, i),
            doc_id=doc.doc_id,
            chunk_index=i,
            content=text,
            token_count=len(text.split()),  # word count as proxy
            source_id=doc.source_id,
            url=doc.url,
            title=doc.title,
            island=doc.metadata.island,
            category=doc.metadata.category,
            content_type=doc.metadata.content_type,
        )
        for i, text in enumerate(texts)
        if text.strip()
    ]
