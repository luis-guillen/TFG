from __future__ import annotations

import re
import unicodedata

import trafilatura
from bs4 import BeautifulSoup


def html_to_text(html: str, url: str = "") -> str:
    """Extract clean text from HTML. Tries trafilatura first, falls back to BS4."""
    text = trafilatura.extract(
        html,
        url=url,
        include_tables=True,
        include_links=False,
        output_format="txt",
        favor_recall=True,
        no_fallback=False,
    )
    if not text or len(text.strip()) < 80:
        text = _bs4_extract(html)
    return _clean(text or "")


def _bs4_extract(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
