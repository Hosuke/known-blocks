"""Dune Spellbook browser plugin — occasional reference browsing.

Reads SQL model files and YAML source definitions from a local clone of the
Dune Spellbook repository to understand on-chain data structures and protocol
event schemas.  This is *not* a primary learning source — think of it as
flipping through a reference book.  Each ``learn()`` call randomly samples a
few protocols that haven't been browsed yet and generates summary documents.
"""

import glob as _glob
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import yaml

from .config import load_config, ensure_dirs

DEFAULT_SPELLBOOK_PATH = "/Users/hosuke/Connector/Python/spellbook"


# ─── Progress Tracking ─────────────────────────────────────────

def _get_progress_file(base_dir: Path) -> Path:
    meta_dir = Path(load_config(base_dir)["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir / "spellbook_progress.json"


def _load_progress(base_dir: Path) -> dict:
    pf = _get_progress_file(base_dir)
    if pf.exists():
        return json.loads(pf.read_text())
    return {"browsed_protocols": [], "total_browsed": 0, "last_run": None}


def _save_progress(base_dir: Path, progress: dict):
    pf = _get_progress_file(base_dir)
    pf.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


# ─── Discovery ─────────────────────────────────────────────────

def _discover_protocols(spellbook_path: str) -> list[str]:
    """Find all protocol names from the sources/ and models/ directories."""
    sp = Path(spellbook_path)
    protocols: set[str] = set()

    # From sources/
    sources_dir = sp / "sources"
    if sources_dir.is_dir():
        for child in sources_dir.iterdir():
            if child.is_dir() and not child.name.startswith("_"):
                protocols.add(child.name)

    # From dbt_subprojects/daily_spellbook/models/_projects/
    models_dir = sp / "dbt_subprojects" / "daily_spellbook" / "models" / "_projects"
    if models_dir.is_dir():
        for child in models_dir.iterdir():
            if child.is_dir() and not child.name.startswith("_"):
                protocols.add(child.name)

    return sorted(protocols)


# ─── Parsing helpers ───────────────────────────────────────────

def _parse_source_yamls(yml_files: list[str]) -> tuple[list[dict], list[str]]:
    """Parse source YAML files, returning (tables_info, chains).

    Each table_info dict: {"source_name": str, "table_name": str,
                           "columns": list[dict], "chain": str}
    """
    tables: list[dict] = []
    chains: set[str] = set()

    for yf in yml_files:
        yp = Path(yf)
        # Infer chain from directory structure: sources/{protocol}/{chain}/...
        parts = yp.parts
        try:
            # Find protocol dir, chain is typically the next segment
            for i, part in enumerate(parts):
                if part == "sources" and i + 2 < len(parts):
                    chain = parts[i + 2]
                    if not chain.endswith(".yml"):
                        chains.add(chain)
                    break
        except (IndexError, ValueError):
            pass

        try:
            with open(yf) as f:
                data = yaml.safe_load(f)
        except Exception:
            continue

        if not data or not isinstance(data, dict):
            continue

        for source in data.get("sources", []):
            if not isinstance(source, dict):
                continue
            source_name = source.get("name", "")
            for table in source.get("tables", []):
                if not isinstance(table, dict):
                    continue
                table_name = table.get("name", "")
                columns = []
                for col in table.get("columns", []):
                    if isinstance(col, dict):
                        columns.append({
                            "name": col.get("name", ""),
                            "description": col.get("description", ""),
                        })
                tables.append({
                    "source_name": source_name,
                    "table_name": table_name,
                    "columns": columns,
                    "chain": chain if chains else "",
                })

    return tables, sorted(chains)


def _parse_sql_models(sql_files: list[str]) -> list[dict]:
    """Read the first 50 lines of each SQL model to extract metadata.

    Returns list of dicts: {"filename": str, "comment": str, "columns": list[str]}
    """
    models: list[dict] = []

    for sf in sql_files:
        sp = Path(sf)
        try:
            lines = sp.read_text(encoding="utf-8", errors="replace").splitlines()[:50]
        except Exception:
            continue

        header = "\n".join(lines)

        # Extract comments (lines starting with -- or blocks in /* */)
        comment_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("--"):
                comment_lines.append(stripped.lstrip("- ").strip())
            elif stripped.startswith("/*"):
                comment_lines.append(stripped.lstrip("/* ").strip())
            elif stripped.startswith("*") and not stripped.startswith("*/"):
                comment_lines.append(stripped.lstrip("* ").strip())

        comment = " ".join(c for c in comment_lines if c)[:200]

        # Try to find column names from SELECT block
        columns: list[str] = []
        col_pattern = re.findall(r'(?:,\s*|\bSELECT\s+)(\w+)\b', header, re.IGNORECASE)
        # Filter out SQL keywords
        sql_keywords = {
            "SELECT", "FROM", "WHERE", "AND", "OR", "AS", "ON", "JOIN",
            "LEFT", "RIGHT", "INNER", "OUTER", "GROUP", "BY", "ORDER",
            "UNION", "ALL", "DISTINCT", "CASE", "WHEN", "THEN", "ELSE",
            "END", "NOT", "IN", "IS", "NULL", "LIKE", "BETWEEN", "EXISTS",
            "HAVING", "LIMIT", "OFFSET", "WITH", "IF", "ref", "config",
        }
        for col in col_pattern:
            if col.upper() not in sql_keywords and col not in columns:
                columns.append(col)

        models.append({
            "filename": sp.stem,
            "comment": comment,
            "columns": columns[:20],  # Cap at 20
        })

    return models


# ─── Ingestion ─────────────────────────────────────────────────

def ingest_protocol(
    protocol_name: str,
    spellbook_path: str,
    base_dir: Path | None = None,
) -> Path | None:
    """Summarize a single protocol's on-chain data structures.

    Returns the path to the saved document, or None on failure.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    slug = f"spellbook-{protocol_name}"
    doc_dir = raw_dir / slug

    # Skip if already ingested
    if (doc_dir / "index.md").exists():
        return None

    sp = Path(spellbook_path)

    # Find source YAMLs
    yml_pattern = str(sp / "sources" / protocol_name / "**" / "*.yml")
    yml_files = _glob.glob(yml_pattern, recursive=True)

    # Find model SQL files
    sql_pattern = str(
        sp / "dbt_subprojects" / "daily_spellbook" / "models" / "**"
        / protocol_name / "**" / "*.sql"
    )
    sql_files = _glob.glob(sql_pattern, recursive=True)

    # Nothing found — skip silently
    if not yml_files and not sql_files:
        return None

    # Parse sources
    source_tables, chains = _parse_source_yamls(yml_files)

    # Parse models
    models = _parse_sql_models(sql_files)

    # ── Build markdown summary ──────────────────────────────

    chains_str = ", ".join(chains) if chains else "unknown"
    title = f"{protocol_name} - On-Chain Data Structure"

    body_parts: list[str] = []
    body_parts.append(f"# {protocol_name} — On-Chain Data Overview\n")

    # Chains
    body_parts.append("## Chains")
    body_parts.append(f"Deployed on: {chains_str}\n")

    # Smart Contract Events
    if source_tables:
        body_parts.append("## Smart Contract Events")
        for tbl in source_tables:
            name = tbl["table_name"]
            cols = tbl["columns"]
            # Build a short description from column info
            col_desc = ""
            if cols:
                col_names = [c["name"] for c in cols[:5] if c["name"]]
                if col_names:
                    col_desc = f" (columns: {', '.join(col_names)})"
            body_parts.append(f"- {name}{col_desc}")
        body_parts.append("")

    # Data Models
    if models:
        body_parts.append("## Data Models")
        for m in models:
            desc = f": {m['comment']}" if m["comment"] else ""
            body_parts.append(f"- {m['filename']}{desc}")
        body_parts.append("")

    # Sector guess (simple heuristic)
    sector = _guess_sector(protocol_name, source_tables, models)
    if sector:
        body_parts.append("## Sector")
        body_parts.append(f"{sector} (based on spellbook classification)\n")

    body = "\n".join(body_parts)

    # ── Write frontmatter document ──────────────────────────
    doc_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body)
    post.metadata["title"] = title
    post.metadata["source"] = f"spellbook://{protocol_name}"
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "spellbook_protocol"
    post.metadata["protocol"] = protocol_name
    post.metadata["chains"] = chains
    post.metadata["compiled"] = False

    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return doc_path


def _guess_sector(
    protocol_name: str,
    source_tables: list[dict],
    models: list[dict],
) -> str:
    """Rough heuristic to guess the protocol's sector."""
    all_text = protocol_name.lower()
    for t in source_tables:
        all_text += " " + t["table_name"].lower()
    for m in models:
        all_text += " " + m["filename"].lower()

    if any(kw in all_text for kw in ("swap", "trade", "pair", "pool", "dex", "amm")):
        return "DEX"
    if any(kw in all_text for kw in ("lend", "borrow", "supply", "repay", "atoken")):
        return "Lending"
    if any(kw in all_text for kw in ("nft", "erc721", "mint", "collection")):
        return "NFT"
    if any(kw in all_text for kw in ("bridge", "relay", "cross")):
        return "Bridge"
    if any(kw in all_text for kw in ("stake", "staking", "validator", "deposit")):
        return "Staking"
    if any(kw in all_text for kw in ("oracle", "price_feed", "keeper")):
        return "Oracle"
    if any(kw in all_text for kw in ("govern", "vote", "proposal", "dao")):
        return "Governance"
    return ""


# ─── Public API ────────────────────────────────────────────────

def learn(batch_size: int = 3, base_dir: Path | None = None) -> list[str]:
    """Randomly browse a few protocols from the local Spellbook repo.

    Each call picks ``batch_size`` protocols that haven't been browsed yet,
    summarizes their on-chain data structures, and saves them as raw documents.

    Returns:
        List of protocol names that were successfully ingested.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    spellbook_path = cfg.get("spellbook", {}).get("path", DEFAULT_SPELLBOOK_PATH)

    if not Path(spellbook_path).is_dir():
        return []

    progress = _load_progress(base)
    browsed_set = set(progress["browsed_protocols"])

    all_protocols = _discover_protocols(spellbook_path)
    pending = [p for p in all_protocols if p not in browsed_set]

    if not pending:
        return []

    # Random sample for the "flipping through a reference book" feel
    batch = random.sample(pending, min(batch_size, len(pending)))
    results: list[str] = []

    for protocol in batch:
        path = ingest_protocol(protocol, spellbook_path, base)
        if path:
            results.append(protocol)
        # Mark as browsed even if nothing was found
        browsed_set.add(protocol)

    # Save progress
    progress["browsed_protocols"] = sorted(browsed_set)
    progress["total_browsed"] = len(browsed_set)
    progress["last_run"] = datetime.now(timezone.utc).isoformat()
    _save_progress(base, progress)

    return results


def status(base_dir: Path | None = None) -> dict:
    """Get current browsing progress."""
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    spellbook_path = cfg.get("spellbook", {}).get("path", DEFAULT_SPELLBOOK_PATH)

    progress = _load_progress(base)

    total_available = 0
    if Path(spellbook_path).is_dir():
        total_available = len(_discover_protocols(spellbook_path))

    return {
        "total_available": total_available,
        "total_browsed": progress["total_browsed"],
        "remaining": total_available - progress["total_browsed"],
        "last_run": progress.get("last_run"),
        "recent_protocols": progress["browsed_protocols"][-20:],
    }
