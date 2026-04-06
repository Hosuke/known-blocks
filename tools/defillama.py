"""DefiLlama plugin — ingest DeFi protocol and chain metadata.

Uses DefiLlama's free public API (no auth required) to build
knowledge about the DeFi ecosystem: protocols, chains, and categories.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import frontmatter

from .config import load_config, ensure_dirs

BASE_URL = "https://api.llama.fi"
HEADERS = {"User-Agent": "LLMBase/1.0 (https://github.com/Hosuke/llmbase)"}

PROGRESS_FILE = "defillama_progress.json"


def _load_progress(meta_dir: Path) -> dict:
    """Load progress state from disk."""
    path = meta_dir / PROGRESS_FILE
    if path.exists():
        return json.loads(path.read_text())
    return {
        "ingested_protocols": [],
        "ingested_chains": [],
        "ingested_categories": [],
        "total_ingested": 0,
        "last_run": None,
    }


def _save_progress(meta_dir: Path, progress: dict):
    """Persist progress state."""
    progress["total_ingested"] = (
        len(progress["ingested_protocols"])
        + len(progress["ingested_chains"])
        + len(progress["ingested_categories"])
    )
    progress["last_run"] = datetime.now(timezone.utc).isoformat()
    path = meta_dir / PROGRESS_FILE
    path.write_text(json.dumps(progress, indent=2))


def _fetch_protocols() -> list[dict]:
    """GET /protocols — full protocol list."""
    resp = requests.get(f"{BASE_URL}/protocols", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _fetch_protocol_detail(slug: str) -> dict:
    """GET /protocol/{slug} — detailed protocol info."""
    resp = requests.get(f"{BASE_URL}/protocol/{slug}", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _fetch_chains() -> list[dict]:
    """GET /v2/chains — all chains."""
    resp = requests.get(f"{BASE_URL}/v2/chains", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _format_tvl(tvl: float | int | None) -> str:
    """Human-readable TVL string."""
    if tvl is None:
        return "N/A"
    if tvl >= 1_000_000_000:
        return f"${tvl / 1_000_000_000:.2f}B"
    if tvl >= 1_000_000:
        return f"${tvl / 1_000_000:.2f}M"
    if tvl >= 1_000:
        return f"${tvl / 1_000:.1f}K"
    return f"${tvl:,.0f}"


def ingest_protocol(slug: str, base_dir: Path | None = None) -> Path | None:
    """Fetch and save one protocol as a markdown document.

    Args:
        slug: DefiLlama protocol slug (e.g. "aave").
        base_dir: Project root directory.

    Returns:
        Path to the saved document, or None on failure.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    doc_slug = f"protocol-{slug}"
    doc_dir = raw_dir / doc_slug

    # Skip if already ingested
    if (doc_dir / "index.md").exists():
        return None

    try:
        data = _fetch_protocol_detail(slug)
    except Exception:
        return None

    name = data.get("name", slug)
    description = data.get("description", "")
    category = data.get("category", "Unknown")
    chains = data.get("chains", [])
    tvl = data.get("currentChainTvls", {})
    total_tvl = sum(v for k, v in tvl.items() if not k.startswith("pool2") and not k.startswith("staking") and isinstance(v, (int, float)))
    if total_tvl == 0:
        total_tvl = data.get("tvl", [{}])
        if isinstance(total_tvl, list) and total_tvl:
            total_tvl = total_tvl[-1].get("totalLiquidityUSD", 0)
        elif not isinstance(total_tvl, (int, float)):
            total_tvl = 0
    website = data.get("url", "")
    twitter = data.get("twitter", "")
    audit_links = data.get("audit_links", [])
    gecko_id = data.get("gecko_id", "")

    # Build chains display string
    chains_display = ", ".join(chains[:15])
    if len(chains) > 15:
        chains_display += f", ... ({len(chains)} total)"

    # Build markdown body
    body_parts = [f"# {name}\n"]

    if description:
        body_parts.append(f"{description}\n")

    body_parts.append(f"## Category\n{category}\n")

    body_parts.append(f"## Chains\nDeployed on: {chains_display}\n")

    body_parts.append("## Key Metrics")
    body_parts.append(f"- Total Value Locked: {_format_tvl(total_tvl)}")
    if website:
        body_parts.append(f"- Website: {website}")
    if twitter:
        body_parts.append(f"- Twitter: https://twitter.com/{twitter}")
    if gecko_id:
        body_parts.append(f"- CoinGecko ID: {gecko_id}")
    body_parts.append("")

    if audit_links:
        body_parts.append("## Audits")
        for link in audit_links[:5]:
            body_parts.append(f"- {link}")
        body_parts.append("")

    if description:
        body_parts.append(f"## Description\n{description}\n")

    content = "\n".join(body_parts)

    # Build frontmatter
    post = frontmatter.Post(content)
    post.metadata["title"] = name
    post.metadata["source"] = f"https://defillama.com/protocol/{slug}"
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "defillama_protocol"
    post.metadata["protocol"] = slug
    post.metadata["category"] = category
    post.metadata["chains"] = chains[:20]
    post.metadata["compiled"] = False

    doc_dir.mkdir(parents=True, exist_ok=True)
    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return doc_path


