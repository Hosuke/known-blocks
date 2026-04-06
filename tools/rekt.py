"""Rekt.news plugin — learn blockchain security incidents.

Scrapes rekt.news articles about DeFi exploits, hacks, and security
incidents. Converts HTML to markdown for later LLM compilation.
Designed for progressive learning: each run picks a batch of unread articles.
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .config import load_config, ensure_dirs

BASE_URL = "https://rekt.news"
HEADERS = {"User-Agent": "LLMBase/1.0 (https://github.com/Hosuke/llmbase)"}


# ─── Progress tracking ─────────────────────────────────────

def _get_progress_file(base_dir: Path) -> Path:
    """Get path to the progress tracking file."""
    meta_dir = Path(load_config(base_dir)["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir / "rekt_progress.json"


def load_progress(base_dir: Path) -> dict:
    """Load ingestion progress."""
    pf = _get_progress_file(base_dir)
    if pf.exists():
        return json.loads(pf.read_text())
    return {
        "ingested_urls": [],
        "total_ingested": 0,
        "last_run": None,
        "last_page": 0,
    }


def save_progress(base_dir: Path, progress: dict):
    """Save ingestion progress."""
    pf = _get_progress_file(base_dir)
    pf.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


# ─── Scraping helpers ──────────────────────────────────────

def _discover_articles(page: int = 1) -> list[dict]:
    """Scrape article links from rekt.news listing page.

    Args:
        page: page number (1-indexed)

    Returns:
        List of dicts with 'url', 'title', 'slug' keys.
    """
    if page <= 1:
        url = BASE_URL + "/"
    else:
        url = f"{BASE_URL}/page/{page}/"

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []

    # rekt.news uses anchor tags linking to articles; find them
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Article links are relative paths like /article-slug/
        if not href or href in ("/", "#"):
            continue
        # Filter to article-like paths (single slug segment)
        clean = href.strip("/")
        if not clean or "/" in clean:
            continue
        # Skip navigation links
        if clean in ("page", "leaderboard", "about"):
            continue
        if re.match(r"^page$", clean):
            continue

        title_text = link.get_text(strip=True)
        if not title_text or len(title_text) < 3:
            continue

        full_url = f"{BASE_URL}/{clean}/"
        articles.append({
            "url": full_url,
            "slug": clean,
            "title": title_text,
        })

    # Deduplicate by slug while preserving order
    seen = set()
    unique = []
    for a in articles:
        if a["slug"] not in seen:
            seen.add(a["slug"])
            unique.append(a)

    return unique


def _fetch_article(url: str) -> dict | None:
    """Fetch and parse a single rekt.news article.

    Returns:
        Dict with 'title', 'content' (markdown), 'url', or None on failure.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract title
    title_el = soup.find("h1")
    title = title_el.get_text(strip=True) if title_el else ""

    # Extract article body — rekt.news typically uses <article> or a main content div
    article_el = soup.find("article")
    if not article_el:
        # Fallback: look for main content area
        article_el = soup.find("main") or soup.find("div", class_=re.compile(r"content|post|article", re.I))
    if not article_el:
        return None

    # Convert HTML to markdown
    content = md(str(article_el), heading_style="ATX", strip=["img", "script", "style"])

    # Clean up excessive whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = content.strip()

    if len(content) < 50:
        return None

    if not title:
        # Try to extract from URL slug
        slug = url.strip("/").split("/")[-1]
        title = slug.replace("-", " ").title()

    return {
        "title": title,
        "content": content,
        "url": url,
    }


def _guess_protocol(title: str) -> str:
    """Try to extract protocol name from article title.

    rekt.news titles often follow patterns like:
    'Protocol Name - REKT', 'Protocol Name - REKT 2', etc.
    """
    # Common pattern: "Protocol - REKT"
    match = re.match(r"^(.+?)\s*[-\u2013\u2014]\s*[Rr][Ee][Kk][Tt]", title)
    if match:
        return match.group(1).strip()
    # Fallback: use the full title
    return ""


# ─── Ingestion ──────────────────────────────────────────────

def ingest_article(url: str, base_dir: Path | None = None) -> Path | None:
    """Fetch a single rekt.news article and save to raw/.

    Args:
        url: full article URL, e.g. 'https://rekt.news/ronin-rekt/'
        base_dir: project root (defaults to cwd)

    Returns:
        Path to the saved document, or None on failure.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    # Derive slug from URL
    article_slug = url.strip("/").split("/")[-1]
    slug = f"rekt-{article_slug}"
    doc_dir = raw_dir / slug

    # Skip if already ingested
    if (doc_dir / "index.md").exists():
        return None

    article = _fetch_article(url)
    if not article:
        return None

    protocol = _guess_protocol(article["title"])

    doc_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(article["content"])
    post.metadata["title"] = article["title"]
    post.metadata["source"] = url
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "rekt"
    if protocol:
        post.metadata["protocol"] = protocol
    post.metadata["compiled"] = False

    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return doc_path


def learn(batch_size: int = 3, base_dir: Path | None = None) -> list[str]:
    """Progressive learning: ingest next batch of rekt.news articles.

    Each call discovers articles from the next unread listing page and
    ingests up to ``batch_size`` new articles. Call repeatedly to absorb
    more content over time.

    Returns:
        List of article URLs that were successfully ingested.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    progress = load_progress(base)
    ingested_set = set(progress["ingested_urls"])

    # Start from the next page after the last one we scanned
    current_page = progress.get("last_page", 0) + 1
    results: list[str] = []
    pages_scanned = 0
    max_pages = 5  # Don't scan too many pages in one run

    while len(results) < batch_size and pages_scanned < max_pages:
        try:
            articles = _discover_articles(current_page)
        except Exception:
            break

        if not articles:
            break  # No more pages

        time.sleep(2)  # Rate limit between page fetches

        for article_info in articles:
            if len(results) >= batch_size:
                break

            url = article_info["url"]
            if url in ingested_set:
                continue

            doc_path = ingest_article(url, base)
            if doc_path:
                results.append(url)
                ingested_set.add(url)

            time.sleep(2)  # Rate limit between article fetches

        current_page += 1
        pages_scanned += 1

    # Save progress
    progress["ingested_urls"] = list(ingested_set)
    progress["total_ingested"] = len(ingested_set)
    progress["last_run"] = datetime.now(timezone.utc).isoformat()
    progress["last_page"] = current_page - 1
    save_progress(base, progress)

    return results


def status(base_dir: Path | None = None) -> dict:
    """Get current learning progress."""
    base = Path(base_dir) if base_dir else Path.cwd()
    progress = load_progress(base)
    total_ingested = progress["total_ingested"]
    return {
        "total_ingested": total_ingested,
        "last_page_scanned": progress.get("last_page", 0),
        "last_run": progress.get("last_run"),
        "ingested_urls": progress["ingested_urls"],
    }
