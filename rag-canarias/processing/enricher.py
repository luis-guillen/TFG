from __future__ import annotations

from storage.models import Metadata

# Domain → island mapping (exact)
_DOMAIN_ISLAND: dict[str, str] = {
    "memoriadelanzarote.com": "Lanzarote",
    "cultura.grancanaria.com": "Gran Canaria",
    "elmuseocanario.com": "Gran Canaria",
    "canarias-azul.iatext.ulpgc.es": None,
    "izuran.blogspot.com": None,
    "academiacanarialengua.org": None,
}

# Content keywords → island
_CONTENT_ISLAND: list[tuple[str, list[str]]] = [
    ("Lanzarote",    ["lanzarote", "arrecife", "yaiza", "teguise", "timanfaya"]),
    ("Fuerteventura", ["fuerteventura", "corralejo", "morro jable", "betancuria"]),
    ("Gran Canaria", ["gran canaria", "las palmas", "mogán", "teror", "agüimes"]),
    ("Tenerife",     ["tenerife", "santa cruz", "la orotava", "teide", "icod"]),
    ("La Palma",     ["la palma", "santa cruz de la palma", "caldera de taburiente"]),
    ("La Gomera",    ["la gomera", "san sebastián de la gomera", "silbo"]),
    ("El Hierro",    ["el hierro", "valverde", "frontera"]),
]

# Content keywords → category
_CATEGORIES: list[tuple[str, list[str]]] = [
    ("arqueología",   ["yacimiento", "excavación", "prehistoria", "guanche", "aborigen", "pintadera"]),
    ("lingüística",   ["diccionario", "léxico", "habla canaria", "silbo", "amazigh", "guanchismo"]),
    ("etnografía",    ["costumbre", "tradición", "folclore", "artesanía", "lucha canaria", "folklore"]),
    ("gastronomía",   ["gofio", "mojo", "papas", "bienmesabe", "gastronomía", "receta"]),
    ("naturaleza",    ["laurisilva", "teide", "drago", "caldera", "flora canaria", "fauna"]),
    ("patrimonio",    ["bien cultural", "monumento", "patrimonio", "catalogado", "protegido"]),
    ("museo",         ["museo", "colección", "exposición", "pieza", "vitrina", "sala"]),
]


def enrich(
    domain: str,
    title: str,
    content: str,
    base_metadata: Metadata | None = None,
) -> Metadata:
    m = base_metadata or Metadata()

    if m.island is None:
        m.island = _detect_island(domain, content)

    if m.category is None:
        m.category = _detect_category(title + " " + content[:2000])

    return m


def _detect_island(domain: str, content: str) -> str | None:
    # 1. Exact domain match
    for d, island in _DOMAIN_ISLAND.items():
        if d in domain:
            return island

    # 2. Keyword scan in content (first 3 000 chars)
    low = content[:3000].lower()
    counts: dict[str, int] = {}
    for island, kws in _CONTENT_ISLAND:
        hits = sum(low.count(kw) for kw in kws)
        if hits:
            counts[island] = hits

    if counts:
        return max(counts, key=lambda k: counts[k])
    return None


def _detect_category(text: str) -> str | None:
    low = text.lower()
    scores: dict[str, int] = {}
    for category, kws in _CATEGORIES:
        hits = sum(low.count(kw) for kw in kws)
        if hits:
            scores[category] = hits
    return max(scores, key=lambda k: scores[k]) if scores else "patrimonio"
