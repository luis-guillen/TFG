from __future__ import annotations

import logging

from fastapi import FastAPI

from api.routes import router
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


def create_app() -> FastAPI:
    settings = Settings.get()

    app = FastAPI(
        title="RAG Canarias API",
        description="Sistema RAG para patrimonio cultural de Canarias — TFG",
        version="0.1.0",
    )

    @app.on_event("startup")
    async def _ensure_dirs() -> None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.raw_queue_path.parent.mkdir(parents=True, exist_ok=True)

    app.include_router(router)
    return app


app = create_app()
