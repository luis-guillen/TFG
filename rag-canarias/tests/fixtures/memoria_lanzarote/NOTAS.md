# Notas de exploración: Memoria de Lanzarote

Exploración realizada: 2026-04-07

## 1. Estructura de URLs observada

- **Listado de documentos:** `/documentos` con paginación `?o=periodo&page=N` (páginas 0-24)
- **Detalle de item:** `/item/{id}-{slug}` (ej. `/item/24016-la-trenza-de-espejo-...`)
- **Imágenes:** `/imagenes` con la misma estructura de paginación
- **Audios:** `/audios`
- **Colecciones:** `/colecciones`
- **Backend de medios:** `https://bk.memoriadelanzarote.com/media/items/...`

## 2. Selectores CSS del contenido principal

- **Título:** `h1` (texto del título del documento)
- **Contenedor principal:** `div.contenido` (contiene todo el bloque del item)
- **Bloque de información:** `.informacion` (contiene metadatos y descripción)
- **Descripción/texto:** `.prose` dentro de `.informacion`
- **Lista de metadatos:** `.informacion ul.space-y-4 > li`

## 3. Selectores de metadatos

Los metadatos están en elementos `<li>` dentro de `.informacion ul`. Cada campo sigue el patrón:
texto con label en negrita seguido del valor. Campos observados:

| Campo               | Ejemplo                                    |
|---------------------|--------------------------------------------|
| Descripción         | Texto largo en `.prose`                    |
| Autor               | "RODRÍGUEZ, RODRÍGUEZ, Julián; ..."       |
| Año de publicación  | "2024"                                      |
| Lugar de publicación| "Lanzarote"                                |
| Editorial           | "Cabildo de Lanzarote..."                  |
| ISBN                | "978-84-128811-3-4"                        |
| Dentro de           | "XIX Jornadas de Estudios..."              |
| Ámbito geográfico   | "Sin Concretar" / "Yaiza"                  |
| Periodo             | "1981-1990" (en fotografías)               |
| Tipo de fotografía  | "Retrato exterior individual" (fotos)      |
| Documento           | Enlace de descarga (PDF)                   |

## 4. ¿Renderizado con JavaScript?

**Parcialmente.** El contenido principal (título, metadatos, descripción) se renderiza
del lado del servidor y está disponible en el HTML estático. No se detectaron
frameworks SPA (React, Vue, Svelte) embebidos como aplicación completa,
aunque hay clases de Tailwind CSS y Svelte (`svelte-tn6d3a`).

El listado de documentos también se renderiza server-side con los 40 items por página
visibles en el HTML.

**Implicación:** El Fetcher HTTP estándar es suficiente; no se necesita un navegador headless.

## 5. ¿Tiene API interna?

**No se encontró una API JSON pública.** El backend en `bk.memoriadelanzarote.com`
sirve archivos de medios (imágenes, PDFs) pero no expone endpoints API.
Las rutas `/api/*` devuelven 404.

El contenido se obtiene directamente del HTML renderizado.

## 6. Observaciones sobre robots.txt

```
user-agent: *
disallow: /aviso-legal/
disallow: /politica-privacidad/
disallow: /politica-cookies/
disallow: /busqueda-avanzada/

sitemap: https://memoriadelanzarote.com/sitemap.xml
```

- **Permite acceso** a `/documentos`, `/item/*`, `/imagenes`, `/audios`, etc.
- **Tiene sitemap** en `/sitemap.xml` (útil para descubrimiento completo).
- Solo bloquea páginas legales y la búsqueda avanzada.

## 7. Volumen estimado

- **~1000 documentos** en la sección "Documentos" (25 páginas × 40 items/página).
- Secciones adicionales: imágenes, audios, colecciones (no contabilizadas aún).
- Cada documento tiene entre 500 y 5000 palabras de contenido textual.
