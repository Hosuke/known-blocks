"""Curriculum-driven learning — LLM generates structured learning plans per theme.

Instead of learning whatever data sources provide, the curriculum system:
1. Defines learning themes (Solana ecosystem, AI agents, DeFi trends, etc.)
2. Uses LLM to generate ordered concept lists with dependencies
3. Researches each concept via direct doc fetch or LLM generation
4. Tracks progress in taskdb

Usage:
    from tools.curriculum import generate_curriculum, get_next_lessons, research_lesson
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
from .llm import chat, extract_json
from .taskdb import enqueue_task, get_curriculum_tasks, claim_task, complete_task, fail_task

logger = logging.getLogger("llmbase.curriculum")

HEADERS = {"User-Agent": "KnownBlocks/1.0 (Knowledge Base Research)"}

# ─── Theme definitions ───────────────────────────────────────

THEMES = {
    "solana-ecosystem": {
        "description": (
            "Solana blockchain: architecture, Proof of History, Sealevel runtime, "
            "SPL token standard, and the DeFi ecosystem including Jupiter, Raydium, "
            "Marinade, Jito, Drift, Orca, Tensor, and Solana mobile/Saga."
        ),
        "seed_concepts": [
            "solana", "proof-of-history", "solana-programs", "spl-token",
            "jupiter-aggregator", "raydium", "marinade-finance", "jito-mev",
        ],
        "preferred_domains": [
            "solana.com", "docs.solana.com",
            "jup.ag", "raydium.io", "marinade.finance", "jito.network",
            "docs.drift.trade", "docs.orca.so", "tensor.trade",
        ],
    },
    "ai-agents-web3": {
        "description": (
            "Autonomous AI agents in Web3: agent frameworks (Eliza, AutoGPT, LangChain agents), "
            "on-chain AI agents, agent wallets, intent-based transactions, AI-driven trading, "
            "AI DAOs, decentralized inference, and the intersection of LLMs with smart contracts."
        ),
        "seed_concepts": [
            "ai-agent", "eliza-framework", "on-chain-agent", "intent-based-transactions",
            "agent-wallet", "decentralized-inference", "ai-dao",
        ],
        "preferred_domains": [
            "eliza.how", "ai16z.ai", "docs.phala.network",
            "www.autonolas.network", "docs.virtuals.io",
            "bittensor.com", "docs.ritual.net",
        ],
    },
    "defi-trends": {
        "description": (
            "Latest DeFi architecture trends: restaking and EigenLayer, liquid restaking tokens (LRTs), "
            "real-world assets (RWA) tokenization, institutional DeFi, points and airdrop meta, "
            "Pendle yield trading, intent-centric protocols, and DeFi on non-EVM chains."
        ),
        "seed_concepts": [
            "restaking", "eigenlayer", "liquid-restaking-token", "rwa-tokenization",
            "pendle", "points-system", "ethena", "morpho",
        ],
        "preferred_domains": [
            "docs.eigenlayer.xyz", "docs.etherfi.com", "docs.kelpdao.xyz",
            "docs.pendle.finance", "docs.ondo.finance", "docs.centrifuge.io",
            "docs.ethena.fi", "docs.morpho.org",
        ],
    },
    "modular-blockchains": {
        "description": (
            "Modular blockchain architecture: data availability layers (Celestia, EigenDA, Avail), "
            "execution environments, settlement layers, rollup-as-a-service (Conduit, Caldera, AltLayer), "
            "chain abstraction, cross-chain messaging (LayerZero, Hyperlane, Wormhole), "
            "and the Cosmos/IBC ecosystem."
        ),
        "seed_concepts": [
            "modular-blockchain", "data-availability-layer", "celestia",
            "chain-abstraction", "rollup-as-a-service", "layerzero", "cosmos-ibc",
        ],
        "preferred_domains": [
            "docs.celestia.org", "docs.avail.so",
            "docs.cosmos.network", "layerzero.network",
            "docs.hyperlane.xyz", "conduit.xyz", "docs.altlayer.io",
        ],
    },
    # ─── Chain ecosystems ──────────────────────────────────
    "ethereum-defi": {
        "description": (
            "Ethereum DeFi ecosystem deep dive: Uniswap V3/V4 concentrated liquidity, "
            "Aave V3 multi-chain lending, MakerDAO and DAI, Curve Finance and stableswap, "
            "Lido liquid staking, Compound, Balancer, 1inch aggregation, Flashbots MEV, "
            "EigenLayer restaking, and Ethereum staking economics."
        ),
        "seed_concepts": [
            "uniswap-v3", "aave-v3", "makerdao", "curve-finance",
            "compound", "1inch", "flashbots", "ethereum-staking",
        ],
        "preferred_domains": [
            "docs.uniswap.org", "docs.aave.com", "docs.makerdao.com",
            "resources.curve.fi", "docs.compound.finance", "docs.1inch.io",
            "docs.flashbots.net", "docs.lido.fi",
        ],
    },
    "arbitrum-ecosystem": {
        "description": (
            "Arbitrum L2 ecosystem: Arbitrum One and Nova architecture, Nitro stack, "
            "Stylus smart contracts, ARB governance, top DeFi (GMX, Camelot, Radiant, "
            "Pendle, Vela), Arbitrum Orbit chains, and the Arbitrum DAO."
        ),
        "seed_concepts": [
            "arbitrum-nitro", "arbitrum-stylus", "gmx", "camelot-dex",
            "arbitrum-orbit", "arb-governance",
        ],
        "preferred_domains": [
            "docs.arbitrum.io", "docs.gmx.io", "docs.camelot.exchange",
            "docs.radiant.capital", "docs.vela.exchange",
        ],
    },
    "base-ecosystem": {
        "description": (
            "Base L2 ecosystem by Coinbase: OP Stack architecture, Base Bridge, "
            "top protocols (Aerodrome, BaseSwap, Moonwell, Extra Finance), "
            "friend.tech social, Farcaster frames, onchain summer, and Base chain identity."
        ),
        "seed_concepts": [
            "base-chain", "op-stack", "aerodrome", "farcaster",
            "onchain-identity", "coinbase-smart-wallet",
        ],
        "preferred_domains": [
            "docs.base.org", "docs.optimism.io", "aerodrome.finance",
            "docs.farcaster.xyz", "docs.moonwell.fi",
        ],
    },
    "bnb-chain-ecosystem": {
        "description": (
            "BNB Chain ecosystem: BNB Smart Chain (BSC) architecture, opBNB L2, "
            "BNB Greenfield storage, PancakeSwap, Venus Protocol, BiSwap, "
            "BNB staking, and the Binance connection."
        ),
        "seed_concepts": [
            "bnb-smart-chain", "opbnb", "pancakeswap", "venus-protocol",
            "bnb-greenfield", "bnb-staking",
        ],
        "preferred_domains": [
            "docs.bnbchain.org", "docs.pancakeswap.finance",
            "docs.venus.io", "docs.opbnb.org",
        ],
    },
    # ─── Emerging topics ───────────────────────────────────
    "bitcoin-ecosystem": {
        "description": (
            "Bitcoin ecosystem renaissance: Ordinals and BRC-20 tokens, Bitcoin L2s (Stacks, "
            "Lightning Network, Liquid, BOB), Runes protocol, BitVM, Bitcoin DeFi, "
            "Taproot and script upgrades, and Bitcoin scaling debates."
        ),
        "seed_concepts": [
            "ordinals", "brc-20", "runes-protocol", "lightning-network",
            "stacks-blockchain", "bitvm", "taproot",
        ],
        "preferred_domains": [
            "docs.ordinals.com", "docs.stacks.co", "lightning.network",
            "docs.liquid.net", "docs.gobob.xyz",
        ],
    },
    "nft-gaming-social": {
        "description": (
            "NFTs, GameFi, and SocialFi: ERC-721/1155/6551, NFT marketplaces (OpenSea, Blur, "
            "Magic Eden), on-chain gaming (Immutable, Ronin, Treasure), SocialFi (Lens Protocol, "
            "Farcaster, friend.tech), creator economy, and digital identity (ENS, Worldcoin)."
        ),
        "seed_concepts": [
            "nft-marketplace", "erc-6551", "immutable-x", "lens-protocol",
            "ens", "worldcoin", "blur-marketplace",
        ],
        "preferred_domains": [
            "docs.immutable.com", "docs.lens.xyz", "docs.ens.domains",
            "docs.blur.foundation", "docs.treasure.lol",
        ],
    },
    "security-mev": {
        "description": (
            "Blockchain security and MEV: common attack vectors (reentrancy, flash loan attacks, "
            "oracle manipulation, sandwich attacks), MEV extraction and PBS (proposer-builder separation), "
            "Flashbots, audit firms and practices, formal verification, "
            "major hacks analysis, and security tooling (Slither, Foundry fuzzing)."
        ),
        "seed_concepts": [
            "reentrancy-attack", "flash-loan-attack", "sandwich-attack",
            "mev-extraction", "proposer-builder-separation", "smart-contract-audit",
        ],
        "preferred_domains": [
            "docs.flashbots.net", "docs.openzeppelin.com",
            "docs.trail-of-bits.com", "docs.consensys.io/diligence",
        ],
    },
    "depin-rwa": {
        "description": (
            "DePIN (Decentralized Physical Infrastructure Networks) and RWA tokenization: "
            "Helium, Hivemapper, Render Network, Filecoin, Arweave, "
            "tokenized treasuries (Ondo, Backed), real estate tokens, "
            "supply chain (VeChain), and the regulatory landscape."
        ),
        "seed_concepts": [
            "depin", "helium-network", "filecoin", "arweave",
            "render-network", "ondo-finance", "tokenized-treasuries",
        ],
        "preferred_domains": [
            "docs.helium.com", "docs.filecoin.io", "docs.arweave.org",
            "docs.render.network", "docs.ondo.finance",
        ],
    },
}


# ─── Curriculum generation ────────────────────────────────────


def generate_curriculum(theme_key: str, base_dir: Path | None = None) -> list[dict]:
    """Use LLM to generate a structured learning curriculum for a theme.

    Returns list of lesson dicts and enqueues them in taskdb.
    """
    base = Path(base_dir) if base_dir else Path.cwd()

    if theme_key not in THEMES:
        raise ValueError(f"Unknown theme: {theme_key}. Available: {list(THEMES.keys())}")

    theme = THEMES[theme_key]

    # Get existing articles to avoid duplicates
    cfg = load_config(base)
    concepts_dir = Path(cfg["paths"]["concepts"])
    existing = set()
    if concepts_dir.exists():
        existing = {p.stem for p in concepts_dir.glob("*.md")}

    # Check what curriculum tasks already exist for this theme
    existing_tasks = get_curriculum_tasks(theme_key, base_dir=base)
    if existing_tasks:
        logger.info(f"Curriculum for {theme_key} already exists ({len(existing_tasks)} lessons)")
        return [t for t in existing_tasks if t.get("metadata")]

    prompt = f"""You are a blockchain/crypto education curriculum designer.

