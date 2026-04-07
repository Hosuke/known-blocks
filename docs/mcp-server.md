# MCP Server Guide

LLMBase exposes a [Model Context Protocol](https://modelcontextprotocol.io/) server, allowing any MCP-compatible AI client to interact with the knowledge base natively.

## What is MCP?

MCP (Model Context Protocol) is a standard for AI tools to expose capabilities to AI clients. Instead of HTTP APIs, MCP uses stdio transport — the AI client spawns the server as a subprocess and communicates via JSON-RPC over stdin/stdout.

**Result**: Your AI assistant can directly search, query, and manage your knowledge base as if it were a native tool.

## Setup

### Claude Code

Add to `~/.claude/settings.json` or project `.claude/settings.json`:

```json
{
  "mcpServers": {
    "llmbase": {
      "command": "python",
      "args": ["-m", "tools.mcp_server", "--base-dir", "/absolute/path/to/your/kb"]
    }
  }
}
```

### Cursor / Windsurf / ClawHub

Each client has its own MCP configuration. The key fields are the same:
- **command**: `python`
- **args**: `["-m", "tools.mcp_server", "--base-dir", "/path/to/kb"]`
- **transport**: stdio (default)

### CLI

```bash
llmbase mcp
```

## Available Tools

### Read Tools (no side effects)

| Tool | Input | Description |
|------|-------|-------------|
| `kb_search` | `query`, `top_k?` | Full-text search across wiki articles |
| `kb_ask` | `question`, `tone?` | Deep research — searches relevant articles, synthesizes answer |
| `kb_get` | `slug` | Get article by slug or alias. Supports Chinese (`空`), pinyin (`kong`), English |
| `kb_list` | `tag?` | List all articles, optionally filtered by tag |
| `kb_backlinks` | `slug` | Find all articles that reference the given article |
| `kb_taxonomy` | `lang?` | Hierarchical category tree (zh/en/ja/zh-en) |
| `kb_stats` | — | Article count, raw doc count |
| `kb_xici` | `lang?` | Guided reading (导读) — LLM-generated introduction |

### Write Tools (mutating, uses job lock)

| Tool | Input | Description |
|------|-------|-------------|
| `kb_ingest` | `url` | Ingest a URL as a raw document |
| `kb_compile` | — | Compile new raw docs into wiki articles |
| `kb_lint` | `fix?` | Health check (`fix=false`) or auto-fix pipeline (`fix=true`) |

Write tools are mutex-protected — only one can run at a time.

## Examples

In Claude Code, after MCP registration:

```
You: Search my knowledge base for "emptiness"
Claude: [calls kb_search with query="emptiness"]
→ Found 5 articles: 空, 中观, 龙树...

You: What is the relationship between 仁 and governance?
Claude: [calls kb_ask with question="仁 and governance"]
→ [Deep research answer using wiki context]

You: Show me the article about Mencius
Claude: [calls kb_get with slug="孟子"]  
→ [Full article with alias resolution: 孟子 → mencius]

You: What articles cite this one?
Claude: [calls kb_backlinks with slug="mencius"]
→ Cited by: four-beginnings, benevolent-government, ...
```

## Tone Modes

`kb_ask` supports tone modes via the `tone` parameter:

| Tone | Description |
|------|-------------|
| `default` | Standard research assistant |
| `wenyan` | Classical Chinese (文言文) |
| `scholar` | Academic English |
| `caveman` | Primitive speech |
| `eli5` | Explain Like I'm 5 |

## Architecture

```
AI Client (Claude Code / Cursor / etc.)
  ↕ stdio (JSON-RPC)
MCP Server (tools/mcp_server.py)
  ↕ direct Python calls
LLMBase core (tools/*.py)
  ↕ file I/O
wiki/_meta/*.json + wiki/concepts/*.md
```

No HTTP server needed. The MCP server is a lightweight Python process that the AI client manages.

## Publishing

MCP servers don't need to be "published" — they run locally. Just point your AI client's config to the `python -m tools.mcp_server` command with the right `--base-dir`.

For sharing: users clone the repo, `pip install -e .`, and add the MCP config to their client.
