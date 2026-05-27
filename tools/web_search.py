"""Web search tool — connects SkyNet to the internet.
Uses DuckDuckGo (curl) — no API key needed.
"""

import json
import urllib.parse
import subprocess
import re
from skynet.registry import registry


# ─── Helpers ─────────────────────────────────────────────────────────────


def _run_curl(url: str, timeout: int = 10) -> str:
    """Fetch a URL via curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-m", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"


def _extract_text(html: str, max_chars: int = 4000) -> str:
    """Very rough HTML-to-text extraction."""
    # Remove scripts and styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]


# ─── Tools ───────────────────────────────────────────────────────────────


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo (no API key needed).

    Args:
        query: The search query
        max_results: Maximum number of results to return (1-10)
    """
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"

    html = _run_curl(url)
    if not html or html.startswith("Error"):
        return html or "No results"

    # Extract results from DuckDuckGo HTML
    results = []
    # Find result blocks
    blocks = re.findall(
        r'<a rel="nofollow" class="result__a" href="(.*?)".*?>(.*?)</a>',
        html, re.DOTALL,
    )
    snippets = re.findall(
        r'<a class="result__snippet".*?>(.*?)</a>',
        html, re.DOTALL,
    )

    for i, (href, title) in enumerate(blocks[:max_results]):
        title_text = re.sub(r'<[^>]+>', '', title).strip()
        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
        results.append({
            "title": title_text,
            "url": href,
            "snippet": snippet,
        })

    return json.dumps({"results": results})


def web_fetch(url: str, max_chars: int = 4000) -> str:
    """Fetch and extract the text content of a URL.

    Args:
        url: The URL to fetch
        max_chars: Maximum characters to return
    """
    html = _run_curl(url)
    if html.startswith("Error"):
        return html

    text = _extract_text(html, max_chars)
    return json.dumps({
        "url": url,
        "content": text,
        "char_count": len(text),
    })


def web_search_news(query: str, max_results: int = 5) -> str:
    """Search news using DuckDuckGo.

    Args:
        query: The news search query
        max_results: Maximum number of results (1-10)
    """
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}&ia=news"

    html = _run_curl(url)
    if not html or html.startswith("Error"):
        return html or "No results"

    results = []
    blocks = re.findall(
        r'<a rel="nofollow" class="result__a" href="(.*?)".*?>(.*?)</a>',
        html, re.DOTALL,
    )
    snippets = re.findall(
        r'<a class="result__snippet".*?>(.*?)</a>',
        html, re.DOTALL,
    )

    for i, (href, title) in enumerate(blocks[:max_results]):
        title_text = re.sub(r'<[^>]+>', '', title).strip()
        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
        results.append({
            "title": title_text,
            "url": href,
            "snippet": snippet,
        })

    return json.dumps({"results": results})


# ─── Register ────────────────────────────────────────────────────────────

registry.register("web_search", web_search, {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query"},
        "max_results": {"type": "integer", "description": "Max results (1-10)", "default": 5},
    },
    "required": ["query"],
}, "Search the web using DuckDuckGo (no API key needed)", "web")

registry.register("web_fetch", web_fetch, {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "URL to fetch"},
        "max_chars": {"type": "integer", "description": "Max chars to return", "default": 4000},
    },
    "required": ["url"],
}, "Fetch and extract text content from a URL", "web")

registry.register("web_search_news", web_search_news, {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "News search query"},
        "max_results": {"type": "integer", "description": "Max results (1-10)", "default": 5},
    },
    "required": ["query"],
}, "Search news using DuckDuckGo", "web")