Theme: {theme["description"]}

The knowledge base already contains articles about: {", ".join(sorted(existing)[:50])}

Generate a learning curriculum of 15-25 concepts in DEPENDENCY ORDER (learn prerequisites first).
For each concept, provide:
- slug: kebab-case identifier (e.g., "proof-of-history", "raydium-amm")
- title: Human-readable title
- depends_on: list of slugs from this curriculum that should be learned first
- search_query: specific search query to find authoritative information
- depth: "deep" (1500+ words) or "medium" (800-1200 words)
- description: 1-2 sentence description of what to cover

Seed concepts to include: {", ".join(theme["seed_concepts"])}

Output ONLY a JSON array, no other text:
[
  {{"slug": "concept-slug", "title": "Concept Title", "depends_on": [], "search_query": "...", "depth": "deep", "description": "..."}},
  ...
]"""

    try:
        response = chat(prompt, max_tokens=4096)
        json_text = extract_json(response)
        lessons = json.loads(json_text)
    except Exception as e:
        logger.error(f"Failed to generate curriculum for {theme_key}: {e}")
        # Fallback: use seed concepts
        lessons = [
            {
                "slug": slug,
                "title": slug.replace("-", " ").title(),
                "depends_on": [],
                "search_query": f"{slug.replace('-', ' ')} blockchain crypto explained",
                "depth": "deep",
                "description": f"Core concept: {slug}",
            }
            for slug in theme["seed_concepts"]
        ]

    # Enqueue in taskdb
    for i, lesson in enumerate(lessons):
        item_key = f"{theme_key}/{lesson['slug']}"
        metadata = {
            "theme": theme_key,
            "title": lesson.get("title", lesson["slug"]),
            "depends_on": lesson.get("depends_on", []),
            "search_query": lesson.get("search_query", ""),
            "depth": lesson.get("depth", "medium"),
            "description": lesson.get("description", ""),
            "order": i,
            "preferred_domains": theme.get("preferred_domains", []),
        }
        enqueue_task(
            "curriculum", item_key, priority=2,
            base_dir=base, metadata=metadata,
        )

    logger.info(f"Generated curriculum for {theme_key}: {len(lessons)} lessons")
    return lessons


def generate_all_curricula(base_dir: Path | None = None) -> dict:
    """Generate curricula for all defined themes."""
    base = Path(base_dir) if base_dir else Path.cwd()
    results = {}
    for theme_key in THEMES:
        try:
            lessons = generate_curriculum(theme_key, base)
            results[theme_key] = len(lessons)
        except Exception as e:
            logger.error(f"Failed to generate curriculum for {theme_key}: {e}")
            results[theme_key] = f"error: {e}"
    return results


# ─── Lesson retrieval ─────────────────────────────────────────


def get_next_lessons(batch_size: int = 3, base_dir: Path | None = None) -> list[dict]:
    """Get next lessons to learn, respecting dependency order.

    Only returns lessons whose dependencies are all completed.
    """
    base = Path(base_dir) if base_dir else Path.cwd()

    queued = get_curriculum_tasks(status="queued", base_dir=base)
    if not queued:
        return []

    # Build set of completed lesson slugs
    completed = get_curriculum_tasks(status="completed", base_dir=base)
    completed_slugs = set()
    for t in completed:
        # Extract slug from item_key "theme/slug"
        parts = t["item_key"].split("/", 1)
        if len(parts) > 1:
            completed_slugs.add(parts[1])

    # Also check existing articles
    cfg = load_config(base)
    concepts_dir = Path(cfg["paths"]["concepts"])
    if concepts_dir.exists():
        completed_slugs |= {p.stem for p in concepts_dir.glob("*.md")}

    # Filter to lessons whose dependencies are met
    ready = []
    for task in queued:
        meta = task.get("metadata", {})
        if not meta:
            ready.append(task)
            continue
        deps = meta.get("depends_on", [])
        if all(d in completed_slugs for d in deps):
            ready.append(task)

    # Sort by order field in metadata
    ready.sort(key=lambda t: (t.get("metadata", {}).get("order", 999), t["priority"]))

    return ready[:batch_size]


# ─── Research execution ───────────────────────────────────────


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-")


def _try_fetch_doc_site(concept_slug: str, preferred_domains: list[str]) -> tuple[str, str] | None:
    """Try to fetch documentation directly from known doc sites."""
    concept_path = concept_slug.replace("-", "/")
    concept_dashed = concept_slug

    url_patterns = [
        "/{slug}",
        "/docs/{slug}",
        "/learn/{slug}",
        "/developers/docs/{slug}",
        "/docs/learn/{slug}",
    ]

    for domain in preferred_domains[:5]:  # Limit to avoid too many requests
        for pattern in url_patterns:
            path = pattern.format(slug=concept_dashed)
            url = f"https://{domain}{path}"
            try:
                resp = requests.get(url, timeout=10, headers=HEADERS, allow_redirects=True)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")

                # Remove nav/footer/scripts
                for tag in soup.find_all(["nav", "footer", "script", "style", "aside", "header"]):
                    tag.decompose()

                main = soup.find("main") or soup.find("article") or soup.find("body")
                if not main:
                    continue

                content = md(str(main), heading_style="ATX", strip=["img"])
                content = re.sub(r"\n{3,}", "\n\n", content)

                if len(content.strip()) < 500:
                    continue

                title = ""
                h1 = soup.find("h1")
                if h1:
                    title = h1.get_text(strip=True)
                if not title:
                    title_el = soup.find("title")
                    if title_el:
                        title = title_el.get_text(strip=True)

                logger.info(f"[curriculum] Fetched doc: {url} ({len(content)} chars)")
                return title, content

            except Exception:
                continue

    return None


def _generate_research_article(concept_slug: str, metadata: dict) -> str:
    """Generate a research article using LLM knowledge."""
    search_query = metadata.get("search_query", f"{concept_slug.replace('-', ' ')} explained")
    description = metadata.get("description", "")
    depth = metadata.get("depth", "medium")
    title = metadata.get("title", concept_slug.replace("-", " ").title())

    word_target = "1500-2500" if depth == "deep" else "800-1200"

    prompt = f"""Write a comprehensive, factual article about "{title}".

