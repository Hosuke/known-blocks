<div align="center">

# Known-Blocks

**自主学习链上知识的 LLM 知识库**

基于 [LLMBase](https://github.com/Hosuke/llmbase) 构建。系统像一个好奇的 crypto researcher——自动发现该学什么、从哪学、怎么补盲。部署后无需人工干预，知识库持续增长。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

[English](#how-it-works) | [中文](#中文说明)

</div>

---

## How It Works

```
┌─ Orchestrator (the brain) ──────────────────────────────┐
│  "What should I learn next?"                             │
│                                                          │
│  P0: Foundations missing? → search & learn               │
│  P1: Broken wiki-links? → research the concept           │
│  P2: Top DeFi protocols uncovered? → learn from DeFi... │
│  P3: More EIPs/docs to read? → fetch from GitHub         │
│  P4: Shallow articles? → deepen with more sources        │
│  P5: Feeling curious? → browse spellbook / rekt.news     │
└──────────────┬───────────────────────────────────────────┘
               │ picks a strategy, calls a data source
               ▼
┌─ Data Source Plugins ────────────────────────────────────┐
│  ethereum.org docs │ EIP standards │ DefiLlama API       │
│  L2Beat            │ rekt.news     │ Spellbook SQL       │
│  Web search (gap-filling)                                │
└──────────────┬───────────────────────────────────────────┘
               │ writes raw/{slug}/index.md
               ▼
┌─ LLMBase Pipeline ──────────────────────────────────────┐
│  Compile → trilingual wiki articles (EN / 中文 / 日本語)  │
│  Lint → broken links, orphans, stubs                     │
│  Heal → auto-generate stubs, fix metadata                │
│  Index → full-text search + backlinks + taxonomy          │
└──────────────────────────────────────────────────────────┘
```

## Install

```bash
cd known-blocks

# Python dependencies
pip install -e .

# Frontend (optional, for Web UI)
cd frontend && npm install && npx vite build && cd ..
```

## Quick Start

### 1. Configure LLM

```bash
cp .env.example .env
```

Edit `.env` with your LLM provider. Any OpenAI-compatible API works:

```bash
# OpenAI
LLMBASE_API_KEY=sk-...
LLMBASE_BASE_URL=https://api.openai.com/v1
LLMBASE_MODEL=gpt-4o

# Or OpenRouter (200+ models)
LLMBASE_API_KEY=sk-or-...
LLMBASE_BASE_URL=https://openrouter.ai/api/v1
LLMBASE_MODEL=anthropic/claude-sonnet-4-5

# Or Ollama (local, free)
LLMBASE_API_KEY=ollama
LLMBASE_BASE_URL=http://localhost:11434/v1
LLMBASE_MODEL=llama3.1
```

### 2. Configure Spellbook Path (optional)

If you have a local clone of [duneanalytics/spellbook](https://github.com/duneanalytics/spellbook), edit `config.yaml`:

```yaml
spellbook:
  path: "/path/to/your/spellbook"
```

### 3. Learn Something

```bash
# Learn 3 pages from ethereum.org
llmbase ingest ethdocs-learn --batch 3

# Compile into wiki articles
llmbase compile new

# Check what was created
llmbase search query "ethereum"
```

### 4. Let the Orchestrator Decide

```bash
# Run one auto-learning cycle
llmbase ingest orchestrate

# Then compile
llmbase compile new
```

### 5. Go Fully Autonomous

Edit `config.yaml`:

```yaml
worker:
  enabled: true
  learn_source: orchestrator
  learn_interval_hours: 4
  learn_batch_size: 5
```

Then start the server:

```bash
llmbase web    # http://localhost:5555
```

The worker runs in the background: learn → compile → index → health check → repeat.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Blockchain Orchestrator** | Priority-based auto-learning: foundations → broken links → trending protocols → EIPs → deepening → curiosity |
| **7 Data Source Plugins** | ethereum.org, EIPs, DefiLlama, L2Beat, rekt.news, Spellbook, web search |
| **Trilingual Output** | Every article compiled in English, 中文, and 日本語 with global language switcher |
| **Self-Healing Wiki** | 7-step auto-fix: clean garbage → fix tags → normalize → metadata → broken links → dedup → taxonomy |
| **MCP Server** | Model Context Protocol support — Claude Code, Cursor, and other AI clients can query your KB directly |
| **Model Fallback** | Primary LLM fails? Auto-falls back to secondary models. Handles thinking-mode output. |
| **Knowledge Graph** | D3.js force-directed graph with density control slider, tag filtering, adaptive layout |
| **Agent-First API** | HTTP API + Python SDK for LLM agents to query and contribute |

## CLI Reference

### Learning Commands

```bash
# ─── Structured sources (systematic traversal) ───────────

# Ethereum.org developer docs (EVM, gas, consensus, scaling...)
llmbase ingest ethdocs-learn --batch 5

# EIP/ERC standards (ERC-20, ERC-721, EIP-1559, EIP-4844...)
llmbase ingest eips-learn --batch 5

# DeFi protocols by TVL rank (from DefiLlama)
llmbase ingest defillama-learn --batch 5

# Layer 2 ecosystem (from L2Beat)
llmbase ingest l2beat-learn --batch 5

# Security incidents (from rekt.news)
llmbase ingest rekt-learn --batch 3

# On-chain data structures (browse local Spellbook)
llmbase ingest spellbook-browse --batch 3

# ─── Auto-learning ───────────────────────────────────────

# Let the orchestrator decide what to learn
llmbase ingest orchestrate --batch 5
```

### Standard Commands

```bash
# ─── Ingest ───────────────────────────────────────
llmbase ingest url https://docs.uniswap.org/concepts/overview
llmbase ingest pdf ./whitepaper.pdf --chunk-pages 20
llmbase ingest file ./notes.md

# ─── Compile ──────────────────────────────────────
llmbase compile new          # Incremental (3-layer dedup)
llmbase compile all          # Full rebuild
llmbase compile index        # Rebuild index + aliases

# ─── Health & Repair ─────────────────────────────
llmbase lint check           # All checks
llmbase lint clean           # Remove garbage stubs
llmbase lint dedup           # Detect + merge duplicates
llmbase lint normalize-tags  # Merge synonymous tags
llmbase lint fix             # Full auto-fix pipeline
llmbase lint heal            # Check → fix → recheck → report

# ─── Query ────────────────────────────────────────
llmbase query "What is a flash loan?" --file-back
llmbase query "Compare Optimistic vs ZK rollups"
llmbase query "What is MEV?" --tone scholar

# ─── Serve ────────────────────────────────────────
llmbase web                  # Web UI (localhost:5555)
llmbase serve                # Agent API (localhost:5556)
llmbase mcp                  # MCP server (stdio)
```

## Data Sources

| Source | What It Learns | API Key? |
|--------|---------------|----------|
| **ethereum.org** | EVM, gas, consensus, scaling, smart contracts, token standards | No (GitHub raw) |
| **EIP/ERC Standards** | Token standards, protocol upgrades, account abstraction | No (GitHub raw) |
| **DefiLlama** | Protocol metadata, TVL rankings, chain info, DeFi categories | No (free API) |
| **L2Beat** | L2 architecture, risk assessment, stage ratings | No (public API) |
| **rekt.news** | Security incidents, exploit analysis, post-mortems | No (web scraping) |
| **Spellbook** | On-chain event schemas, SQL data models, protocol structures | No (local files) |
| **Web Research** | Gap-filling — any blockchain concept via search | No (DuckDuckGo) |

All sources are free and require no API keys. Only the LLM provider needs a key.

## Orchestrator

The orchestrator (`tools/orchestrator.py`) is the brain. Each cycle, it evaluates what the knowledge base is missing and picks the highest-priority learning task:

| Priority | Strategy | Trigger |
|----------|----------|---------|
| **P0** | Foundation | Core concepts missing (blockchain, EVM, gas, DeFi, AMM...) |
| **P1** | Gap-fill | Broken `[[wiki-links]]` — concepts referenced but not yet learned |
| **P2** | Trending | Top DeFi protocols by TVL not yet covered |
| **P3** | Structured | Next batch of EIPs or ethereum.org docs |
| **P4** | Deepen | Stub articles that need more content |
| **P5** | Curiosity | Random browsing — spellbook, rekt.news, or L2Beat |

A `curiosity_ratio` config (default 0.2) means 20% of cycles skip priorities and just explore randomly.

## Configuration

`config.yaml` key settings:

```yaml
worker:
  enabled: true               # Enable background autonomous learning
  learn_source: orchestrator   # Use the orchestrator (or: ethdocs, eips, defillama, etc.)
  learn_interval_hours: 4      # How often to learn
  learn_batch_size: 5          # Items per learning cycle
  compile_interval_hours: 1    # How often to compile new docs
  health_check_interval_hours: 24  # Self-heal every 24h

spellbook:
  path: "/path/to/spellbook"   # Local spellbook clone path

defillama:
  min_tvl: 1000000             # Only learn protocols with TVL > $1M
  top_n: 50                    # Track top 50 by TVL

orchestrator:
  curiosity_ratio: 0.2         # 20% chance of random exploration
```

## MCP Server (AI Client Integration)

LLMBase exposes a [Model Context Protocol](https://modelcontextprotocol.io/) server, so any MCP-compatible AI client can interact with your knowledge base directly.

```json
{
  "mcpServers": {
    "known-blocks": {
      "command": "python",
      "args": ["-m", "tools.mcp_server", "--base-dir", "/path/to/known-blocks"]
    }
  }
}
```

## Project Structure

```
known-blocks/
├── tools/                     # Python backend
│   ├── orchestrator.py        # Learning brain — priority queue + curiosity
│   ├── ethdocs.py             # Ethereum.org docs plugin
│   ├── eips.py                # EIP/ERC standards plugin
│   ├── defillama.py           # DefiLlama protocol data plugin
│   ├── l2beat.py              # L2Beat ecosystem plugin
│   ├── rekt.py                # Security incidents plugin
│   ├── spellbook_browse.py    # Spellbook SQL browsing plugin
│   ├── web_research.py        # Web search gap-filler
│   ├── refs/                  # Reference link plugins
│   ├── compile.py             # LLM compilation pipeline
│   ├── worker.py              # Background worker
│   ├── cli.py                 # CLI entry point
│   └── ...                    # (inherited from LLMBase)
├── raw/                       # Ingested raw documents
├── wiki/
│   ├── concepts/              # Compiled trilingual articles
│   ├── outputs/               # Q&A answer archive
│   └── _meta/                 # Index, taxonomy, health, progress files
├── config.yaml                # Configuration
├── .env                       # LLM API credentials
└── frontend/                  # React Web UI
```

## Deployment

```bash
# Docker
docker compose up -d

# Railway
railway login && railway init
railway variables set LLMBASE_API_KEY=sk-...
railway up

# Manual
gunicorn --bind 0.0.0.0:5555 --workers 2 --timeout 300 wsgi:app
```

---

## 中文说明

### 这是什么？

Known-Blocks 是一个**自主学习区块链知识的 LLM 知识库**。

基于 [LLMBase](https://github.com/Hosuke/llmbase) 构建，继承了它的核心能力（三语编译、自愈系统、知识图谱），并增加了 7 个区块链数据源插件和一个学习编排器。

### 核心理念

系统像一个**刚入行的 crypto researcher**：
1. 先学基础概念（区块链、EVM、gas、DeFi...）
2. 再学具体协议（Uniswap、Aave、Lido...）
3. 遇到不懂的就去查（断链搜索）
4. 看到热门项目就去了解（TVL 趋势）
5. 偶尔翻翻参考书（Spellbook、安全事件）

### 快速开始

```bash
# 安装
pip install -e .

# 配置 LLM（编辑 .env 填入 API key）
cp .env.example .env

# 手动学几篇以太坊文档
llmbase ingest ethdocs-learn --batch 3

# 编译成三语文章
llmbase compile new

# 或者，让编排器自己决定学什么
llmbase ingest orchestrate

# 全自动模式：编辑 config.yaml 设 worker.enabled: true
llmbase web
```

### 学习来源

| 来源 | 学什么 | 需要 API Key？ |
|------|--------|---------------|
| ethereum.org | EVM、gas、共识、扩容、智能合约 | 不需要 |
| EIP/ERC 标准 | 代币标准、协议升级、账户抽象 | 不需要 |
| DefiLlama | 协议元数据、TVL 排名、链信息 | 不需要 |
| L2Beat | L2 技术架构、风险评级 | 不需要 |
| rekt.news | 安全事件、漏洞分析 | 不需要 |
| Spellbook | 链上事件 schema、SQL 数据模型 | 不需要（本地文件） |
| 网络搜索 | 补盲——任何缺失的区块链概念 | 不需要 |

所有数据源免费，只有 LLM 编译需要 API key。

---

## License

MIT

---

<div align="center">
<sub>Built with LLMs, for LLMs. Knowledge compounds. 温故而知新。</sub>
</div>
