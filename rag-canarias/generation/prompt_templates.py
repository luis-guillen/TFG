"""Plantillas de prompts para el generador RAG."""
from __future__ import annotations

SYSTEM_PROMPT = """\
Eres un asistente experto en patrimonio cultural, histórico y natural de las Islas Canarias.
Responde siempre en español, de forma clara, rigurosa y citando tus fuentes.
Usa únicamente la información de los fragmentos proporcionados.
Si no puedes responder con la información disponible, indícalo explícitamente.
No inventes hechos ni especules más allá de lo que dicen los fragmentos."""


def build_user_prompt(question: str, context_chunks: list[dict]) -> str:
    """Construye el prompt con los fragmentos de contexto numerados."""
    if not context_chunks:
        return f"Pregunta: {question}\n\n(No se han encontrado fragmentos relevantes.)"

    parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        title = chunk.get("title", "Sin título")
        url = chunk.get("url", "")
        content = chunk.get("content", "").strip()
        parts.append(f"[{i}] {title}\nFuente: {url}\n{content}")

    context_block = "\n\n---\n\n".join(parts)

    return (
        f"Fragmentos de contexto:\n\n{context_block}\n\n"
        f"---\n\n"
        f"Pregunta: {question}\n\n"
        f"Responde basándote exclusivamente en los fragmentos anteriores. "
        f"Al final incluye una sección 'Fuentes:' con los números de referencia utilizados "
        f"(ej. [1], [2])."
    )
