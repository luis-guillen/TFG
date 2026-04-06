# Arquitectura del Sistema RAG — Patrimonio Cultural de Canarias

## 1. Objetivo de la tarea

Definir la estructura de carpetas, módulos y responsabilidades del proyecto software que sustentará un sistema RAG (Retrieval-Augmented Generation) para consulta inteligente sobre patrimonio cultural canario. Esta estructura debe ser:

- **Modular**: cada etapa del pipeline (crawling → parsing → normalización → chunking → indexación → recuperación → generación) vive en su propio paquete con interfaces claras.
- **Extensible por fuente**: añadir una nueva fuente web implica crear un único archivo conector sin tocar el núcleo.
- **Realista para un TFG**: sin sobre-ingeniería, pero con separación suficiente para que cada capítulo del TFG tenga su correspondencia directa en código.

---

## 2. Propuesta de estructura de carpetas

```
rag-canarias/
│
├── config/
│   ├── settings.py              # Configuración global (rutas, tiempos, umbrales)
│   └── sources.yaml             # Registro declarativo de fuentes
│
├── connectors/
│   ├── __init__.py
│   ├── base.py                  # Clase abstracta BaseConnector
│   ├── memoria_lanzarote.py     # Conector: memoriadelanzarote.com
│   ├── academia_lengua.py       # Conector: academiacanarialengua.org
│   ├── canarias_azul.py         # Conector: canarias-azul.iatext.ulpgc.es
│   ├── museo_canario.py         # Conector: elmuseocanario.com
│   ├── izuran.py                # Conector: izuran.blogspot.com
│   └── cultura_grancanaria.py   # Conector: cultura.grancanaria.com
│
├── crawler/
│   ├── __init__.py
│   ├── discovery.py             # Descubrimiento de URLs (sitemaps, enlaces internos)
│   ├── fetcher.py               # Descarga HTTP con reintentos y rate limiting
│   └── robots.py                # Comprobación de robots.txt
│
├── parser/
│   ├── __init__.py
│   ├── html_parser.py           # Extracción de contenido limpio desde HTML
│   ├── pdf_parser.py            # Extracción desde PDFs (si alguna fuente los tiene)
│   └── media.py                 # Extracción de metadatos de imágenes/audio
│
├── processing/
│   ├── __init__.py
│   ├── normalizer.py            # Limpieza de texto, normalización Unicode, etc.
│   ├── enricher.py              # Enriquecimiento con metadatos (fechas, categorías, isla)
│   └── chunker.py               # Segmentación de documentos en fragmentos
│
├── storage/
│   ├── __init__.py
│   ├── document_store.py        # Persistencia de documentos procesados (SQLite/JSON)
│   └── models.py                # Modelos de datos (Document, Chunk, Metadata)
│
├── indexing/
│   ├── __init__.py
│   ├── vector_index.py          # Indexación vectorial (embeddings + FAISS/ChromaDB)
│   └── lexical_index.py         # Indexación léxica (BM25)
│
├── retrieval/
│   ├── __init__.py
│   ├── retriever.py             # Orquestador de recuperación híbrida
│   ├── vector_search.py         # Búsqueda por similitud semántica
│   ├── lexical_search.py        # Búsqueda léxica BM25
│   └── reranker.py              # Re-ranking de resultados combinados
│
├── generation/
│   ├── __init__.py
│   ├── generator.py             # Generación de respuesta con LLM
│   └── prompt_templates.py      # Plantillas de prompts (para fase posterior)
│
├── api/
│   ├── __init__.py
│   └── routes.py                # Endpoints REST (placeholder para fase posterior)
│
├── pipeline/
│   ├── __init__.py
│   ├── ingest.py                # Pipeline completo de ingestión (crawl→parse→chunk→index)
│   └── query.py                 # Pipeline completo de consulta (retrieve→generate)
│
├── scripts/
│   ├── ingest_source.py         # CLI: ingestar una fuente concreta
│   ├── ingest_all.py            # CLI: ingestar todas las fuentes
│   └── query_cli.py             # CLI: hacer una consulta de prueba
│
├── tests/
│   ├── test_connectors/
│   ├── test_crawler/
│   ├── test_parser/
│   ├── test_processing/
│   ├── test_indexing/
│   └── test_retrieval/
│
├── data/                        # Ignorado en git, generado en ejecución
│   ├── raw/                     # HTML/PDF crudos descargados
│   ├── processed/               # Documentos normalizados (JSON)
│   ├── vector_store/            # Índice vectorial persistido
│   └── lexical_store/           # Índice léxico persistido
│
├── notebooks/                   # Experimentación y prototipado rápido
│   └── exploracion_fuentes.ipynb
│
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## 3. Descripción de cada módulo

### `config/`

| Archivo | Responsabilidad |
|---|---|
| `settings.py` | Carga de variables de entorno y constantes globales: rutas de datos, timeouts de red, tamaño máximo de chunk, modelo de embeddings a usar, etc. Un solo punto de verdad para la configuración. |
| `sources.yaml` | Registro declarativo de fuentes. Cada entrada define: nombre, URL base, conector a usar, frecuencia de recrawl y selectores CSS relevantes. Añadir una fuente nueva empieza aquí. |

Ejemplo de `sources.yaml`:
```yaml
sources:
  - id: memoria_lanzarote
    name: "Memoria de Lanzarote"
    base_url: "https://memoriadelanzarote.com/"
    connector: "connectors.memoria_lanzarote.MemoriaLanzaroteConnector"
    content_selectors:
      - "article"
      - ".entry-content"
    discovery: sitemap
    island: Lanzarote

  - id: academia_lengua
    name: "Academia Canaria de la Lengua"
    base_url: "https://www.academiacanarialengua.org/diccionario/"
    connector: "connectors.academia_lengua.AcademiaLenguaConnector"
    content_selectors:
      - ".dictionary-entry"
    discovery: pagination
    island: null  # ámbito general canario
