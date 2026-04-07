"""Tests para parser/html_parser.py."""

from parser.html_parser import (
    extract_text_by_selectors,
    extract_first_match,
    extract_meta_tag,
    clean_markdown,
    extract_links_from_html
)

def test_extract_text_by_selectors():
    html = '<html><body><div class="author">César Manrique</div><div class="author">Otro</div></body></html>'
    res = extract_text_by_selectors(html, [".author"])
    assert res == "César Manrique Otro"

def test_extract_first_match_priority():
    html = '<html><body><div class="secondary">Segundo</div></body></html>'
    res = extract_first_match(html, [".primary", ".secondary"])
    assert res == "Segundo"

def test_extract_meta_tag():
    html = '<html><head><meta name="description" content="Una descripción"><meta property="og:title" content="Título OG"></head></html>'
    assert extract_meta_tag(html, "description") == "Una descripción"
    assert extract_meta_tag(html, "og:title") == "Título OG"
    assert extract_meta_tag(html, "missing") is None

def test_clean_markdown_removes_images():
    md = "# Hola\n\n![alt](https://img.com)\n\nMás texto."
    cleaned = clean_markdown(md)
    assert cleaned == "# Hola\n\nMás texto."
    assert "![alt]" not in cleaned

def test_clean_markdown_collapses_whitespace():
    md = "Párrafo 1\n\n\n\n\nPárrafo 2\n\n\n\nPárrafo 3"
    cleaned = clean_markdown(md)
    assert cleaned == "Párrafo 1\n\nPárrafo 2\n\nPárrafo 3"

def test_clean_markdown_removes_boilerplate():
    md = "[Volver al inicio](/)\n\nTexto útil.\n\nCopyright © 2023."
    cleaned = clean_markdown(md)
    assert cleaned == "Texto útil."

def test_extract_links_from_html():
    html = '''
    <a href="/pagina1">Paginación</a>
    <div class="content"><a href="https://externo.com/1">Ext</a></div>
    <a href="#ancla">Ignorar</a>
    '''
    # Sin selector
    links1 = extract_links_from_html(html, "https://base.com")
    assert links1 == ["https://base.com/pagina1", "https://externo.com/1"]
    
    # Con selector
    links2 = extract_links_from_html(html, "https://base.com", selector=".content")
    assert links2 == ["https://externo.com/1"]
