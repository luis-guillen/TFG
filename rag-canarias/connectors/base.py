"""Conector base para fuentes de datos.

Define la interfaz que todo conector debe implementar.
Patrón Template Method: run() orquesta el flujo,
los métodos abstractos se sobreescriben por fuente.
"""

from abc import ABC, abstractmethod
import logging
from typing import Generator

from config.settings import Settings, SourceConfig
from crawler.fetcher import Fetcher
from crawler.robots import RobotsChecker
from storage.models import RawDocument, ProcessedDocument, Metadata
from storage.models import generate_doc_id, generate_content_hash
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Clase abstracta para conectores de fuentes de datos.
    
    Cada fuente web del proyecto tiene un conector concreto que hereda
    de BaseConnector e implementa los métodos abstractos. El conector
    actúa como director: sabe qué URLs descubrir, qué selectores usar
    y cómo extraer metadatos específicos de su fuente.
    
    El flujo general es:
        discover_urls() → fetch (via Fetcher) → parse_document() → enrich()
    
    El método run() orquesta este flujo y NO debe sobreescribirse.
    """
    
    # Versión del conector. Incrementar al cambiar lógica de extracción.
    VERSION: str = "1.0"
    
    def __init__(self, source_config: SourceConfig, settings: Settings,
                 fetcher: Fetcher, robots_checker: RobotsChecker):
        """Inicializa el conector con sus dependencias.
        
        Args:
            source_config: Configuración de la fuente desde sources.yaml.
            settings: Configuración global del proyecto.
            fetcher: Cliente de crawling para descargar páginas.
            robots_checker: Verificador de robots.txt.
        """
        self.source_config = source_config
        self.settings = settings
        self.fetcher = fetcher
        self.robots_checker = robots_checker
        self.source_id = source_config.id
    
    @abstractmethod
    def discover_urls(self, limit: int | None = None) -> list[str]:
        """Descubre las URLs a procesar de esta fuente.
        
        Cada fuente tiene su propia estrategia: sitemap, paginación,
        archivo cronológico, navegación A-Z, etc.
        
        Args:
            limit: Número máximo de URLs a descubrir (None = todas).
            
        Returns:
            Lista de URLs absolutas a procesar.
        """
    
    @abstractmethod
    def get_crawl_config(self) -> dict:
        """Devuelve los parámetros de CrawlerRunConfig para esta fuente.
        
        Permite a cada conector personalizar el crawling: selectores CSS,
        tags excluidos, umbral de palabras, etc. Estos parámetros se
        pasan como **overrides al Fetcher.
        
        Returns:
            Dict con parámetros para CrawlerRunConfig. Ejemplo:
            {"css_selector": "article", "excluded_tags": ["nav", "footer"]}
        """
    
    @abstractmethod
    def extract_metadata(self, raw_doc: RawDocument) -> Metadata:
        """Extrae metadatos específicos de la fuente desde el documento descargado.
        
        Cada fuente tiene su propia estructura de metadatos.
        El conector sabe dónde encontrar autor, fecha, categoría, etc.
        
        Args:
            raw_doc: Documento descargado con HTML y markdown.
            
        Returns:
            Metadata con los campos extraídos.
        """
    
    @abstractmethod
    def extract_title(self, raw_doc: RawDocument) -> str:
        """Extrae el título del documento.
        
        Args:
            raw_doc: Documento descargado.
            
        Returns:
            Título del documento.
        """
    
    @abstractmethod
    def extract_content(self, raw_doc: RawDocument) -> str:
        """Extrae el contenido textual principal del documento.
        
        Con crawl4ai, esto normalmente es raw_doc.markdown_raw o
        raw_doc.markdown_fit, pero el conector puede procesarlo
        o limpiarlo adicionalmente.
        
        Args:
            raw_doc: Documento descargado.
            
        Returns:
            Texto limpio del contenido principal.
        """
    
    def parse_document(self, raw_doc: RawDocument) -> ProcessedDocument | None:
        """Convierte un RawDocument en ProcessedDocument.
        
        Método concreto que orquesta la extracción. Los conectores
        normalmente NO sobreescriben este método.
        
        Args:
            raw_doc: Documento descargado.
            
        Returns:
            ProcessedDocument listo para chunking, o None si se debe descartar.
        """
        try:
            title = self.extract_title(raw_doc)
            content = self.extract_content(raw_doc)
            metadata = self.extract_metadata(raw_doc)
            
            if not content or len(content.strip()) < 50:
                logger.warning(f"Contenido vacío o muy corto para {raw_doc.url}, descartando.")
                return None
            
            return ProcessedDocument(
                doc_id=generate_doc_id(self.source_id, raw_doc.url),
                source_id=self.source_id,
                url=raw_doc.url,
                title=title,
                content=content,
                content_hash=generate_content_hash(content),
                language="es",
                metadata=metadata,
                fetched_at=raw_doc.fetched_at,
                processed_at=datetime.now(timezone.utc),
                connector_version=self.VERSION,
            )
        except Exception as e:
            logger.error(f"Error procesando {raw_doc.url}: {e}")
            return None
    
    def run(self, limit: int | None = None) -> Generator[ProcessedDocument, None, None]:
        """Ejecuta el pipeline del conector: descubre URLs, descarga y procesa.
        
        Este es el método principal. NO sobreescribir.
        Devuelve un generador para procesar documentos uno a uno
        sin cargar todo en memoria.
        
        Args:
            limit: Número máximo de documentos a procesar.
            
        Yields:
            ProcessedDocument por cada documento procesado con éxito.
        """
        logger.info(f"Iniciando conector '{self.source_id}' (v{self.VERSION})")
        
        # 1. Descubrir URLs
        urls = self.discover_urls(limit=limit)
        logger.info(f"URLs descubiertas: {len(urls)}")
        
        # 2. Filtrar por robots.txt
        allowed_urls = [u for u in urls if self.robots_checker.is_allowed(u)]
        blocked = len(urls) - len(allowed_urls)
        if blocked > 0:
            logger.warning(f"URLs bloqueadas por robots.txt: {blocked}")
        
        # 3. Obtener configuración de crawling específica de la fuente
        crawl_config = self.get_crawl_config()
        
        # 4. Descargar y procesar cada URL
        processed = 0
        errors = 0
        for url in allowed_urls:
            try:
                raw_doc = self.fetcher.fetch(url, **crawl_config)
                doc = self.parse_document(raw_doc)
                if doc:
                    yield doc
                    processed += 1
            except Exception as e:
                logger.error(f"Error en {url}: {e}")
                errors += 1
        
        logger.info(
            f"Conector '{self.source_id}' finalizado. "
            f"Procesados: {processed}, Errores: {errors}, "
            f"Total URLs: {len(allowed_urls)}"
        )