```

### `connectors/`

El paquete más importante para la extensibilidad. Cada conector encapsula las **particularidades** de una fuente concreta.

| Archivo | Responsabilidad |
|---|---|
| `base.py` | Clase abstracta `BaseConnector` que define la interfaz que todo conector debe implementar: `discover_urls()`, `fetch_page(url)`, `parse_content(html)` y `extract_metadata(html)`. |
| Un archivo por fuente | Implementación específica. Cada uno sabe qué selectores CSS usar, cómo paginar, qué metadatos concretos extraer de esa fuente. |

La decisión clave aquí es que el conector **no hace crawling genérico**: delega la descarga al módulo `crawler/` y el parsing pesado al módulo `parser/`. El conector actúa como **director** que sabe qué pedir y cómo interpretar lo que recibe de cada fuente.

### `crawler/`

| Archivo | Responsabilidad |
|---|---|
| `discovery.py` | Dado un conector y su configuración, descubre todas las URLs a procesar. Estrategias: parseo de sitemap.xml, seguimiento de enlaces internos con profundidad configurable, paginación explícita. |
| `fetcher.py` | Descarga HTTP robusta: cabeceras de user-agent apropiadas, rate limiting por dominio (1-2 req/s), reintentos con backoff exponencial, caché local de respuestas. |
| `robots.py` | Comprueba robots.txt antes de cualquier descarga. Si una URL está bloqueada, la salta y lo registra en log. |

### `parser/`

| Archivo | Responsabilidad |
|---|---|
| `html_parser.py` | Recibe HTML crudo y selectores CSS (proporcionados por el conector), devuelve texto limpio estructurado. Usa BeautifulSoup. Elimina navegación, footers, scripts, publicidad. |
| `pdf_parser.py` | Para fuentes que enlacen documentos PDF. Extracción con `pdfplumber` o similar. |
| `media.py` | Extracción de URLs de imágenes, textos alt, y metadatos de medios incrustados. Útil para El Museo Canario, que probablemente tenga piezas con imágenes descriptivas. |

### `processing/`

| Archivo | Responsabilidad |
|---|---|
| `normalizer.py` | Normalización Unicode (NFC), colapso de espacios en blanco, eliminación de HTML residual, normalización de comillas y guiones, detección de idioma. |
| `enricher.py` | Añade metadatos estructurados al documento: isla asociada (Lanzarote, Gran Canaria...), categoría temática (arqueología, lingüística, etnografía...), fecha de publicación si se detecta, tipo de contenido (artículo, entrada de diccionario, ficha de museo). |
| `chunker.py` | Divide documentos largos en fragmentos aptos para embedding. Estrategia principal: chunking por párrafos con ventana deslizante y solapamiento configurable (ej. 512 tokens, 64 de overlap). Cada chunk hereda los metadatos del documento padre. |

### `storage/`

| Archivo | Responsabilidad |
|---|---|
| `models.py` | Dataclasses que definen las estructuras de datos del sistema. Los tres modelos centrales son `RawDocument` (HTML descargado + URL + timestamp), `ProcessedDocument` (texto limpio + metadatos enriquecidos) y `Chunk` (fragmento + referencia al documento padre + metadatos heredados). |
| `document_store.py` | Persistencia de documentos procesados. Para el MVP: SQLite con una tabla `documents` y una tabla `chunks`. Interfaz simple: `save_document()`, `get_document(doc_id)`, `list_documents(source_id)`, `save_chunks()`. |

### `indexing/`

| Archivo | Responsabilidad |
|---|---|
| `vector_index.py` | Genera embeddings de cada chunk (con `sentence-transformers`, modelo multilingüe como `paraphrase-multilingual-MiniLM-L12-v2`) y los almacena en un índice vectorial. Para el MVP: ChromaDB (embebido, sin servidor externo, persistencia en disco). |
| `lexical_index.py` | Construye un índice BM25 sobre los chunks para búsqueda léxica. Librería `rank_bm25`. Útil para términos canarios específicos (guanchismos, topónimos) que los embeddings podrían no capturar bien. |

### `retrieval/`

| Archivo | Responsabilidad |
|---|---|
| `vector_search.py` | Dada una query, genera su embedding y busca los k chunks más cercanos en el índice vectorial. |
| `lexical_search.py` | Dada una query, busca por BM25 en el índice léxico. |
| `retriever.py` | Orquestador de búsqueda híbrida. Combina resultados de ambas búsquedas mediante fusión de rankings (Reciprocal Rank Fusion). Es el punto de entrada único para el pipeline de consulta. |
| `reranker.py` | Re-ranking opcional con un cross-encoder para refinar el orden de los resultados. Para el MVP puede ser un pass-through que simplemente devuelve lo que recibe sin alterar. |

### `generation/`

| Archivo | Responsabilidad |
|---|---|
| `generator.py` | Recibe la query del usuario y los chunks recuperados, construye el prompt con contexto y llama al LLM. Devuelve la respuesta generada junto con las referencias a las fuentes usadas. |
| `prompt_templates.py` | Plantillas Jinja2 o strings formateados para los prompts del sistema. Se desarrollará en fases posteriores. |

### `pipeline/`

| Archivo | Responsabilidad |
|---|---|
| `ingest.py` | Orquesta el pipeline completo de ingestión para una fuente: carga su configuración desde `sources.yaml` → instancia el conector → descubre URLs → descarga → parsea → normaliza → enriquece → chunkea → persiste → indexa. |
| `query.py` | Orquesta el pipeline de consulta: recibe pregunta en lenguaje natural → recupera chunks relevantes → genera respuesta → devuelve respuesta + fuentes citadas. |

### `api/`

Placeholder para la fase posterior. Un archivo `routes.py` vacío con un comentario indicando que aquí irá la API REST (FastAPI) que expondrá el pipeline de consulta.

### `scripts/`

Puntos de entrada CLI para ejecución directa durante el desarrollo:

| Script | Uso |
|---|---|
| `ingest_source.py` | `python -m scripts.ingest_source --source memoria_lanzarote` |
| `ingest_all.py` | `python -m scripts.ingest_all` |
| `query_cli.py` | `python -m scripts.query_cli "¿Qué es un tagoro?"` |

---

## 4. Separación entre lógica común y lógica específica por fuente

Esta es una decisión de diseño central del proyecto. La regla es clara:

### Lógica GENÉRICA (reutilizada por todas las fuentes)

- Descarga HTTP con rate limiting (`crawler/fetcher.py`)
- Comprobación de robots.txt (`crawler/robots.py`)
- Limpieza y extracción HTML genérica (`parser/html_parser.py`)
- Normalización de texto (`processing/normalizer.py`)
- Chunking (`processing/chunker.py`)
- Persistencia documental (`storage/`)
- Indexación vectorial y léxica (`indexing/`)
- Recuperación y generación (`retrieval/`, `generation/`)

### Lógica ESPECÍFICA por fuente (un archivo por fuente)

Cada conector en `connectors/` encapsula:

- **Selectores CSS** de contenido principal (cada web tiene su estructura HTML propia).
- **Estrategia de descubrimiento** de URLs: Memoria de Lanzarote puede tener sitemap; el diccionario de la Academia usa paginación por letras; Izuran (Blogspot) usa la estructura de archivo de blog.
- **Extracción de metadatos específicos**: el diccionario extrae lema, definición, ejemplo de uso; El Museo Canario extrae título de pieza, datación, sala; Cultura Gran Canaria extrae nombre del museo, localización, horarios.
- **Transformaciones concretas**: por ejemplo, el diccionario de la Academia podría requerir unir varias entradas en un solo documento temático.

### Patrón de diseño: Template Method

`BaseConnector` define el esqueleto del proceso. Los conectores concretos sobreescriben solo los métodos que necesitan personalizar:

```
BaseConnector (base.py)
├── discover_urls()        → cada fuente lo implementa
├── get_content_selectors() → cada fuente devuelve sus selectores
├── extract_metadata()     → cada fuente extrae sus campos propios
├── transform_document()   → hook opcional, por defecto no-op
└── run()                  → orquesta todo, NO se sobreescribe
```

El resultado: **para añadir una fuente nueva se crea un único archivo** en `connectors/` y se añade una entrada en `sources.yaml`. No se toca nada más.

---

## 5. Flujo general entre módulos

```
┌─────────────────────────────────────── INGESTIÓN ───────────────────────────────────────┐
│                                                                                         │
│  sources.yaml ──→ connectors/     ──→ crawler/        ──→ parser/                       │
│  (configuración)  (dirige qué       (descarga HTTP       (extrae texto                  │
│                    pedir y cómo       robusta, respeta     limpio con                    │
│                    interpretarlo)     robots.txt)          selectores CSS)               │
│                                                                                         │
│                  ──→ processing/normalizer  ──→ processing/enricher                      │
│                     (limpieza Unicode,         (isla, categoría,                         │
│                      espacios, idioma)          tipo, fecha)                             │
│                                                                                         │
│                  ──→ processing/chunker    ──→ storage/document_store                    │
│                     (fragmentos de             (SQLite: documentos                       │
│                      512 tokens con             y chunks)                                │
│                      solapamiento)                                                       │
│                                                                                         │
│                  ──→ indexing/vector_index  +  indexing/lexical_index                     │
│                     (ChromaDB con              (BM25 sobre                               │
│                      embeddings)                chunks)                                  │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────── CONSULTA ────────────────────────────────────────┐
│                                                                                         │
│  Pregunta ──→ retrieval/retriever ──→ vector_search + lexical_search                    │
│  del usuario  (orquestador             (búsqueda semántica   (búsqueda                  │
│                híbrido)                 por embeddings)        por BM25)                 │
│                                                                                         │
│             ──→ retrieval/reranker ──→ generation/generator                              │
│                (fusión RRF,            (construye prompt                                 │
│                 re-ranking)             con contexto, llama                              │
│                                         al LLM, cita fuentes)                           │
│                                                                                         │
│             ──→ Respuesta + fuentes citadas                                             │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Recomendaciones de diseño

