"""Learning orchestrator — the brain that decides what to learn next.

Works like a curious researcher: checks what's missing, follows broken links,
tracks trends, and occasionally browses reference material out of curiosity.

Uses a priority queue model:
  P0: Foundation concepts missing (blockchain, EVM, gas, etc.)
  P1: Broken wiki-links (concepts referenced but no article exists)
  P2: Trending protocols not yet covered (DefiLlama top-N)
  P3: Structured traversal (EIPs, ethereum.org docs)
  P4: Deepen shallow articles (stubs)
  P5: Curiosity — random browsing (spellbook, rekt.news)
"""

import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config, ensure_dirs

logger = logging.getLogger("llmbase.orchestrator")

# Foundational concepts every blockchain knowledge base should cover
FOUNDATIONS = [
    "blockchain",
    "ethereum",
    "smart-contract",
    "evm",
    "gas",
    "consensus",
    "proof-of-stake",
    "proof-of-work",
    "erc-20",
    "erc-721",
    "defi",
    "amm",
    "lending-protocol",
    "flash-loan",
    "liquidity-pool",
    "oracle",
    "bridge",
    "layer-2",
    "rollup",
    "mev",
    "dao",
    "governance",
    "stablecoin",
    "yield-farming",
    "staking",
    "nft",
    "wallet",
    "private-key",
    "transaction",
    "block",
    "merkle-tree",
    "hash-function",
    "token",
    "dex",
    "cex",
    "impermanent-loss",
    "slippage",
    "tvl",
    "airdrop",
    "tokenomics",
    "liquid-staking",
    "restaking",
    "account-abstraction",
    "zero-knowledge-proof",
    "optimistic-rollup",
    "zk-rollup",
]


