PYTHON := rag-canarias/.venv/bin/python
PIP    := rag-canarias/.venv/bin/pip
UV     := rag-canarias/.venv/bin/uvicorn

.PHONY: help install qdrant-up qdrant-down serve index query eval ollama-setup

help:
	@echo "Comandos disponibles:"
	@echo "  make install       Instala dependencias en .venv"
	@echo "  make qdrant-up     Arranca Qdrant en Docker"
	@echo "  make qdrant-down   Para Qdrant"
	@echo "  make serve         Arranca FastAPI (requiere qdrant-up)"
	@echo "  make index         Indexa la cola de documentos crudos"
	@echo "  make index REINDEX=1  Fuerza reindexado completo"
	@echo "  make query         CLI de consulta interactiva"
	@echo "  make eval          Evaluación RAGAS sobre golden set"
	@echo "  make ollama-setup  Descarga modelo LLM via Ollama (nativo)"

install:
	cd rag-canarias && .venv/bin/pip install -e ".[dev]"

qdrant-up:
	docker compose up qdrant -d
	@echo "Qdrant UI: http://localhost:6333/dashboard"

qdrant-down:
	docker compose down

serve: qdrant-up
	cd rag-canarias && KMP_DUPLICATE_LIB_OK=TRUE .venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

index:
	cd rag-canarias && KMP_DUPLICATE_LIB_OK=TRUE .venv/bin/python scripts/build_index.py $(if $(REINDEX),--reindex,)

query:
	cd rag-canarias && KMP_DUPLICATE_LIB_OK=TRUE .venv/bin/python scripts/query_cli.py

eval:
	cd rag-canarias && KMP_DUPLICATE_LIB_OK=TRUE .venv/bin/python scripts/eval_run.py

ollama-setup:
	@command -v ollama >/dev/null 2>&1 || (echo "Instala Ollama: brew install ollama" && exit 1)
	ollama pull llama3.1:8b-instruct-q4_K_M
	@echo "Modelo listo. Arranca con: ollama serve"
