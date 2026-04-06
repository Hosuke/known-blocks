"""Ethereum.org developer docs plugin — incremental ingestion.

Fetches Ethereum developer documentation from the ethereum-org-website
GitHub repository (raw markdown) and saves them for later LLM compilation.
Designed for progressive learning: each run picks a batch of unread pages.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import requests

from .config import load_config, ensure_dirs

BASE_RAW_URL = (
    "https://raw.githubusercontent.com/ethereum/ethereum-org-website"
    "/master/public/content/developers/docs"
)

# (path_segment, human_title)
SITEMAP = [
    ("intro-to-ethereum", "Introduction to Ethereum"),
    ("intro-to-ether", "Introduction to Ether"),
    ("web2-vs-web3", "Web2 vs Web3"),
    ("accounts", "Ethereum Accounts"),
    ("transactions", "Transactions"),
    ("blocks", "Blocks"),
    ("evm", "Ethereum Virtual Machine (EVM)"),
    ("gas", "Gas and Fees"),
    ("nodes-and-clients", "Nodes and Clients"),
    ("networks", "Networks"),
    ("consensus-mechanisms", "Consensus Mechanisms"),
    ("consensus-mechanisms/pos", "Proof-of-Stake"),
    ("consensus-mechanisms/pow", "Proof-of-Work"),
    ("networking-layer", "Networking Layer"),
    ("data-structures-and-encoding", "Data Structures"),
    ("smart-contracts", "Smart Contracts"),
    ("smart-contracts/languages", "Smart Contract Languages"),
    ("smart-contracts/anatomy", "Anatomy of Smart Contracts"),
    ("smart-contracts/deploying", "Deploying Smart Contracts"),
    ("smart-contracts/security", "Smart Contract Security"),
    ("smart-contracts/formal-verification", "Formal Verification"),
    ("smart-contracts/composability", "Composability"),
    ("standards/tokens", "Token Standards"),
    ("standards/tokens/erc-20", "ERC-20 Token Standard"),
    ("standards/tokens/erc-721", "ERC-721 NFT Standard"),
    ("standards/tokens/erc-1155", "ERC-1155 Multi Token"),
    ("standards/tokens/erc-4626", "ERC-4626 Tokenized Vault"),
    ("oracles", "Oracles"),
    ("scaling", "Scaling"),
    ("scaling/optimistic-rollups", "Optimistic Rollups"),
    ("scaling/zk-rollups", "Zero-Knowledge Rollups"),
    ("scaling/sidechains", "Sidechains"),
    ("scaling/plasma", "Plasma"),
    ("scaling/validium", "Validium"),
    ("bridges", "Bridges"),
    ("mev", "MEV"),
    ("dapps", "Dapps"),
    ("storage", "Decentralized Storage"),
    ("ides", "Development IDEs"),
]


# ─── Progress tracking ─────────────────────────────────────

def _get_progress_file(base_dir: Path) -> Path:
    """Get path to the progress tracking file."""
    meta_dir = Path(load_config(base_dir)["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir / "ethdocs_progress.json"


def _load_progress(base_dir: Path) -> dict:
    """Load ingestion progress."""
    pf = _get_progress_file(base_dir)
    if pf.exists():
        return json.loads(pf.read_text())
    return {"ingested_pages": [], "total_ingested": 0, "last_run": None}


def _save_progress(base_dir: Path, progress: dict):
    """Save ingestion progress."""
    pf = _get_progress_file(base_dir)
    pf.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


# ─── Helpers ────────────────────────────────────────────────

def _path_to_slug(url_path: str) -> str:
    """Convert a sitemap path to a filesystem slug.

    e.g. 'smart-contracts/security' -> 'ethdocs-smart-contracts-security'
    """
    return "ethdocs-" + url_path.replace("/", "-")


def _path_to_section(url_path: str) -> str:
    """Extract the top-level section from a path."""
    return url_path.split("/")[0]


# ─── Ingestion ──────────────────────────────────────────────

def ingest_doc(url_path: str, base_dir: Path | None = None) -> Path | None:
    """Fetch a single ethereum.org doc page and save to raw/.

    Args:
        url_path: path segment from SITEMAP, e.g. 'smart-contracts/security'
        base_dir: project root (defaults to cwd)

    Returns:
        Path to the saved document, or None if already ingested or fetch failed.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    slug = _path_to_slug(url_path)
    doc_dir = raw_dir / slug

    # Skip if already ingested
    if (doc_dir / "index.md").exists():
        return None

    # Fetch raw markdown from GitHub
    fetch_url = f"{BASE_RAW_URL}/{url_path}/index.md"
    try:
        resp = requests.get(fetch_url, timeout=30)
        resp.raise_for_status()
    except Exception:
        return None

    content = resp.text
    if not content or len(content) < 50:
        return None

    # If the source file itself has frontmatter, strip it and keep only the body
    # so we can write our own clean frontmatter.
    try:
        parsed = frontmatter.loads(content)
        body = parsed.content
        # Grab title from source frontmatter if available
        source_title = parsed.metadata.get("title", "")
    except Exception:
        body = content
        source_title = ""

    # Look up human title from sitemap; fall back to source frontmatter
    title = ""
    for path, label in SITEMAP:
        if path == url_path:
            title = label
            break
    if not title:
        title = source_title or url_path

    # Write raw doc
    doc_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body)
    post.metadata["title"] = title
    post.metadata["source"] = f"https://ethereum.org/en/developers/docs/{url_path}/"
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "ethdocs"
    post.metadata["section"] = _path_to_section(url_path)
    post.metadata["compiled"] = False

    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return doc_path


def learn(batch_size: int = 5, base_dir: Path | None = None) -> list[str]:
    """Progressive learning: ingest next batch of unread Ethereum doc pages.

    Each call picks the next ``batch_size`` pages from the SITEMAP that have
    not yet been ingested. Call repeatedly to absorb all pages over time.

    Returns:
        List of url_path strings that were successfully ingested.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    progress = _load_progress(base)
    ingested_set = set(progress["ingested_pages"])

    # Filter out already ingested
    pending = [path for path, _label in SITEMAP if path not in ingested_set]

    if not pending:
        return []

    batch = pending[:batch_size]
    results: list[str] = []

    for url_path in batch:
        doc_path = ingest_doc(url_path, base)
        if doc_path:
            results.append(url_path)
            ingested_set.add(url_path)

        time.sleep(1)  # Rate-limit: be respectful to GitHub

    # Save progress
    progress["ingested_pages"] = list(ingested_set)
    progress["total_ingested"] = len(ingested_set)
    progress["last_run"] = datetime.now(timezone.utc).isoformat()
    _save_progress(base, progress)

    return results


def status(base_dir: Path | None = None) -> dict:
    """Get current learning progress."""
    base = Path(base_dir) if base_dir else Path.cwd()
    progress = _load_progress(base)
    total_available = len(SITEMAP)
    total_ingested = progress["total_ingested"]
    return {
        "total_available": total_available,
        "total_ingested": total_ingested,
        "remaining": total_available - total_ingested,
        "last_run": progress.get("last_run"),
        "ingested_pages": progress["ingested_pages"],
    }