### 6.1. Usar dataclasses, no diccionarios

Definir `RawDocument`, `ProcessedDocument`, `Chunk` y `Metadata` como dataclasses en `storage/models.py`. Esto da autocompletado en el IDE, validación implícita y documentación viva de la estructura de datos. Evita el anti-patrón de pasar diccionarios anidados entre módulos sin que nadie sepa qué campos contienen.

### 6.2. Inyección de dependencias ligera

Los pipelines (`ingest.py`, `query.py`) reciben sus componentes como parámetros, no los importan directamente. Esto permite intercambiar implementaciones sin tocar el pipeline:

```python
# pipeline/ingest.py
class IngestPipeline:
    def __init__(self, fetcher, parser, normalizer, enricher, chunker, doc_store, indexers):
        ...
```

### 6.3. Logging estructurado desde el inicio

Usar `logging` estándar de Python con formato consistente en todos los módulos. Cada etapa del pipeline loguea: qué fuente procesa, cuántas URLs descubrió, cuántos documentos procesó, cuántos chunks generó. Esto es imprescindible para la memoria del TFG (sección de resultados y evaluación).

### 6.4. Configuración centralizada, no constantes dispersas

Todo parámetro ajustable (tamaño de chunk, overlap, modelo de embeddings, timeout HTTP, user-agent) vive en `config/settings.py` o en variables de entorno. Nunca hardcodeado dentro de un módulo.