def ingest_chain(chain_name: str, base_dir: Path | None = None) -> Path | None:
    """Fetch and save one chain as a markdown document.

    Args:
        chain_name: Chain name (e.g. "Ethereum").
        base_dir: Project root directory.

    Returns:
        Path to the saved document, or None on failure.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    slug = f"chain-{chain_name.lower()}"
    doc_dir = raw_dir / slug

    if (doc_dir / "index.md").exists():
        return None

    # Fetch all chains and find the matching one
    try:
        all_chains = _fetch_chains()
    except Exception:
        return None

    chain_data = None
    for c in all_chains:
        if c.get("name", "").lower() == chain_name.lower():
            chain_data = c
            break

    if chain_data is None:
        return None

    name = chain_data.get("name", chain_name)
    tvl = chain_data.get("tvl", 0)
    gecko_id = chain_data.get("gecko_id", "")
    token_symbol = chain_data.get("tokenSymbol", "")
    cmc_id = chain_data.get("cmcId", "")

    body_parts = [f"# {name}\n"]
    body_parts.append(f"{name} is a blockchain network tracked by DefiLlama.\n")

    body_parts.append("## Key Metrics")
    body_parts.append(f"- Total Value Locked: {_format_tvl(tvl)}")
    if token_symbol:
        body_parts.append(f"- Native Token: {token_symbol}")
    if gecko_id:
        body_parts.append(f"- CoinGecko ID: {gecko_id}")
    body_parts.append("")

    content = "\n".join(body_parts)

    post = frontmatter.Post(content)
    post.metadata["title"] = name
    post.metadata["source"] = f"https://defillama.com/chain/{name}"
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "defillama_chain"
    post.metadata["chain"] = name
    post.metadata["compiled"] = False

    doc_dir.mkdir(parents=True, exist_ok=True)
    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return doc_path


def learn_categories(base_dir: Path | None = None) -> list[str]:
    """Learn DeFi categories from protocol data.

    Fetches all protocols, extracts unique categories, and creates a
    summary document for each category listing its top protocols.

    Returns:
        List of category names that were ingested.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])
    meta_dir = Path(cfg["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)

    progress = _load_progress(meta_dir)

    try:
        protocols = _fetch_protocols()
    except Exception:
        return []

    # Group protocols by category
    categories: dict[str, list[dict]] = {}
    for p in protocols:
        cat = p.get("category", None)
        if not cat:
            continue
        categories.setdefault(cat, []).append(p)

    # Sort protocols within each category by TVL
    for cat in categories:
        categories[cat].sort(key=lambda x: x.get("tvl", 0) or 0, reverse=True)

    ingested = set(progress["ingested_categories"])
    results = []

    for cat_name, cat_protocols in sorted(categories.items()):
        slug = f"defi-category-{cat_name.lower().replace(' ', '-').replace('/', '-')}"

        if slug in ingested:
            continue

        doc_dir = raw_dir / slug
        if (doc_dir / "index.md").exists():
            ingested.add(slug)
            continue

        # Build markdown
        top = cat_protocols[:20]
        body_parts = [f"# {cat_name}\n"]
        body_parts.append(
            f"{cat_name} is a DeFi category tracked by DefiLlama "
            f"with {len(cat_protocols)} protocols.\n"
        )

        total_tvl = sum(p.get("tvl", 0) or 0 for p in cat_protocols)
        body_parts.append("## Overview")
        body_parts.append(f"- Total protocols: {len(cat_protocols)}")
        body_parts.append(f"- Combined TVL: {_format_tvl(total_tvl)}")
        body_parts.append("")

        body_parts.append("## Top Protocols")
        for p in top:
            p_tvl = _format_tvl(p.get("tvl", 0))
            p_name = p.get("name", "Unknown")
            p_chains = ", ".join((p.get("chains") or [])[:5])
            body_parts.append(f"- **{p_name}** — TVL: {p_tvl} — Chains: {p_chains}")
        body_parts.append("")

        content = "\n".join(body_parts)

        post = frontmatter.Post(content)
        post.metadata["title"] = f"DeFi Category: {cat_name}"
        post.metadata["source"] = f"https://defillama.com/protocols/{cat_name}"
        post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
        post.metadata["type"] = "defillama_category"
        post.metadata["category"] = cat_name
        post.metadata["protocol_count"] = len(cat_protocols)
        post.metadata["compiled"] = False

        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "index.md"
        doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")

        ingested.add(slug)
        results.append(cat_name)

    progress["ingested_categories"] = list(ingested)
    _save_progress(meta_dir, progress)

    return results


def learn(batch_size: int = 5, base_dir: Path | None = None) -> list[str]:
    """Progressive learning of DeFi protocols and chains by TVL rank.

    Each call ingests the next batch of top protocols (by TVL) that
    haven't been ingested yet, plus top chains on the first run.

    Args:
        batch_size: Number of protocols to ingest per call.
        base_dir: Project root directory.

    Returns:
        List of protocol slugs that were ingested.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    meta_dir = Path(cfg["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)

    progress = _load_progress(meta_dir)

    # Load config settings
    dl_cfg = cfg.get("defillama", {})
    min_tvl = dl_cfg.get("min_tvl", 1_000_000)
    top_n = dl_cfg.get("top_n", 50)

    # Fetch all protocols
    try:
        protocols = _fetch_protocols()
    except Exception:
        return []

    # Sort by TVL descending, filter by min_tvl, limit to top_n
    protocols.sort(key=lambda x: x.get("tvl", 0) or 0, reverse=True)
    protocols = [p for p in protocols[:top_n] if (p.get("tvl", 0) or 0) >= min_tvl]

    ingested_set = set(progress["ingested_protocols"])

    # Filter out already ingested
    pending = [p for p in protocols if p.get("slug", "") not in ingested_set]

    if not pending:
        _save_progress(meta_dir, progress)
        return []

    batch = pending[:batch_size]
    results = []

    for proto in batch:
        slug = proto.get("slug", "")
        if not slug:
            continue
        try:
            path = ingest_protocol(slug, base)
            if path:
                results.append(slug)
                ingested_set.add(slug)
        except Exception:
            pass
        time.sleep(0.5)

    progress["ingested_protocols"] = list(ingested_set)

    # First run: also ingest top chains
    if not progress["ingested_chains"]:
        try:
            chains = _fetch_chains()
            chains.sort(key=lambda x: x.get("tvl", 0) or 0, reverse=True)
            top_chains = chains[:10]
            time.sleep(0.5)
            for chain in top_chains:
                name = chain.get("name", "")
                if not name:
                    continue
                try:
                    ingest_chain(name, base)
                    progress["ingested_chains"].append(name.lower())
                except Exception:
                    pass
                time.sleep(0.5)
        except Exception:
            pass

    _save_progress(meta_dir, progress)
    return results


def status(base_dir: Path | None = None) -> dict:
    """Get current learning progress."""
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    meta_dir = Path(cfg["paths"]["meta"])
    progress = _load_progress(meta_dir)
    return {
        "total_ingested": len(progress["ingested_protocols"]) + len(progress["ingested_chains"]),
        "ingested_protocols": len(progress["ingested_protocols"]),
        "ingested_chains": len(progress["ingested_chains"]),
        "last_run": progress.get("last_run"),
    }
