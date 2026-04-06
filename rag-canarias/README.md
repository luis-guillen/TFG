# RAG Canarias

Sistema RAG para consulta inteligente sobre patrimonio cultural de Canarias.

**Estado actual:** Fase 1 — pipeline de ingestión en desarrollo.

## Instalación

```bash
pip install -e ".[dev]"
```

## Tests

```bash
pytest
```

## Estructura del proyecto

```
rag-canarias/
├── config/          # Configuración y definición de fuentes
├── connectors/      # Conectores específicos por fuente de datos
├── crawler/         # Fetcher HTTP y comprobación de robots.txt
├── parser/          # Extracción de contenido desde HTML
├── processing/      # Normalización, enriquecimiento y chunking
├── storage/         # Modelos de dominio y persistencia
├── indexing/        # Índices vectorial y léxico
├── retrieval/       # Búsqueda híbrida y reranking
├── generation/      # Generación de respuestas con LLM
├── api/             # API REST
├── pipeline/        # Orquestación de ingestión y consulta
├── scripts/         # Scripts CLI
├── tests/           # Tests unitarios y fixtures
├── data/            # Datos descargados e índices (no versionado)
└── notebooks/       # Notebooks de exploración
```

## Fuentes de datos

1. [Memoria de Lanzarote](https://memoriadelanzarote.com/) — Archivo digital de Lanzarote
2. [IZURAN](https://izuran.academiacanarialengua.org/) — Diccionario de la lengua amazigh insular
3. [Museo Canario](https://www.elmuseocanario.com/) — Colección arqueológica de Gran Canaria
4. [Guanches.org](https://www.guanches.org/) — Portal sobre el pueblo guanche
5. [BienMesabe.org](https://www.bienmesabe.org/) — Revista digital de cultura canaria
6. [Patriarca ULPGC](https://patriarca.ulpgc.es/) — Patrimonio documental de Canarias