### 6.5. Idempotencia en ingestión

El pipeline de ingestión debe poder re-ejecutarse sin duplicar datos. Cada documento se identifica por su URL + hash del contenido. Si el contenido no ha cambiado, se salta. Si ha cambiado, se re-procesa y actualiza los índices.

### 6.6. Tests por módulo, no solo end-to-end

Cada módulo debe tener tests unitarios con datos de prueba estáticos (HTMLs guardados en `tests/fixtures/`). No depender de conexión a internet para los tests. Los tests de integración (pipeline completo) son separados y opcionales.

### 6.7. Priorizar profundidad sobre amplitud en el MVP

Es mejor tener 2-3 fuentes completamente integradas y funcionando que 6 fuentes a medias. Las fuentes recomendadas para empezar, por orden de complejidad creciente:

1. **Izuran (Blogspot)** — Estructura predecible de blog, HTML limpio, buen primer conector.
2. **Memoria de Lanzarote** — Sitio con mucho contenido textual, buena fuente para probar chunking.
3. **Academia Canaria de la Lengua (diccionario)** — Estructura diferente (entradas léxicas), valida que el sistema es realmente extensible.

### 6.8. Dependencias recomendadas para el MVP

| Necesidad | Librería | Justificación |
|---|---|---|
| HTTP | `httpx` | Async-ready, mejor API que requests |
| HTML parsing | `beautifulsoup4` + `lxml` | Estándar de facto, robusto |
| Embeddings | `sentence-transformers` | Modelos multilingües de calidad |
| Índice vectorial | `chromadb` | Embebido, sin infraestructura, persistente |
| BM25 | `rank-bm25` | Ligero, sin dependencias |
| Base de datos | `sqlite3` (stdlib) | Cero configuración, suficiente para TFG |
| Config | `pyyaml` + `python-dotenv` | YAML para fuentes, .env para secretos |
| CLI | `click` o `argparse` | Ejecución desde terminal |
| LLM | API de Anthropic u OpenAI | Se decide en fase posterior |
| Tests | `pytest` | Estándar |

