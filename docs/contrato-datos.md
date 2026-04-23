# Contrato de datos: Web Forms → FastAPI

Interfaz HTTP entre el crawler C# (Web Forms, VM Windows ARM) y el pipeline RAG Python (macOS host).

---

## Endpoint de ingestión

```
POST http://<mac-ip>:8000/ingest/document
Content-Type: application/json
```

### Request body

```json
{
  "url":             "https://elmuseocanario.com/colecciones/prehistoria",
  "domain":          "elmuseocanario.com",
  "html_clean":      "<article>Texto limpio sin scripts ni estilos...</article>",
  "title":           "Colecciones — Prehistoria",
  "http_status":     200,
  "depth":           2,
  "fetched_at":      "2026-04-23T10:00:00Z",
  "crawler_version": "csharp-webforms-1.0"
}
```

| Campo            | Tipo    | Requerido | Descripción |
|------------------|---------|-----------|-------------|
| `url`            | string  | ✓         | URL canónica de la página (sin fragmento) |
| `domain`         | string  | ✓         | Dominio raíz sin `www.` ni protocolo |
| `html_clean`     | string  | ✓         | HTML ya limpiado por HtmlAgilityPack (sin scripts/styles/nav) |
| `title`          | string  | —         | Título extraído del `<title>` o `<h1>` |
| `http_status`    | int     | —         | Código HTTP de la respuesta (default 200) |
| `depth`          | int     | —         | Profundidad BFS desde la semilla (default 0) |
| `fetched_at`     | string  | ✓         | ISO 8601 UTC del momento de descarga |
| `crawler_version`| string  | —         | Versión del crawler para trazabilidad |

### Response 200

```json
{
  "doc_id":  "a3f4c2...64hex...",
  "status":  "received",
  "message": "Queued for processing"
}
```

| Campo    | Valores posibles             | Descripción |
|----------|------------------------------|-------------|
| `status` | `received` / `duplicate` / `error` | Estado del documento ingestado |
| `doc_id` | SHA-256 hex (64 chars)       | ID determinista: `SHA256(domain + "\|" + canonical_url)` |

### Errores

| Código | Motivo |
|--------|--------|
| 422    | Request body inválido (Pydantic validation) |
| 500    | Error interno del servidor |

---

## Endpoint de salud

```
GET http://<mac-ip>:8000/health
```

```json
{"status": "ok", "timestamp": "2026-04-23T10:05:00Z"}
```

---

## Endpoint de consulta (Phase 3, stub ahora)

```
POST http://<mac-ip>:8000/query
Content-Type: application/json
```

```json
{
  "question":      "¿Qué es el silbo gomero?",
  "top_k":         6,
  "source_filter": null
}
```

```json
{
  "answer": "El silbo gomero es...",
  "citations": [
    {
      "doc_id": "a3f4c2...",
      "url":    "https://...",
      "title":  "Silbo Gomero — Patrimonio UNESCO",
      "snippet": "El silbo gomero es un lenguaje silbado...",
      "score":   0.92
    }
  ],
  "latency_ms": 840
}
```

---

## Notas de implementación (C# side — pendiente VM)

```csharp
// RagApiClient.cs — adaptación Web Forms
private static readonly HttpClient _http = new HttpClient
{
    BaseAddress = new Uri(ConfigurationManager.AppSettings["RagApiBaseUrl"])
};

public async Task<IngestDocumentResponse> SendDocumentAsync(IngestDocumentRequest req)
{
    var json = JsonSerializer.Serialize(req);
    var content = new StringContent(json, Encoding.UTF8, "application/json");
    var response = await _http.PostAsync("/ingest/document", content);
    response.EnsureSuccessStatusCode();
    var body = await response.Content.ReadAsStringAsync();
    return JsonSerializer.Deserialize<IngestDocumentResponse>(body);
}
```

En `Web.config`:
```xml
<appSettings>
  <add key="RagApiBaseUrl" value="http://192.168.64.1:8000" />
</appSettings>
```

> La IP `192.168.64.1` es el gateway UTM desde la VM. Verifícala con `ipconfig` en la VM
> y busca el adaptador "UTM" o similar.

---

## doc_id — cómo se calcula

```python
import hashlib
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

TRACKING_PARAMS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","fbclid","gclid","ref","source"}

def canonical_url(url: str) -> str:
    p = urlparse(url)
    qs = {k: v for k, v in parse_qs(p.query, keep_blank_values=True).items()
          if k.lower() not in TRACKING_PARAMS}
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme, p.netloc, path, p.params, urlencode(qs, doseq=True), ""))

def doc_id(domain: str, url: str) -> str:
    return hashlib.sha256(f"{domain}|{canonical_url(url)}".encode()).hexdigest()
```

El C# debe producir el mismo hash para facilitar la deduplicación cruzada (futuro).
