# Frontend Design Prompt for Google Stitch

## Project Overview

Design a modern, responsive web frontend for **LLMBase** — an LLM-powered personal knowledge base. The app has a REST API backend (Flask) and needs a React SPA frontend. The design should feel like a hybrid between **Obsidian** (knowledge graph + markdown wiki) and **Perplexity** (AI-powered Q&A with citations).

**Tech stack:** React 18 + TypeScript + Tailwind CSS + shadcn/ui components + react-markdown + remark-gfm + D3.js (for graph)

**API base:** All data comes from REST endpoints (listed below). No auth needed for v1.

---

## Design System

- **Theme:** Dark mode primary (like Obsidian), with light mode toggle
- **Dark palette:** Background #0a0a0f, Surface #12121f, Card #1a1a2e, Border #2a2a4a, Accent #6366f1 (indigo), Secondary #22d3ee (cyan), Text #e2e8f0, Muted #64748b
- **Light palette:** Background #fafafa, Surface #ffffff, Card #f8fafc, Accent #4f46e5
- **Typography:** Inter for UI, JetBrains Mono for code, Noto Serif SC for CJK body text
- **Border radius:** 12px cards, 8px buttons/inputs, 6px tags
- **Spacing:** 8px grid system
- **Motion:** Subtle transitions (150ms ease), page transitions with fade

---

## Pages & Components

### 1. Layout Shell

A persistent layout wrapping all pages:

```
┌──────────────────────────────────────────────────┐
│ [Sidebar]  │  [Top Bar]                          │
│            │──────────────────────────────────────│
│  Logo      │                                     │
│  Nav       │         [Main Content Area]         │
│  Articles  │                                     │
│  Tags      │                                     │
│            │                                     │
│  Stats     │                                     │
└──────────────────────────────────────────────────┘
```

**Sidebar (260px, collapsible on mobile):**
- Logo + app name "LLMBase" at top
- Navigation items with icons:
  - 🏠 Dashboard
  - 📚 Wiki (browse all articles)
  - 🔍 Search
  - 💬 Q&A
  - 📊 Knowledge Graph
  - 📥 Ingest (add documents)
  - 🔧 Lint & Health
- Divider
- "Wiki Articles" section: scrollable list of all article titles, clickable, showing tag dots
- Bottom: compact stats bar (X articles, Y words)

**Top Bar:**
- Global search input (Cmd+K shortcut)
- Theme toggle (dark/light)
- Compile button (triggers wiki compilation)

---

### 2. Dashboard Page (`/`)

Overview of the knowledge base.

**Stats row (4 cards, horizontal):**
- Raw Documents (count, icon: 📄)
- Wiki Articles (count, icon: 📝)
- Filed Outputs (count, icon: 💾)
- Total Words (formatted with commas, icon: 📊)

**Recent Articles section:**
- Grid of article cards (2 columns on desktop, 1 on mobile)
- Each card shows: title, summary (2 lines truncated), tags as colored pills, created date
- Click → navigate to article page

**Quick Actions row:**
- "Ask a Question" button → navigates to Q&A
- "Ingest URL" button → opens ingest modal
- "Run Health Check" button → navigates to Lint

**API:** `GET /api/stats`, `GET /api/articles`

---

### 3. Wiki Browser Page (`/wiki`)

Browse and filter all wiki articles.

**Filter bar at top:**
- Search/filter input (client-side filtering)
- Tag filter chips (click to toggle, multi-select)
- Sort dropdown: Alphabetical, Newest, Most linked

**Article grid:**
- Cards with: title (h3), summary, tags (colored pills), word count badge
- Hover: subtle border glow
- Click → article detail page

**Empty state:** Illustration + "No articles yet. Ingest some documents and compile them."

**API:** `GET /api/articles`

---

### 4. Article Detail Page (`/wiki/:slug`)

Full article reading view — **this is the most important page, needs excellent markdown rendering.**

