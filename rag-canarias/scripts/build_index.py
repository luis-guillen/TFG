#!/usr/bin/env python3
"""Build or refresh the RAG vector+lexical index from the raw ingestion queue.

Usage:
    python scripts/build_index.py            # skip already-indexed docs
    python scripts/build_index.py --reindex  # force reprocess all
"""
from __future__ import annotations

import os

# Must be set before any ML library import (OpenMP conflict on macOS+conda)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse
import logging
import sys
from pathlib import Path

# Make project root importable when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from pipeline.ingest import run_ingest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Reprocess all documents, ignoring previous indexing state",
    )
    args = parser.parse_args()

    settings = Settings.get()
    logging.info("Queue  : %s", settings.raw_queue_path)
    logging.info("Qdrant : %s  collection=%s", settings.qdrant_url, settings.qdrant_collection)
    logging.info("Model  : %s", settings.embedding_model)
    logging.info("Reindex: %s", args.reindex)

    stats = run_ingest(reindex=args.reindex)

    print("\n── Index build complete ─────────────────────")
    print(f"  Processed : {stats['processed']}")
    print(f"  Skipped   : {stats['skipped']}")
    print(f"  Errors    : {stats['errors']}")
    print(f"  Chunks    : {stats['total_chunks']}")
    print("─────────────────────────────────────────────")


if __name__ == "__main__":
    main()
