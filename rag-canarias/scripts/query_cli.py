#!/usr/bin/env python3
"""CLI de consulta interactiva al sistema RAG.

Uso:
    python scripts/query_cli.py
    python scripts/query_cli.py "¿Qué es el Charco de San Ginés?"
"""
from __future__ import annotations

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.query import run_query

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


def _print_result(result) -> None:
    print("\n" + "=" * 64)
    print(result.answer)
    if result.citations:
        print("\n── Fragmentos recuperados " + "─" * 38)
        for i, c in enumerate(result.citations, 1):
            print(f"  [{i}] {c.title}")
            print(f"       {c.url}")
            print(f"       score: {c.score:.4f}")
    print(f"\n  Latencia: {result.latency_ms:.0f} ms")
    print("=" * 64 + "\n")


def main() -> None:
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        _print_result(run_query(question))
        return

    print("RAG Canarias — CLI de consulta interactiva (Ctrl+C para salir)")
    print("─" * 64)
    while True:
        try:
            question = input("\nPregunta: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego.")
            break
        if not question:
            continue
        _print_result(run_query(question))


if __name__ == "__main__":
    main()