**Header:**
- Article title (large, h1)
- Summary (muted text below title)
- Tags as clickable pills
- Metadata bar: created date, word count, source count

**Content area (max-width 720px, centered):**
- Full markdown rendering with:
  - Proper headings (h1-h6) with anchor links
  - Tables with zebra striping and horizontal scroll on mobile
  - Code blocks with syntax highlighting (highlight.js or Prism)
  - Blockquotes with left accent border
  - Ordered/unordered lists with proper nesting
  - Images with lazy loading and lightbox
  - Horizontal rules
  - Bold, italic, strikethrough
  - **Wiki-links `[[target|label]]`** rendered as clickable internal links (indigo color, hover underline) that navigate to `/wiki/target`
  - Math/LaTeX support (optional, KaTeX)

**Right sidebar (240px, desktop only):**
- Table of contents (auto-generated from headings, sticky)
- "Backlinks" section: list of articles that link TO this article
- "Related" section: articles sharing tags

**Bottom:**
- Previous/Next article navigation

**API:** `GET /api/articles/:slug`

---

### 5. Search Page (`/search`)

Full-text search across the wiki.

**Search bar (prominent, centered at top):**
- Large input with search icon
- "Search the knowledge base..." placeholder
- Enter to search

**Results area:**
- Result count + query echo: "Found 8 results for 'meditation'"
- Each result card:
  - Title (clickable → article page)
  - Relevance score badge
  - Summary line
  - Highlighted snippet with matching terms in bold/yellow background
  - Tags
- Empty state: "No results found. Try different keywords."

**API:** `GET /api/search?q=query&top_k=10`

---

### 6. Q&A Page (`/qa`)

AI-powered question answering — **should feel like Perplexity.**

**Question input area:**
- Large textarea (auto-expanding, 3-5 lines)
- Placeholder: "Ask anything about your knowledge base..."
- Row of action buttons below:
  - "Ask" (primary, indigo) — standard query
  - "Deep Research" (secondary, cyan) — multi-step search
  - Checkbox: "File answer back to wiki" (checked by default)
  - Format selector: Markdown / Slides (Marp) / Chart

**Answer area:**
- Loading state: animated shimmer skeleton
- Rendered answer with full markdown support (same as article page)
- Citations shown as linked references to wiki articles (like Perplexity footnotes)
- "Copy" button, "File to Wiki" button at bottom

**Conversation history (optional, sidebar or accordion):**
- List of previous Q&A pairs in this session
- Click to review

**API:** `POST /api/ask { question, deep, file_back }`

---

### 7. Knowledge Graph Page (`/graph`)

Interactive visualization of article connections.

**Full-screen canvas with:**
- Force-directed graph (D3.js force simulation)
- Nodes = articles (circles, sized by word count, colored by primary tag)
- Edges = wiki-links between articles (lines, thicker = more links)
- Node labels: article titles
- Interactions:
  - Hover node: highlight connected nodes, dim others, show tooltip with summary
  - Click node: navigate to article page
  - Drag nodes to rearrange
  - Zoom/pan with mouse wheel and drag
  - Search box overlaid to highlight matching nodes

**Control panel (top-right overlay):**
- Filter by tag
- Toggle labels on/off
- Layout options (force / radial / tree)
- "Orphan articles" toggle (show unlinked articles)

**API:** `GET /api/articles` (to build graph), read backlinks from article data

---

### 8. Ingest Page (`/ingest`)

Add new raw documents to the knowledge base.

**Tab interface:**
- **URL tab:** Input field + "Ingest" button. Shows progress spinner, then success message with document title.
- **File tab:** Drag-and-drop zone + file picker. Supports .md, .txt, .pdf, .py, .json, .csv
- **Directory tab:** Path input for local directory ingestion

**Raw Documents list (below tabs):**
- Table or card list of all ingested documents
- Columns: Title, Type (web_article / local_file / browser_article), Compiled status (✓/✗), Ingested date
- Uncompiled docs highlighted with a "Compile" button

