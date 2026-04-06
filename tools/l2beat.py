"""L2Beat plugin — learn L2 ecosystem knowledge from L2Beat API.

Fetches L2 scaling project data from the L2Beat summary API and generates
descriptive markdown documents for each project. Designed for progressive
learning: each run picks a batch of unprocessed projects.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import requests

from .config import load_config, ensure_dirs

API_SUMMARY = "https://l2beat.com/api/scaling/summary"
HEADERS = {"User-Agent": "LLMBase/1.0 (https://github.com/Hosuke/llmbase)"}

PRIORITY_L2S = [
    "arbitrum", "optimism", "base", "blast", "mantle",
    "linea", "scroll", "zksync-era", "starknet",
    "polygon-zkevm", "manta-pacific", "mode",
]

# Category normalization for frontmatter tech field
TECH_MAP = {
    "Optimistic Rollup": "optimistic_rollup",
    "ZK Rollup": "zk_rollup",
    "Validium": "validium",
    "Optimium": "optimium",
    "Plasma": "plasma",
}


# ─── Progress tracking ─────────────────────────────────────

def _get_progress_file(base_dir: Path) -> Path:
    """Get path to the progress tracking file."""
    meta_dir = Path(load_config(base_dir)["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir / "l2beat_progress.json"


def load_progress(base_dir: Path) -> dict:
    """Load ingestion progress."""
    pf = _get_progress_file(base_dir)
    if pf.exists():
        return json.loads(pf.read_text())
    return {"ingested_slugs": [], "total_ingested": 0, "last_run": None}


def save_progress(base_dir: Path, progress: dict):
    """Save ingestion progress."""
    pf = _get_progress_file(base_dir)
    pf.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


# ─── API helpers ───────────────────────────────────────────

def _fetch_summary() -> dict:
    """Fetch L2Beat scaling summary API."""
    resp = requests.get(API_SUMMARY, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _format_tvl(tvl_value: float | int | None) -> str:
    """Format TVL as human-readable string."""
    if tvl_value is None:
        return "N/A"
    if tvl_value >= 1_000_000_000:
        return f"${tvl_value / 1_000_000_000:.2f} B"
    if tvl_value >= 1_000_000:
        return f"${tvl_value / 1_000_000:.2f} M"
    return f"${tvl_value:,.0f}"


def _extract_project_data(project: dict) -> dict:
    """Extract relevant fields from a project entry in the API response."""
    name = project.get("name", "Unknown")
    slug = project.get("slug", "")
    category = project.get("category", "Unknown")
    provider = project.get("provider", None)
    purposes = project.get("purposes", [])
    stage = project.get("stage", None)

    # TVL extraction — API shape may vary; try common paths
    tvl = None
    tvl_data = project.get("tvl", {})
    if isinstance(tvl_data, dict):
        tvl = tvl_data.get("value", tvl_data.get("total", None))
    elif isinstance(tvl_data, (int, float)):
        tvl = tvl_data

    return {
        "name": name,
        "slug": slug,
        "category": category,
        "provider": provider,
        "purposes": purposes if isinstance(purposes, list) else [str(purposes)],
        "stage": stage,
        "tvl": tvl,
    }


def _generate_markdown(data: dict) -> str:
    """Generate descriptive markdown body from project data."""
    name = data["name"]
    category = data["category"]
    provider = data["provider"]
    stage = data["stage"]
    purposes = ", ".join(data["purposes"]) if data["purposes"] else "Universal"
    tvl_str = _format_tvl(data["tvl"])

    provider_line = f" built on the {provider} stack" if provider else ""
    lines = [
        f"# {name}",
        "",
        f"{name} is a {category}{provider_line}.",
        "",
        "## Technology",
        f"- Type: {category}",
    ]
    if provider:
        lines.append(f"- Provider: {provider}")
    if stage:
        lines.append(f"- Stage: {stage}")

    lines += [
        "",
        "## Purposes",
        purposes,
        "",
        "## Total Value Locked",
        tvl_str,
    ]

    return "\n".join(lines)


# ─── Ingestion ──────────────────────────────────────────────

def ingest_l2(project_slug: str, base_dir: Path | None = None, _projects_cache: dict | None = None) -> Path | None:
    """Fetch L2Beat data for a single project and save to raw/.

    Args:
        project_slug: L2Beat project slug, e.g. 'arbitrum'
        base_dir: project root (defaults to cwd)
        _projects_cache: pre-fetched projects dict keyed by slug (avoids repeat API calls)

    Returns:
        Path to the saved document, or None on failure.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    slug = f"l2-{project_slug}"
    doc_dir = raw_dir / slug

    # Skip if already ingested
    if (doc_dir / "index.md").exists():
        return None

    # Fetch project data
    if _projects_cache and project_slug in _projects_cache:
        project_raw = _projects_cache[project_slug]
    else:
        try:
            summary = _fetch_summary()
        except Exception:
            return None
        # Find project in the response — API may return list or dict
        projects = summary.get("data", summary.get("projects", []))
        if isinstance(projects, dict):
            projects = list(projects.values())
        project_raw = None
        for p in projects:
            if p.get("slug") == project_slug:
                project_raw = p
                break
        if project_raw is None:
            return None

    data = _extract_project_data(project_raw)
    body = _generate_markdown(data)

    # Build frontmatter
    tech = TECH_MAP.get(data["category"], data["category"].lower().replace(" ", "_"))

    doc_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body)
    post.metadata["title"] = data["name"]
    post.metadata["source"] = f"https://l2beat.com/scaling/projects/{project_slug}"
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "l2beat"
    post.metadata["l2_name"] = data["name"]
    post.metadata["tech"] = tech
    if data["stage"]:
        post.metadata["stage"] = data["stage"]
    if data["provider"]:
        post.metadata["provider"] = data["provider"]
    post.metadata["compiled"] = False

    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return doc_path