---

## 7. Estructura final recomendada

Resumiendo las decisiones concretas:

**Lenguaje**: Python 3.11+

**Gestión de proyecto**: `pyproject.toml` con dependencias definidas, sin Docker para el MVP (no es necesario para un TFG).

**Base de datos**: SQLite para documentos y metadatos. ChromaDB embebido para vectores. BM25 en memoria con serialización a disco.

**Patrón central**: Template Method para conectores + Pipeline para ingestión/consulta.

**Extensibilidad**: Un archivo YAML + un archivo Python por fuente nueva. Nada más.

**Pipeline de ingestión**: `sources.yaml` → `BaseConnector.run()` → `fetcher` → `html_parser` → `normalizer` → `enricher` → `chunker` → `document_store` → `vector_index` + `lexical_index`.

**Pipeline de consulta**: query → `retriever` (vector + BM25 + RRF) → `reranker` → `generator` → respuesta con citas.

**Próximos pasos inmediatos** (tareas siguientes del TFG):

1. Implementar `storage/models.py` con las dataclasses.
2. Implementar `config/settings.py` y `sources.yaml` con la primera fuente.
3. Implementar `BaseConnector` y el primer conector concreto (Izuran).
4. Implementar `crawler/fetcher.py` con rate limiting.
5. Implementar `parser/html_parser.py` genérico.
6. Probar el flujo descarga → parsing → normalización para una fuente.

---

*Documento generado como base arquitectónica del TFG sobre sistema RAG para patrimonio cultural de Canarias.*