**Compile action:**
- "Compile All New" button at top
- Shows progress: "Compiling 3 documents..." with progress bar
- Success: shows list of newly created articles with links

**API:** `POST /api/ingest { source }`, `POST /api/compile`, `GET /api/sources`

---

### 9. Lint & Health Page (`/lint`)

Wiki quality dashboard.

**Health Overview cards:**
- Structural Issues (count + status icon: ✅ or ⚠️)
- Broken Links (count)
- Orphan Articles (count)
- Missing Metadata (count)

**Issues list (expandable sections):**
- Each category as an accordion
- Individual issues listed with article link + description
- "Auto-Fix" button per category (triggers LLM fix)

**Deep Analysis section:**
- "Run Deep Analysis" button
- LLM-generated report rendered as markdown (in a card)
- Suggestions for new articles, missing connections, research questions

**API:** `POST /api/lint { deep: false }`, `POST /api/lint { deep: true }`

---

## Shared Components

### Markdown Renderer
Use `react-markdown` with these plugins:
- `remark-gfm` (tables, strikethrough, task lists)
- `rehype-highlight` (code syntax highlighting)
- `rehype-raw` (inline HTML support)
- Custom plugin to transform `[[wiki-link|label]]` into React Router `<Link>` components

### Article Card
Reusable card with: title, summary (2-line clamp), tags, optional metadata (date, word count, score)

### Tag Pill
Colored pill component. Each tag gets a deterministic color from a palette.

### Search Input
Cmd+K global shortcut, autocomplete dropdown with article title suggestions.

### Loading States
Skeleton shimmer for cards, spinner for API calls, progress bar for batch operations.

### Toast Notifications
Bottom-right toast for: "Article compiled", "Answer filed to wiki", "Ingestion complete", errors.

### Empty States
Friendly illustrations + helpful message + CTA button for each page's empty state.

---

## Responsive Breakpoints

- **Desktop (≥1024px):** Full sidebar + content + right sidebar (article page)
- **Tablet (768-1023px):** Collapsed sidebar (icons only) + content
- **Mobile (<768px):** Bottom tab navigation, full-width content, no sidebars

---

## API Reference (for data binding)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | `{ raw_count, article_count, output_count, total_words }` |
| `/api/articles` | GET | `{ articles: [{ slug, title, summary, tags }] }` |
| `/api/articles/:slug` | GET | `{ slug, title, summary, tags, content }` |
| `/api/search?q=...&top_k=10` | GET | `{ query, results: [{ slug, title, summary, score, snippet }] }` |
| `/api/ask` | POST | `{ question, deep, file_back }` → `{ answer }` |
| `/api/sources` | GET | `{ documents: [{ title, type, compiled, ingested_at }] }` |
| `/api/ingest` | POST | `{ source: "url or path" }` → `{ status, path }` |
| `/api/compile` | POST | `{}` → `{ status, articles_created }` |
| `/api/lint` | POST | `{ deep: bool }` → `{ results/report }` |
| `/api/index/rebuild` | POST | `{}` → `{ status, article_count }` |

---

## Key UX Details

1. **Wiki-links are the core interaction** — clicking `[[concept]]` in article text seamlessly navigates to that article. If the target doesn't exist, show it as a red "broken link" that suggests creating it.

2. **Q&A answers should cite sources** — when the LLM references a wiki article, render it as a footnote-style citation that links to the article.

3. **Everything feeds back** — after asking a Q&A question with "file back" enabled, the new output should appear in the wiki sidebar article list without page refresh.

4. **The knowledge graph is a discovery tool** — users should be able to see clusters of related concepts and find unexpected connections.

5. **CJK support is essential** — the app must handle Chinese/Japanese/Korean text beautifully. Use Noto Serif SC for body text, ensure proper line breaking and text spacing.

6. **The markdown renderer is the most critical component** — articles may contain complex markdown (nested lists, tables with CJK text, code blocks, blockquotes with citations, wiki-links mixed with regular text). Test with real-world complex markdown.
