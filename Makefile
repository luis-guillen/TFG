.PHONY: help install qdrant-up qdrant-down serve index query eval ollama-setup

help:
	@echo "Comandos disponibles:"
	@echo "  make install       Instala dependencias Python (rag-canarias)"
	@echo "  make qdrant-up     Arranca Qdrant en Docker"
	@echo "  make qdrant-down   Para Qdrant"
	@echo "  make serve         Arranca FastAPI (requiere qdrant-up)"
	@echo "  make index         Indexa la cola de documentos crudos"
	@echo "  make query         CLI de consulta interactiva"
	@echo "  make eval          Evaluación RAGAS sobre golden set"
	@echo "  make ollama-setup  Descarga modelo LLM via Ollama (nativo)"

install:
	cd rag-canarias && pip install -e ".[dev]"

qdrant-up:
	docker compose up qdrant -d
	@echo "Qdrant UI: http://localhost:6333/dashboard"

qdrant-down:
	docker compose down

serve: qdrant-up
	cd rag-canarias && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

index:
	cd rag-canarias && python scripts/build_index.py

query:
	cd rag-canarias && python scripts/query_cli.py

eval:
	cd rag-canarias && python scripts/eval_run.py

ollama-setup:
	@command -v ollama >/dev/null 2>&1 || (echo "Instala Ollama: brew install ollama" && exit 1)
	ollama pull llama3.1:8b-instruct-q4_K_M
	@echo "Modelo listo. Arranca con: ollama serve"