Context: {description}
Research angle: {search_query}

Requirements:
- Write in English, be authoritative and technical
- Cover: definition, how it works, key implementations/projects, relationship to other concepts
- Include specific details: protocol names, technical mechanisms, market data where relevant
- Use [[wiki-link]] syntax when referencing other blockchain concepts
- Length: {word_target} words
- Target audience: someone building knowledge about blockchain technology

Do NOT include a title heading — just start with the content."""

    return chat(prompt, max_tokens=6144 if depth == "deep" else 4096)


def research_lesson(task: dict, base_dir: Path | None = None) -> Path | None:
    """Research a curriculum lesson: try doc fetch, fallback to LLM generation.

    Returns path to the raw document created, or None on failure.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    cfg = load_config(base)
    ensure_dirs(cfg)
    raw_dir = Path(cfg["paths"]["raw"])

    item_key = task["item_key"]
    meta = task.get("metadata", {})
    if isinstance(meta, str):
        meta = json.loads(meta) if meta else {}

    # Extract theme and slug
    parts = item_key.split("/", 1)
    theme_key = parts[0] if len(parts) > 1 else "unknown"
    concept_slug = parts[1] if len(parts) > 1 else item_key

    # Check if already exists
    slug = f"curriculum-{_slugify(concept_slug)}"
    doc_dir = raw_dir / slug
    if (doc_dir / "index.md").exists():
        logger.info(f"[curriculum] Already researched: {concept_slug}")
        return doc_dir / "index.md"

    task_id = claim_task("curriculum", item_key, priority=2, base_dir=base)

    try:
        # Step 1: Try direct doc site fetch
        preferred_domains = meta.get("preferred_domains", [])
        fetched = _try_fetch_doc_site(concept_slug, preferred_domains)

        if fetched:
            title, content = fetched
            source_type = "doc_site"
            source_url = "direct_fetch"
        else:
            # Step 2: LLM-generated research
            logger.info(f"[curriculum] No doc found for {concept_slug}, using LLM research")
            content = _generate_research_article(concept_slug, meta)
            title = meta.get("title", concept_slug.replace("-", " ").title())
            source_type = "llm_research"
            source_url = "llm-generated"

        if not content or len(content) < 200:
            fail_task(task_id, "Content too short", base_dir=base)
            return None

        # Save raw document
        doc_dir.mkdir(parents=True, exist_ok=True)
        post = frontmatter.Post(content)
        post.metadata["title"] = title
        post.metadata["source"] = source_url
        post.metadata["source_type"] = source_type
        post.metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()
        post.metadata["type"] = "curriculum"
        post.metadata["concept"] = concept_slug
        post.metadata["theme"] = theme_key
        post.metadata["compiled"] = False

        doc_path = doc_dir / "index.md"
        doc_path.write_text(frontmatter.dumps(post), encoding="utf-8")

        complete_task(task_id, base_dir=base)
        logger.info(f"[curriculum] Researched '{concept_slug}' ({source_type}, {len(content)} chars)")
        return doc_path

    except Exception as e:
        fail_task(task_id, str(e), base_dir=base)
        logger.error(f"[curriculum] Failed to research {concept_slug}: {e}")
        return None


# ─── Utility ──────────────────────────────────────────────────


def list_themes() -> dict:
    """Return available themes and their descriptions."""
    return {k: v["description"] for k, v in THEMES.items()}
