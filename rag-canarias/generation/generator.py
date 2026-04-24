"""Generador de respuestas con LLM.

Estrategia: Anthropic (si hay API key) → Ollama local (por defecto).
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class LLMBackend(ABC):
    @abstractmethod
    def generate(self, system: str, user: str) -> str: ...


class OllamaBackend(LLMBackend):
    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self._url = f"{base_url.rstrip('/')}/api/chat"
        self._model = model
        self._timeout = timeout

    def generate(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(self._url, json=payload)
            resp.raise_for_status()
        return resp.json()["message"]["content"]


class AnthropicBackend(LLMBackend):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._api_key = api_key
        self._model = model

    def generate(self, system: str, user: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self._api_key)
        msg = client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text


def build_generator(settings) -> LLMBackend:
    """Devuelve AnthropicBackend si hay API key configurada, OllamaBackend si no."""
    if settings.anthropic_api_key:
        logger.info("LLM backend: Anthropic (%s)", "claude-sonnet-4-6")
        return AnthropicBackend(api_key=settings.anthropic_api_key)
    logger.info("LLM backend: Ollama (%s @ %s)", settings.ollama_model, settings.ollama_url)
    return OllamaBackend(base_url=settings.ollama_url, model=settings.ollama_model)
