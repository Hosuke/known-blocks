"""Taxonomy generator — auto-generate hierarchical categories from wiki articles."""

import json
from pathlib import Path

import frontmatter

from .config import load_config
from .llm import chat

SYSTEM_PROMPT = """You are a classical knowledge taxonomy specialist.
Generate a hierarchical category structure from the given article tags and titles.
Follow the tradition of Chinese bibliography (四库全书 classification) for Chinese classics,
and standard academic taxonomy for other domains."""


def generate_taxonomy(base_dir: Path | None = None) -> dict:
    """Analyze all wiki articles and generate a hierarchical taxonomy."""
    cfg = load_config(base_dir)
    concepts_dir = Path(cfg["paths"]["concepts"])
    meta_dir = Path(cfg["paths"]["meta"])

    # Collect all article metadata
    articles = []
    all_tags = set()
    all_books = set()

    for md_file in sorted(concepts_dir.glob("*.md")):
        post = frontmatter.load(str(md_file))
        tags = post.metadata.get("tags", [])
        all_tags.update(tags)
        articles.append({
            "slug": md_file.stem,
            "title": post.metadata.get("title", md_file.stem),
            "tags": tags,
            "summary": post.metadata.get("summary", ""),
        })

    # Also check raw docs for book/source metadata
    raw_dir = Path(cfg["paths"]["raw"])
    if raw_dir.exists():
        for d in raw_dir.iterdir():
            idx = d / "index.md"
            if idx.exists():
                post = frontmatter.load(str(idx))
                book = post.metadata.get("book", "")
                if book:
                    all_books.add(book)

    if not articles:
        return {"categories": []}

    # Ask LLM to generate taxonomy
    prompt = f"""Given these wiki articles about classical texts, generate a hierarchical taxonomy.

Articles ({len(articles)} total):
{json.dumps([{"title": a["title"], "tags": a["tags"]} for a in articles[:50]], ensure_ascii=False, indent=2)}

All tags: {sorted(all_tags)}
Source books: {sorted(all_books)}

Generate a JSON taxonomy with this structure:
{{
  "categories": [
    {{
      "id": "jing",
      "label": "經部",
      "label_en": "Classics",
      "children": [
        {{"id": "sishu", "label": "四書", "label_en": "Four Books", "tags": ["confucianism", "analects", "mencius"]}},
        {{"id": "wujing", "label": "五經", "label_en": "Five Classics", "tags": ["poetry", "history"]}}
      ]
    }},
    ...
  ]
}}

Rules:
- Use traditional Chinese bibliography categories where applicable
- Each leaf node has a "tags" array mapping to existing article tags
- Include both Chinese and English labels
- Group logically: 經部 (classics), 子部 (philosophers), 佛部 (Buddhism), 道部 (Daoism), etc.
- Keep it practical: 2-3 levels max
- Only output valid JSON, no other text"""

    response = chat(prompt, system=SYSTEM_PROMPT, max_tokens=4096)

    # Parse JSON from response
    try:
        # Find JSON in response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            taxonomy = json.loads(response[start:end])
        else:
            taxonomy = {"categories": []}
    except json.JSONDecodeError:
        taxonomy = {"categories": []}

    # Save taxonomy
    meta_dir.mkdir(parents=True, exist_ok=True)
    taxonomy_path = meta_dir / "taxonomy.json"
    taxonomy_path.write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False), encoding="utf-8")

    return taxonomy


def load_taxonomy(base_dir: Path | None = None) -> dict:
    """Load existing taxonomy."""
    cfg = load_config(base_dir)
    meta_dir = Path(cfg["paths"]["meta"])
    taxonomy_path = meta_dir / "taxonomy.json"
    if taxonomy_path.exists():
        return json.loads(taxonomy_path.read_text())
    return {"categories": []}
