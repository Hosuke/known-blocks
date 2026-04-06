"""EIP/ERC plugin — incremental ingestion of Ethereum Improvement Proposals.

Fetches EIP and ERC standard documents from the ethereum/EIPs GitHub repository.
Designed for progressive learning: each run picks a batch of unprocessed EIPs,
ingests them as raw documents. Over time, the full standards library gets absorbed.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import requests

from .config import load_config, ensure_dirs

# ERCs moved to a separate repo in 2023
GITHUB_RAW_EIP = "https://raw.githubusercontent.com/ethereum/EIPs/master/EIPS/eip-{number}.md"
GITHUB_RAW_ERC = "https://raw.githubusercontent.com/ethereum/ERCs/master/ERCS/erc-{number}.md"
GITHUB_API_EIPS = "https://api.github.com/repos/ethereum/EIPs/contents/EIPS"

# High-value EIPs to learn first
PRIORITY_EIPS = [
    # Token standards
    20, 721, 1155, 4626, 2981,
    # Account & signature
    165, 712, 2612, 1271, 4337, 7702,
    # Core protocol
    1559, 4844, 2718, 2930, 7516,
    # NFT extensions
    6551, 5192,
    # DeFi patterns
    3156,  # Flash loans
    4524,  # Safer ERC-20
]

# EIP statuses we want, in priority order
DESIRED_STATUSES = {"Final", "Last Call", "Review", "Living", "Draft"}
SKIP_STATUSES = {"Withdrawn", "Stagnant", "Moved"}


# ─── Progress Tracking ─────────────────────────────────────────

def get_progress_file(base_dir: Path) -> Path:
    """Get path to the progress tracking file."""
    meta_dir = Path(load_config(base_dir)["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir / "eips_progress.json"


def load_progress(base_dir: Path) -> dict:
    """Load ingestion progress."""
    pf = get_progress_file(base_dir)
    if pf.exists():
        return json.loads(pf.read_text())
    return {"ingested_eips": [], "total_ingested": 0, "last_run": None}


def save_progress(base_dir: Path, progress: dict):
    """Save ingestion progress."""
    pf = get_progress_file(base_dir)
    pf.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


# ─── GitHub Fetching ───────────────────────────────────────────

def fetch_eip_content(number: int) -> frontmatter.Post | None:
    """Fetch a single EIP/ERC document from GitHub and parse its frontmatter.

    Tries the EIPs repo first; if the EIP has status 'Moved', tries the ERCs repo.
    """
    # Try EIPs repo first
    url = GITHUB_RAW_EIP.format(number=number)
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        post = frontmatter.loads(resp.text)
        # If moved to ERCs repo, follow the redirect
        if post.metadata.get("status", "").lower() == "moved":
            url2 = GITHUB_RAW_ERC.format(number=number)
            resp2 = requests.get(url2, timeout=30)
            if resp2.status_code == 200:
                return frontmatter.loads(resp2.text)
        return post
    # Fallback: try ERCs repo directly
    url = GITHUB_RAW_ERC.format(number=number)
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        return frontmatter.loads(resp.text)
    return None


def discover_eip_numbers() -> list[int]:
    """Discover available EIP numbers via the GitHub API."""
    numbers = []
    resp = requests.get(GITHUB_API_EIPS, timeout=30)
    if resp.status_code != 200:
        return numbers
    for entry in resp.json():
        name = entry.get("name", "")
        if name.startswith("eip-") and name.endswith(".md"):
            try:
                num = int(name[4:-3])
                numbers.append(num)
            except ValueError:
                continue
    return sorted(numbers)


# ─── Ingestion ─────────────────────────────────────────────────

def ingest_eip(number: int, base_dir: Path | None = None) -> Path | None:
    """Ingest a single EIP into the knowledge base.

    Returns the path to the saved document, or None if skipped/failed.
    """
    cfg = load_config(base_dir)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    slug = f"eip-{number}"
    doc_dir = raw_dir / slug
    if (doc_dir / "index.md").exists():
        return None  # Already ingested

    post = fetch_eip_content(number)
    if post is None:
        return None

    # Extract metadata from the EIP's own frontmatter
    eip_status = post.metadata.get("status", "")
    eip_category = post.metadata.get("category", "")
    eip_type = post.metadata.get("type", "")
    eip_title = post.metadata.get("title", f"EIP-{number}")

    # Skip undesirable statuses
    if eip_status in SKIP_STATUSES:
        return None

    # Build our own frontmatter for the raw document
    doc_dir.mkdir(parents=True, exist_ok=True)
    out = frontmatter.Post(post.content)
    out.metadata["title"] = f"EIP-{number}: {eip_title}"
    out.metadata["source"] = f"https://eips.ethereum.org/EIPS/eip-{number}"
    out.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    out.metadata["type"] = "eip"
    out.metadata["eip_number"] = number
    out.metadata["status"] = eip_status
    out.metadata["category"] = eip_category or eip_type
    out.metadata["compiled"] = False

    doc_path = doc_dir / "index.md"
    doc_path.write_text(frontmatter.dumps(out), encoding="utf-8")
    return doc_path


def learn(batch_size: int = 5, base_dir: Path | None = None) -> list[str]:
    """Progressive learning: ingest a batch of unprocessed EIPs.

    Each call picks the next `batch_size` EIPs not yet ingested.
    Priority EIPs are processed first, then Final/Last Call, then Draft.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    progress = load_progress(base)
    ingested_set = set(progress["ingested_eips"])

    # Phase 1: priority EIPs that haven't been ingested yet
    pending = [n for n in PRIORITY_EIPS if n not in ingested_set]

    # Phase 2: discover more EIPs from GitHub if we need more
    if len(pending) < batch_size:
        try:
            all_numbers = discover_eip_numbers()
        except Exception:
            all_numbers = []

        remaining = [n for n in all_numbers if n not in ingested_set and n not in pending]

        # Sort by status preference: fetch a sample to check status
        # For efficiency, just add them in numerical order — ingest_eip
        # will skip Withdrawn/Stagnant ones automatically
        pending.extend(remaining)

    if not pending:
        return []

    # Process batch
    batch = pending[:batch_size]
    results = []

    for number in batch:
        path = ingest_eip(number, base)
        if path:
            results.append(str(number))
            ingested_set.add(number)
        else:
            # Mark as seen even if skipped (withdrawn, already exists, etc.)
            ingested_set.add(number)

        time.sleep(1)  # Rate limit: be respectful to GitHub

    # Save progress
    progress["ingested_eips"] = sorted(ingested_set)
    progress["total_ingested"] = len(ingested_set)
    progress["last_run"] = datetime.now(timezone.utc).isoformat()
    save_progress(base, progress)

    return results


def status(base_dir: Path | None = None) -> dict:
    """Get current learning progress."""
    base = Path(base_dir) if base_dir else Path.cwd()
    progress = load_progress(base)
    ingested = progress["ingested_eips"]
    priority_done = [n for n in PRIORITY_EIPS if n in ingested]
    return {
        "total_ingested": progress["total_ingested"],
        "priority_done": f"{len(priority_done)}/{len(PRIORITY_EIPS)}",
        "last_run": progress.get("last_run"),
        "recent_eips": ingested[-20:],
    }