def learn(batch_size: int = 5, base_dir: Path | None = None) -> list[str]:
    """Progressive learning: ingest next batch of L2 projects from L2Beat.

    Priority projects are ingested first, then remaining projects from the
    API in order.

    Returns:
        List of project slugs that were successfully ingested.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    progress = load_progress(base)
    ingested_set = set(progress["ingested_slugs"])

    # Fetch full project list from API
    try:
        summary = _fetch_summary()
    except Exception:
        return []

    projects_list = summary.get("data", summary.get("projects", []))
    if isinstance(projects_list, dict):
        projects_list = list(projects_list.values())

    # Build lookup by slug
    projects_by_slug: dict[str, dict] = {}
    all_slugs: list[str] = []
    for p in projects_list:
        s = p.get("slug")
        if s:
            projects_by_slug[s] = p
            all_slugs.append(s)

    # Order: priority first, then the rest
    ordered: list[str] = []
    for s in PRIORITY_L2S:
        if s in projects_by_slug:
            ordered.append(s)
    for s in all_slugs:
        if s not in ordered:
            ordered.append(s)

    # Filter out already ingested
    pending = [s for s in ordered if s not in ingested_set]

    if not pending:
        return []

    batch = pending[:batch_size]
    results: list[str] = []

    for project_slug in batch:
        doc_path = ingest_l2(project_slug, base, _projects_cache=projects_by_slug)
        if doc_path:
            results.append(project_slug)
            ingested_set.add(project_slug)
        time.sleep(1)

    # Save progress
    progress["ingested_slugs"] = list(ingested_set)
    progress["total_ingested"] = len(ingested_set)
    progress["last_run"] = datetime.now(timezone.utc).isoformat()
    save_progress(base, progress)

    return results


def status(base_dir: Path | None = None) -> dict:
    """Get current learning progress."""
    base = Path(base_dir) if base_dir else Path.cwd()
    progress = load_progress(base)
    total_ingested = progress["total_ingested"]
    return {
        "total_ingested": total_ingested,
        "priority_remaining": len([
            s for s in PRIORITY_L2S
            if s not in set(progress["ingested_slugs"])
        ]),
        "last_run": progress.get("last_run"),
        "ingested_slugs": progress["ingested_slugs"],
    }
