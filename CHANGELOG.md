# Changelog

All notable changes to LLMBase (llmwiki) will be documented in this file.

## [0.2.0] — 2026-04-07

### Added
- **Structured Export API** — `export_article`, `export_by_tag`, `export_graph` for downstream projects
- **MCP Server** — Model Context Protocol support for Claude Code, Cursor, Windsurf, ClawHub (12 tools)
- **Research Trails** — Rabbithole-style exploration paths, auto-generated from deep research queries
- **Entity Extraction** — opt-in people/events/places extraction with timeline, people, and map views
- **Guided Reading** — LLM-generated 导读 (literary introduction), 文言文 as base for all languages
- **Reference Sources** — pluggable citation system with CBETA, Wikisource, ctext.org plugins
- **Backlinks Panel** — article detail page shows "Cited by" with resolved backlinks
- **D3 Timeline** — horizontal time axis with era bands, glow effects, zoom/pan
- **Voice/Tone Modes** — caveman, 文言文, scholar, ELI5
- **Tag Normalization** — LLM merges synonymous tags across wiki
- **Test Suite** — 54 tests covering core modules
- **ClawHub Skill** — `npx clawhub install llmwiki`
- **PyPI Package** — `pip install llmwiki`

### Changed
- **Taxonomy** — now LLM-generated (emergent, domain-agnostic), not hardcoded
- **Search** — default to deep research, single "Ask" button
- **Graph** — density control slider, inverted-index links, adaptive force layout
- **QA** — Chinese defaults to wenyan (文言文) tone
- **Dependencies** — matplotlib, pymupdf, mcp, watchdog moved to optional extras

### Fixed
- **Alias System** — multilingual wiki-link resolution (参禅 → can-chan, 繁简互转)
- **Compile Dedup** — 3-layer duplicate prevention (slug + alias + CJK substring)
- **Thinking Mode** — extract_json handles MiniMax thinking tokens before JSON output
- **Security** — SSRF protection, path traversal guards, constant-time auth, atomic JSON writes, job lock
- **Taxonomy Labels** — fixed string→trilingual dict normalization
- **lint.py** — split into `lint/checks.py`, `lint/fixes.py`, `lint/dedup.py` (was 943 lines)

### Architecture
- `tools/lint/` — package with checks, fixes, dedup (was monolithic 943-line file)
- `tools/refs/` — pluggable reference source plugins (auto-discovery)
- `tools/export.py` — structured export for downstream projects
- `tools/entities.py` — entity extraction with dedup
- `tools/xici.py` — guided reading generation
- `tools/resolve.py` — alias resolution with opencc support
- `tools/atomic.py` — atomic file writes
- `tools/mcp_server.py` — MCP stdio server

## [0.1.0] — 2026-04-04

### Added
- Initial release: ingest, compile, query, search, lint, worker
- Trilingual output (EN/中/日)
- Web UI with React + Tailwind
- Agent HTTP API + Python SDK
- CBETA, ctext.org, Wikisource data source plugins
- D3.js knowledge graph
- Docker + Railway deployment
