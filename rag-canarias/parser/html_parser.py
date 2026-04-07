"""Utilidades de parsing HTML complementarias a crawl4ai.

crawl4ai genera markdown limpio automáticamente. Este módulo
proporciona funciones auxiliares para:
- Extraer metadatos específicos del HTML crudo (BeautifulSoup).
- Limpiar markdown generado por crawl4ai (eliminar ruido residual).
- Extraer elementos concretos del HTML cuando los selectores CSS
  de crawl4ai no son suficientes.
"""

from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


def extract_text_by_selectors(html: str, selectors: list[str]) -> str:
    """Extrae texto combinado de uno o más selectores CSS.
    
    Útil para extraer metadatos que crawl4ai no captura en el markdown.
    
    Args:
        html: HTML crudo de la página.
        selectors: Lista de selectores CSS a probar, en orden de prioridad.
        
    Returns:
        Texto combinado de los elementos encontrados, o cadena vacía.
    """
    soup = BeautifulSoup(html, "lxml")
    for selector in selectors:
        elements = soup.select(selector)
        if elements:
            return " ".join([el.get_text(strip=True) for el in elements if el.get_text(strip=True)])
    return ""


def extract_first_match(html: str, selectors: list[str]) -> str | None:
    """Devuelve el texto del primer selector CSS que tenga coincidencia.
    
    Args:
        html: HTML crudo.
        selectors: Lista de selectores a probar en orden.
        
    Returns:
        Texto del primer match, o None si ninguno coincide.
    """
    soup = BeautifulSoup(html, "lxml")
    for selector in selectors:
        el = soup.select_one(selector)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return None


def extract_meta_tag(html: str, name: str) -> str | None:
    """Extrae el contenido de un meta tag por nombre o property.
    
    Busca <meta name="..." content="..."> y <meta property="..." content="...">.
    
    Args:
        html: HTML crudo.
        name: Nombre o property del meta tag (ej: "description", "og:title").
        
    Returns:
        Contenido del meta tag, o None.
    """
    soup = BeautifulSoup(html, "lxml")
    
    tag = soup.find("meta", attrs={"name": name})
    if tag and tag.get("content"):
        return tag["content"]
        
    tag = soup.find("meta", attrs={"property": name})
    if tag and tag.get("content"):
        return tag["content"]
        
    return None


def clean_markdown(markdown: str) -> str:
    """Limpia markdown generado por crawl4ai.
    
    Operaciones:
    - Eliminar líneas que sean solo imágenes markdown (![...](...)). 
    - Eliminar líneas de navegación ("Ver más", "Volver", enlaces sueltos).
    - Colapsar múltiples líneas vacías en máximo dos.
    - Eliminar espacios trailing.
    - Eliminar bloques de boilerplate común (copyright, cookies, etc.).
    
    Args:
        markdown: Markdown generado por crawl4ai.
        
    Returns:
        Markdown limpio.
    """
    if not markdown:
        return ""
        
    lines = markdown.splitlines()
    cleaned_lines = []
    
    # regex matches exact format ![alt](url)
    image_pattern = re.compile(r'^!\[.*?\]\(.*?\)$')
    
    nav_keywords = {"ver más", "volver", "volver al inicio", "atrás"}
    
    for line in lines:
        stripped = line.strip()
        
        # Remove single image lines
        if image_pattern.match(stripped):
            continue
            
        # Optional: remove bare links if they are just navigation
        if stripped.startswith("[") and stripped.endswith(")") and stripped.count("[") == 1:
            inner_text = stripped[1:stripped.find("]")]
            if inner_text.lower() in nav_keywords:
                continue
                
        # Skip pure boilerplate (basic regex or exact match depending on needs)
        lower = stripped.lower()
        if "todos los derechos reservados" in lower or "copyright ©" in lower:
            continue
            
        cleaned_lines.append(stripped)
        
    # Collapse multiple newlines (more than 2 consecutive) to exactly 2
    joined = "\n".join(cleaned_lines)
    joined = re.sub(r'\n{3,}', '\n\n', joined)
    return joined.strip()


def extract_links_from_html(html: str, base_url: str,
                             selector: str | None = None) -> list[str]:
    """Extrae URLs absolutas de enlaces en el HTML.
    
    Útil para el descubrimiento de URLs en los conectores.
    
    Args:
        html: HTML crudo.
        base_url: URL base para resolver enlaces relativos.
        selector: Selector CSS opcional para limitar dónde buscar enlaces.
        
    Returns:
        Lista de URLs absolutas.
    """
    soup = BeautifulSoup(html, "lxml")
    
    if selector:
        elements = soup.select(selector)
        links = []
        for el in elements:
            links.extend(el.find_all("a", href=True))
    else:
        links = soup.find_all("a", href=True)
        
    urls = []
    for link in links:
        href = link.get("href")
        if href and not href.startswith(("javascript:", "mailto:", "tel:", "#")):
            full_url = urljoin(base_url, href)
            urls.append(full_url)
            
    # return deduplicated
    # maintaining order
    seen = set()
    result = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
            
    return result
