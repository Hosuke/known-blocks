"""Web research plugin — searches for and ingests documents about unknown concepts.

When the knowledge base encounters a broken wiki-link or an unfamiliar concept,
this plugin searches the web for authoritative sources and ingests the best result.
This is the "curiosity" executor — filling gaps in the knowledge graph.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .config import load_config, ensure_dirs

logger = logging.getLogger("llmbase.web_research")

# Prefer these domains for blockchain/DeFi knowledge
PREFERRED_DOMAINS = [
    "ethereum.org",
    "docs.uniswap.org",
    "docs.aave.com",
    "docs.compound.finance",
    "docs.makerdao.com",
    "docs.lido.fi",
    "docs.eigenlayer.xyz",
    "chainlink.com",
    "chain.link",
    "l2beat.com",
    "defillama.com",
    "ethresear.ch",
    "eips.ethereum.org",
    "blog.ethereum.org",
    "vitalik.eth.limo",
    "paradigm.xyz",
    "a16zcrypto.com",
    "messari.io",
    "wiki.polygon.technology",
    "docs.arbitrum.io",
    "docs.optimism.io",
    "docs.base.org",
    "docs.scroll.io",
    "docs.linea.build",
    "docs.starknet.io",
    "docs.zksync.io",
]

HEADERS = {"User-Agent": "KnownBlocks/1.0 (Knowledge Base)"}


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-")


def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo for relevant pages. Returns list of {title, url, snippet}."""
    try:
        # Use DuckDuckGo HTML version (no API key needed)
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for result in soup.select(".result"):
            title_el = result.select_one(".result__title a")
            snippet_el = result.select_one(".result__snippet")
            if title_el:
                href = title_el.get("href", "")
                # DuckDuckGo wraps URLs in redirects
                if "uddg=" in href:
                    from urllib.parse import unquote, parse_qs, urlparse
                    parsed = urlparse(href)
                    qs = parse_qs(parsed.query)
                    href = unquote(qs.get("uddg", [href])[0])
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        logger.error(f"Search failed for '{query}': {e}")
        return []


def _score_result(result: dict) -> int:
    """Score a search result by source authority. Higher is better."""
    url = result.get("url", "")
    score = 0
    for domain in PREFERRED_DOMAINS:
        if domain in url:
            score += 10
            break
    # Prefer docs pages
    if "/docs/" in url or "/documentation/" in url:
        score += 5
    # Penalize forums, social media
    if any(d in url for d in ["reddit.com", "twitter.com", "x.com", "medium.com"]):
        score -= 5
    return score


def _fetch_and_convert(url: str) -> tuple[str, str]:
    """Fetch a URL and convert to markdown. Returns (title, content)."""
    from .ingest import _validate_url
    _validate_url(url)

    resp = requests.get(url, timeout=30, headers=HEADERS, allow_redirects=True)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract title
    title = ""
    title_el = soup.find("title")
    if title_el:
        title = title_el.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # Remove nav, footer, scripts
    for tag in soup.find_all(["nav", "footer", "script", "style", "aside", "header"]):
        tag.decompose()

    # Find main content
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if not main:
        return title, ""

    content = md(str(main), heading_style="ATX", strip=["img"])
    # Clean up excessive whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)
    return title, content.strip()


def research_concept(concept: str, base_dir: Path | None = None) -> Path | None:
    """Search for a blockchain/DeFi concept and ingest the best result.

    Used by the orchestrator when it encounters broken wiki-links
    or missing foundational concepts.
    """
    cfg = load_config(base_dir)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    # Check if already researched
    slug = f"research-{_slugify(concept)}"
    doc_dir = raw_dir / slug
    if (doc_dir / "index.md").exists():
        return None

    # Search with blockchain context
    query = f"{concept} blockchain crypto DeFi explained"
    results = _search_duckduckgo(query)

    if not results:
        logger.warning(f"No search results for concept: {concept}")
        return None

    # Score and pick best result
    results.sort(key=_score_result, reverse=True)
    best = results[0]

    logger.info(f"[research] '{concept}' → {best['url']}")

    try:
        title, content = _fetch_and_convert(best["url"])
    except Exception as e:
        logger.error(f"Failed to fetch {best['url']}: {e}")
        return None

    if not content or len(content) < 100:
        logger.warning(f"Content too short from {best['url']}")
        return None

    # Write raw document
    doc_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(content)
    post.metadata["title"] = title or concept
    post.metadata["source"] = best["url"]
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "web_research"
    post.metadata["concept"] = concept
    post.metadata["compiled"] = False

    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    logger.info(f"[research] Ingested '{concept}' from {best['url']}")
    return doc_path


def research_protocol(protocol_name: str, base_dir: Path | None = None) -> Path | None:
    """Search for a specific protocol's documentation and ingest it."""
    cfg = load_config(base_dir)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    slug = f"research-{_slugify(protocol_name)}"
    doc_dir = raw_dir / slug
    if (doc_dir / "index.md").exists():
        return None

    # Search for official docs
    query = f"{protocol_name} protocol documentation official docs"
    results = _search_duckduckgo(query)

    if not results:
        return None

    results.sort(key=_score_result, reverse=True)
    best = results[0]

    try:
        title, content = _fetch_and_convert(best["url"])
    except Exception as e:
        logger.error(f"Failed to fetch {best['url']}: {e}")
        return None

    if not content or len(content) < 100:
        return None

    doc_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(content)
    post.metadata["title"] = title or protocol_name
    post.metadata["source"] = best["url"]
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "web_research"
    post.metadata["concept"] = protocol_name
    post.metadata["compiled"] = False

    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return doc_path
