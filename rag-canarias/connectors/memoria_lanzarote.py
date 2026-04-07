"""Conector para Memoria de Lanzarote (memoriadelanzarote.com).

Fuente documental con 943+ registros sobre historia, patrimonio,
urbanismo y cultura de Lanzarote. Incluye textos, imágenes, vídeos y datos.
"""

from bs4 import BeautifulSoup
from typing import Optional
import json

from config.settings import SourceConfig, Settings
from crawler.fetcher import Fetcher
from crawler.robots import RobotsChecker
from storage.models import RawDocument, Metadata
from connectors.base import BaseConnector

class MemoriaLanzaroteConnector(BaseConnector):
    """Conector específico para Memoria de Lanzarote.
    
    Estrategia de descubrimiento: usa la API JSON interna.
    Extracción: usa markdown generado por crawl4ai + metadatos CSS.
    """
    
    VERSION = "1.0"
    
    def discover_urls(self, limit: int | None = None) -> list[str]:
        """Descubre URLs navegando por la web principal y extrayendo enlaces."""
        from parser.html_parser import extract_links_from_html
        urls = []
        
        url = "https://memoriadelanzarote.com/documentos"
        raw_doc = self.fetcher.fetch(url)
        all_links = extract_links_from_html(raw_doc.html, url)
        
        seen = set()
        for link in all_links:
            if "/item/" in link and link not in seen:
                seen.add(link)
                urls.append(link)
                if limit and len(urls) >= limit:
                    break
                    
        return urls

    def get_crawl_config(self) -> dict:
        """Configuración de crawling para Memoria de Lanzarote.
        
        Returns:
            Dict con parámetros de CrawlerRunConfig.
        """
        return {
            "css_selector": ", ".join(self.source_config.content_selectors),
            "excluded_tags": ["nav", "footer", "header", "aside", "script", "style"],
            "word_count_threshold": 10,
            "remove_overlay_elements": True,
        }
    
    def extract_title(self, raw_doc: RawDocument) -> str:
        """Extrae el título del documento."""
        soup = BeautifulSoup(raw_doc.html, "lxml")
        
        # Estrategia 1: h1
        h1 = soup.find("h1")
        if h1 and h1.text.strip():
            return h1.text.strip()
            
        # Estrategia 2: title
        title_tag = soup.find("title")
        if title_tag and title_tag.text.strip():
            return title_tag.text.strip()
            
        # Estrategia 3: First heading from raw markdown
        if raw_doc.markdown_raw:
            for line in raw_doc.markdown_raw.splitlines():
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
                    
        # Estrategia 4: URL slug fallback
        from urllib.parse import urlparse
        path = urlparse(raw_doc.url).path
        pieces = path.strip("/").split("/")
        if pieces:
            return pieces[-1].replace("-", " ")
        return ""
    
    def extract_content(self, raw_doc: RawDocument) -> str:
        """Extrae el contenido textual principal."""
        content = raw_doc.markdown_fit if raw_doc.markdown_fit else raw_doc.markdown_raw
        
        if not content:
            soup = BeautifulSoup(raw_doc.html, "lxml")
            body = soup.find("body")
            content = body.get_text(separator="\n\n") if body else ""
        
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            
            # Quitar links crudos que solo sirven de navegación
            if stripped.startswith("[") and stripped.endswith(")]") and stripped.count("[") == 1:
                inner_text = stripped[1:stripped.find("]")]
                if inner_text.lower() in ("ver más", "volver", "inicio", "atrás"):
                    continue
                    
            lines.append(stripped)
            
        return "\n".join(lines)

    def extract_metadata(self, raw_doc: RawDocument) -> Metadata:
        """Extrae metadatos específicos de Memoria de Lanzarote."""
        soup = BeautifulSoup(raw_doc.html, "lxml")
        
        author = None
        published_date = None
        category = None
        
        for p in soup.find_all(["p", "div", "span", "li"]):
            text = p.get_text(separator=" ", strip=True)
            text_upper = text.upper()
            
            if "AUTOR:" in text_upper:
                idx = text_upper.find("AUTOR:")
                author = text[idx + 6:].split("\n")[0].strip()
            elif "PERIODO:" in text_upper:
                idx = text_upper.find("PERIODO:")
                published_date = text[idx + 8:].split("\n")[0].strip()
            elif "FECHA:" in text_upper:
                idx = text_upper.find("FECHA:")
                published_date = text[idx + 6:].split("\n")[0].strip()
            elif "COLECCIÓN:" in text_upper:
                idx = text_upper.find("COLECCIÓN:")
                category = text[idx + 10:].split("\n")[0].strip()
                
        breadcrumbs = soup.select(".breadcrumb li, .breadcrumbs li")
        if breadcrumbs and len(breadcrumbs) > 1 and not category:
            category = breadcrumbs[-2].get_text(strip=True)
            
        return Metadata(
            author=author,
            published_date=published_date,
            category=category,
            island="Lanzarote",
            content_type="article",
            extra={}
        )