def _get_state_file(base_dir: Path) -> Path:
    meta_dir = Path(load_config(base_dir)["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir / "orchestrator_state.json"


def _load_state(base_dir: Path) -> dict:
    sf = _get_state_file(base_dir)
    if sf.exists():
        return json.loads(sf.read_text())
    return {
        "history": [],
        "total_learned": 0,
        "last_run": None,
    }


def _save_state(base_dir: Path, state: dict):
    sf = _get_state_file(base_dir)
    sf.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _article_exists(concept_slug: str, base_dir: Path) -> bool:
    """Check if a wiki article or raw doc exists for a concept (by slug or alias)."""
    cfg = load_config(base_dir)
    concepts_dir = Path(cfg["paths"]["concepts"])
    raw_dir = Path(cfg["paths"]["raw"])

    # Direct slug match (compiled article)
    if (concepts_dir / f"{concept_slug}.md").exists():
        return True

    # Check raw docs (already ingested, awaiting compilation)
    for prefix in ("foundation-", "research-", "curriculum-", ""):
        if (raw_dir / f"{prefix}{concept_slug}" / "index.md").exists():
            return True

    # Check aliases
    aliases_path = Path(cfg["paths"]["meta"]) / "aliases.json"
    if aliases_path.exists():
        try:
            aliases = json.loads(aliases_path.read_text())
            if concept_slug in aliases:
                return True
            # Also check if any alias maps to this slug
            for alias, target in aliases.items():
                if target == concept_slug:
                    return True
        except (json.JSONDecodeError, KeyError):
            pass

    return False


def _get_broken_links(base_dir: Path) -> list[str]:
    """Get broken wiki-links from the latest lint/health report."""
    cfg = load_config(base_dir)
    health_path = Path(cfg["paths"]["meta"]) / "health.json"
    if not health_path.exists():
        return []

    try:
        report = json.loads(health_path.read_text())
        results = report.get("results", {})
        broken = results.get("broken_links", [])
        # Each broken link entry is typically {"source": "article", "target": "missing-concept"}
        if isinstance(broken, list):
            targets = []
            for b in broken:
                if isinstance(b, dict):
                    targets.append(b.get("target", ""))
                elif isinstance(b, str):
                    targets.append(b)
            return [t for t in targets if t]
    except (json.JSONDecodeError, KeyError):
        pass
    return []


def _find_stub_articles(base_dir: Path) -> list[str]:
    """Find articles that are stubs or very short (need deepening)."""
    cfg = load_config(base_dir)
    concepts_dir = Path(cfg["paths"]["concepts"])
    if not concepts_dir.exists():
        return []

    stubs = []
    for md_file in concepts_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        # Consider it a stub if content is under 500 chars (excluding frontmatter)
        parts = content.split("---", 2)
        body = parts[2] if len(parts) >= 3 else content
        if len(body.strip()) < 500:
            stubs.append(md_file.stem)
    return stubs


# ─── Learning strategies ────────────────────────────────────

def _generate_foundation_doc(concept: str, base_dir: Path) -> Path | None:
    """Generate a raw document for a foundational concept using LLM knowledge.

    Fallback when web search is unavailable (e.g., DuckDuckGo blocked in China).
    """
    import frontmatter as fm
    from .llm import chat
    from .config import load_config, ensure_dirs

    cfg = load_config(base_dir)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    slug = f"foundation-{concept}"
    doc_dir = raw_dir / slug
    if (doc_dir / "index.md").exists():
        return doc_dir / "index.md"  # Already researched, return existing

    prompt = (
        f"Write a comprehensive educational article about '{concept}' in the context of "
        f"blockchain, cryptocurrency, and DeFi. Cover: definition, how it works, why it matters, "
        f"key examples, and relationship to other blockchain concepts.\n\n"
        f"Write in English. Be factual and authoritative. Target audience: someone learning "
        f"blockchain technology. Length: 800-1500 words."
    )

    try:
        content = chat(prompt, max_tokens=4096)
        if not content or len(content) < 200:
            return None
    except Exception as e:
        logger.error(f"LLM generation failed for {concept}: {e}")
        return None

    doc_dir.mkdir(parents=True, exist_ok=True)
    post = fm.Post(content)
    post.metadata["title"] = concept.replace("-", " ").title()
    post.metadata["source"] = "llm-generated"
    post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
    post.metadata["type"] = "foundation"
    post.metadata["concept"] = concept
    post.metadata["compiled"] = False

    doc_path = doc_dir / "index.md"
    doc_path.write_text(fm.dumps(post), encoding="utf-8")
    logger.info(f"[orchestrator] Generated foundation doc for '{concept}'")
    return doc_path


def _learn_foundations(batch_size: int, base_dir: Path) -> list[str]:
    """P0: Learn foundational concepts that are missing.

    Tries web research first; falls back to LLM generation if search fails.
    """
    from . import web_research

    missing = [c for c in FOUNDATIONS if not _article_exists(c, base_dir)]
    if not missing:
        return []

    results = []
    for concept in missing[:batch_size]:
        logger.info(f"[orchestrator] P0 foundation: {concept}")
        # Try web research first
        path = web_research.research_concept(concept, base_dir)
        if not path:
            # Fallback: generate from LLM knowledge
            logger.info(f"[orchestrator] Web search failed, using LLM generation for {concept}")
            path = _generate_foundation_doc(concept, base_dir)
        if path:
            results.append(concept)
        time.sleep(2)
    return results


def _learn_broken_links(batch_size: int, base_dir: Path) -> list[str]:
    """P1: Research concepts referenced in wiki but with no article."""
    from . import web_research

    broken = _get_broken_links(base_dir)
    if not broken:
        return []

    results = []
    for concept in broken[:batch_size]:
        logger.info(f"[orchestrator] P1 broken link: {concept}")
        path = web_research.research_concept(concept, base_dir)
        if not path:
            path = _generate_foundation_doc(concept, base_dir)
        if path:
            results.append(concept)
        time.sleep(2)
    return results


def _learn_curriculum(batch_size: int, base_dir: Path) -> list[str]:
    """P1.5: Learn from active theme curricula in dependency order."""
    try:
        from .curriculum import get_next_lessons, research_lesson

        lessons = get_next_lessons(batch_size, base_dir)
        if not lessons:
            return []

        results = []
        for lesson in lessons:
            meta = lesson.get("metadata", {})
            theme = meta.get("theme", "unknown") if meta else "unknown"
            slug = lesson["item_key"].split("/", 1)[-1]
            logger.info(f"[orchestrator] P1.5 curriculum [{theme}]: {slug}")
            path = research_lesson(lesson, base_dir)
            if path:
                results.append(slug)
            time.sleep(2)
        return results
    except Exception as e:
        logger.error(f"[orchestrator] Curriculum learning failed: {e}")
        return []


def _learn_trending(batch_size: int, base_dir: Path) -> list[str]:
    """P2: Learn about top DeFi protocols not yet covered."""
    try:
        from . import defillama
        return defillama.learn(batch_size=batch_size, base_dir=base_dir)
    except Exception as e:
        logger.error(f"[orchestrator] Trend learning failed: {e}")
        return []


def _learn_structured(batch_size: int, base_dir: Path) -> list[str]:
    """P3: Systematic traversal of EIPs and ethereum.org docs."""
    results = []
    half = max(1, batch_size // 2)

    # EIPs
    try:
        from . import eips
        r = eips.learn(batch_size=half, base_dir=base_dir)
        results.extend(r)
    except Exception as e:
        logger.error(f"[orchestrator] EIP learning failed: {e}")

    # Ethereum docs
    try:
        from . import ethdocs
        r = ethdocs.learn(batch_size=half, base_dir=base_dir)
        results.extend(r)
    except Exception as e:
        logger.error(f"[orchestrator] Ethdocs learning failed: {e}")

    return results


def _learn_deepen(batch_size: int, base_dir: Path) -> list[str]:
    """P4: Deepen shallow/stub articles with additional sources."""
    from . import web_research

    stubs = _find_stub_articles(base_dir)
    if not stubs:
        return []

    results = []
    for slug in stubs[:batch_size]:
        logger.info(f"[orchestrator] P4 deepen: {slug}")
        # Search for more info about this concept
        concept = slug.replace("-", " ")
        path = web_research.research_concept(concept, base_dir)
        if path:
            results.append(slug)
        time.sleep(2)
    return results


def _learn_curiosity(batch_size: int, base_dir: Path) -> list[str]:
    """P5: Random browsing — spellbook, rekt.news, L2Beat."""
    sources = ["rekt", "l2beat"]
    source = random.choice(sources)
    logger.info(f"[orchestrator] P5 curiosity: browsing {source}")

    try:
        if source == "spellbook":
            from . import spellbook_browse
            return spellbook_browse.learn(batch_size=batch_size, base_dir=base_dir)
        elif source == "rekt":
            from . import rekt
            return rekt.learn(batch_size=batch_size, base_dir=base_dir)
        elif source == "l2beat":
            from . import l2beat
            return l2beat.learn(batch_size=batch_size, base_dir=base_dir)
    except Exception as e:
        logger.error(f"[orchestrator] Curiosity ({source}) failed: {e}")
    return []


# ─── Main orchestrator ──────────────────────────────────────

def learn(batch_size: int = 5, base_dir: Path | None = None) -> list[str]:
    """Main entry point: decide what to learn and execute.

    Priority order:
      P0: Foundation concepts
      P1: Broken wiki-links
      P2: Trending protocols (DefiLlama)
      P3: Structured traversal (EIPs, ethereum.org)
      P4: Deepen stubs
      P5: Curiosity browsing
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    state = _load_state(base)
    cfg = load_config(base)
    curiosity_ratio = cfg.get("orchestrator", {}).get("curiosity_ratio", 0.2)

    results = []
    strategy_used = "none"

    # Curiosity roll: occasionally skip priorities and just explore
    if random.random() < curiosity_ratio:
        strategy_used = "curiosity"
        results = _learn_curiosity(batch_size, base)
    else:
        # Round-robin allocation: split batch across strategies
        # Give curriculum guaranteed slots so it doesn't starve behind P0
        strategies = [
            ("foundation", _learn_foundations),
            ("broken_links", _learn_broken_links),
            ("curriculum", _learn_curriculum),
            ("trending", _learn_trending),
            ("structured", _learn_structured),
            ("deepen", _learn_deepen),
            ("curiosity", _learn_curiosity),
        ]

        # Allocate: curriculum gets at least 2 slots if it has tasks,
        # foundation gets at least 2, rest is first-come
        curriculum_slots = min(2, batch_size // 2)
        foundation_slots = min(2, batch_size - curriculum_slots)
        remaining_slots = batch_size - curriculum_slots - foundation_slots

        # Try curriculum first with its allocation
        cr = _learn_curriculum(curriculum_slots, base)
        if cr:
            results.extend(cr)
            strategy_used = "curriculum"

        # Then foundation with its allocation
        fr = _learn_foundations(foundation_slots, base)
        if fr:
            results.extend(fr)
            if not strategy_used or strategy_used == "none":
                strategy_used = "foundation"
            else:
                strategy_used = f"{strategy_used}+foundation"

        # Fill remaining slots with other strategies
        if remaining_slots > 0 and len(results) < batch_size:
            remaining = batch_size - len(results)
            other_strategies = [
                ("broken_links", _learn_broken_links),
                ("trending", _learn_trending),
                ("structured", _learn_structured),
                ("deepen", _learn_deepen),
            ]
            for name, fn in other_strategies:
                if remaining <= 0:
                    break
                r = fn(remaining, base)
                if r:
                    results.extend(r)
                    remaining -= len(r)
                    strategy_used = f"{strategy_used}+{name}" if strategy_used != "none" else name

    # Update state
    state["history"].append({
        "strategy": strategy_used,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "items_learned": len(results),
        "items": results[:10],  # Keep first 10 for reference
    })
    # Keep only last 100 history entries
    state["history"] = state["history"][-100:]
    state["total_learned"] += len(results)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    _save_state(base, state)

    logger.info(
        f"[orchestrator] Strategy={strategy_used}, learned={len(results)} items"
    )
    return results


def status(base_dir: Path | None = None) -> dict:
    """Get orchestrator status and learning history."""
    base = Path(base_dir) if base_dir else Path.cwd()
    state = _load_state(base)

    # Count coverage
    missing_foundations = [
        c for c in FOUNDATIONS if not _article_exists(c, base)
    ]

    return {
        "total_learned": state.get("total_learned", 0),
        "last_run": state.get("last_run"),
        "foundation_coverage": f"{len(FOUNDATIONS) - len(missing_foundations)}/{len(FOUNDATIONS)}",
        "missing_foundations": missing_foundations[:10],
        "recent_history": state.get("history", [])[-5:],
    }
