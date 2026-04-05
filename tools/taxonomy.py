"""Taxonomy — hierarchical categories with multilingual labels."""

import json
import re
from pathlib import Path
from collections import defaultdict

import frontmatter

from .config import load_config

# Pre-defined top-level categories with multilingual labels
# Articles are mapped by matching their tags against these patterns
# Patterns support both English/pinyin and Chinese to match real article tags
HIERARCHY = [
    {
        "id": "confucianism",
        "label": {"en": "Confucianism", "zh": "儒家", "ja": "儒教"},
        "match": ["confuci", "analects", "mencius", "mengzi", "lunyu", "junzi", "ren", "li-", "xiao",
                  "benevolence", "virtue", "filial", "ritual", "propriety", "four-books", "five-classics",
                  "doctrine-of-the-mean", "great-learning", "zhongyong", "daxue",
                  "儒", "论语", "孟子", "仁", "礼", "孝", "大学", "中庸", "四书", "五经",
                  "君子", "圣人", "仁义", "儒学", "儒教", "经学"],
        "children": [
            {"id": "analects", "label": {"en": "Analects", "zh": "论语", "ja": "論語"},
             "match": ["analects", "lunyu", "xue-er", "confucius-analects", "论语"]},
            {"id": "mencius", "label": {"en": "Mencius", "zh": "孟子", "ja": "孟子"},
             "match": ["mencius", "mengzi", "mencius-", "孟子"]},
            {"id": "daxue", "label": {"en": "Great Learning", "zh": "大学", "ja": "大学"},
             "match": ["great-learning", "daxue", "sincerity", "self-cultivation", "大学"]},
            {"id": "zhongyong", "label": {"en": "Doctrine of the Mean", "zh": "中庸", "ja": "中庸"},
             "match": ["mean", "zhongyong", "central-harmony", "zhonghe", "中庸"]},
            {"id": "confucian-ethics", "label": {"en": "Ethics & Virtues", "zh": "伦理道德", "ja": "倫理道徳"},
             "match": ["ethics", "virtue", "moral", "benevolent", "governance", "trust",
                       "伦理", "道德", "仁义"]},
        ]
    },
    {
        "id": "buddhism",
        "label": {"en": "Buddhism", "zh": "佛教", "ja": "仏教"},
        "match": ["buddh", "sutra", "dharma", "nirvana", "bodhisattva", "arhat", "tathagata",
                  "agama", "mahayana", "meditation", "karmic", "sangha", "tripitaka",
                  "brahma", "contemplation", "defilement", "liberation", "eight-noble",
                  "佛", "佛教", "佛学", "大乘", "小乘", "菩萨", "般若", "涅槃", "空",
                  "禅", "禅宗", "净土", "念佛", "参禅", "戒律", "修行", "因果",
                  "轮回", "解脱", "三宝", "僧", "经藏", "律藏", "论藏",
                  "唯识", "中观", "华严", "天台", "密宗", "律宗",
                  "高僧", "法师", "明代佛教", "近代佛教", "民国佛教",
                  "佛学辞典", "佛教百科", "佛学家", "词典编纂",
                  "憨山", "紫柏", "四大高僧", "梦游集"],
        "children": [
            {"id": "agama", "label": {"en": "Agama Sutras", "zh": "阿含经", "ja": "阿含経"},
             "match": ["agama", "changahan", "shi-bao", "阿含"]},
            {"id": "cosmology", "label": {"en": "Cosmology", "zh": "宇宙观", "ja": "宇宙論"},
             "match": ["cosmolog", "heaven", "caste", "realm", "world", "宇宙", "天界", "六道"]},
            {"id": "practice", "label": {"en": "Practice & Path", "zh": "修行", "ja": "修行"},
             "match": ["meditat", "practice", "path", "contemplat", "liberation", "stages",
                       "修行", "禅修", "念佛", "参禅", "戒定慧", "三学", "八正道",
                       "禅净双修", "观心", "止观", "修行法门", "修行法門"]},
            {"id": "doctrine", "label": {"en": "Doctrine", "zh": "教义", "ja": "教義"},
             "match": ["doctrine", "dependent", "aggregate", "noble", "dharma", "truth",
                       "教义", "四谛", "四諦", "十二因缘", "十二因緣", "缘起", "空性",
                       "佛教哲学", "佛教哲學", "中觀"]},
            {"id": "figures", "label": {"en": "Figures", "zh": "人物", "ja": "人物"},
             "match": ["高僧", "法师", "四大高僧", "憨山", "紫柏", "丁福保", "佛学家",
                       "龙树", "龍樹", "鸠摩罗什", "僧肇"]},
            {"id": "texts", "label": {"en": "Texts & References", "zh": "经典文献", "ja": "典籍"},
             "match": ["佛学辞典", "佛教百科", "词典编纂", "工具书", "梦游集", "肇论",
                       "楞严", "法华", "心经", "金刚经", "大乘起信论"]},
        ]
    },
    {
        "id": "daoism",
        "label": {"en": "Daoism", "zh": "道家", "ja": "道教"},
        "match": ["dao", "tao", "laozi", "zhuangzi", "wuwei", "yin-yang", "daodejing",
                  "道家", "道教", "老子", "庄子", "道德经", "无为", "阴阳", "太极"],
        "children": []
    },
    {
        "id": "mohism",
        "label": {"en": "Mohism", "zh": "墨家", "ja": "墨家"},
        "match": ["mohis", "mozi", "jian-ai", "universal-love", "墨家", "墨子", "兼爱"],
        "children": []
    },
    {
        "id": "classics",
        "label": {"en": "Classical Studies", "zh": "经学", "ja": "経学"},
        "match": ["classic", "text-stud", "hermeneutic", "translation", "manuscript", "canon",
                  "commentary", "scholarship", "textual", "philolog",
                  "经学", "训诂", "注疏", "版本学", "校勘"],
        "children": []
    },
    {
        "id": "non-target",
        "label": {"en": "Non-target (Archive)", "zh": "非目标（存档）", "ja": "対象外（アーカイブ）"},
        "match": ["non-target", "ollama", "gemma", "quantiz", "gguf", "llm-tool", "ai-model"],
        "children": []
    },
]


def generate_taxonomy(base_dir: Path | None = None) -> dict:
    """Generate and save taxonomy. Called by worker."""
    categories = build_taxonomy(base_dir, lang="zh")
    cfg = load_config(base_dir)
    meta_dir = Path(cfg["paths"]["meta"])
    meta_dir.mkdir(parents=True, exist_ok=True)
    result = {"categories": categories}
    path = meta_dir / "taxonomy.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def build_taxonomy(base_dir: Path | None = None, lang: str = "zh") -> list[dict]:
    """Build hierarchical taxonomy from articles, with labels in the requested language."""
    cfg = load_config(base_dir)
    concepts_dir = Path(cfg["paths"]["concepts"])

    if not concepts_dir.exists():
        return []

    # Load all articles
    articles = []
    for md_file in sorted(concepts_dir.glob("*.md")):
        post = frontmatter.load(str(md_file))
        articles.append({
            "slug": md_file.stem,
            "title": post.metadata.get("title", md_file.stem),
            "tags": [t.lower().replace(" ", "-") for t in post.metadata.get("tags", [])],
            "summary": post.metadata.get("summary", ""),
        })

    # Assign articles to categories
    assigned = set()
    result = []

    for cat in HIERARCHY:
        cat_articles, child_cats = _match_category(cat, articles, assigned, lang)
        if cat_articles or child_cats:
            entry = {
                "id": cat["id"],
                "label": cat["label"].get(lang, cat["label"].get("en", cat["id"])),
                "count": len(cat_articles),
                "articles": cat_articles,
                "children": child_cats,
            }
            # Total count includes children
            entry["total"] = entry["count"] + sum(c["count"] for c in child_cats)
            result.append(entry)

    # Collect unassigned into "Other"
    unassigned = [a for a in articles if a["slug"] not in assigned]
    if unassigned:
        other_label = {"en": "Other", "zh": "其他", "ja": "その他"}
        result.append({
            "id": "other",
            "label": other_label.get(lang, "Other"),
            "count": len(unassigned),
            "total": len(unassigned),
            "articles": [{"slug": a["slug"], "title": a["title"]} for a in unassigned],
            "children": [],
        })

    return result


def _match_category(cat: dict, articles: list, assigned: set, lang: str) -> tuple[list, list]:
    """Match articles to a category and its children."""
    cat_patterns = [p.lower() for p in cat.get("match", [])]

    # Process children first (more specific matches)
    child_results = []
    for child in cat.get("children", []):
        child_patterns = [p.lower() for p in child.get("match", [])]
        child_articles = []
        for a in articles:
            if a["slug"] in assigned:
                continue
            slug_tags = a["slug"] + " " + " ".join(a["tags"])
            if any(p in slug_tags for p in child_patterns):
                child_articles.append({"slug": a["slug"], "title": a["title"]})
                assigned.add(a["slug"])
        if child_articles:
            child_results.append({
                "id": child["id"],
                "label": child["label"].get(lang, child["label"].get("en", child["id"])),
                "count": len(child_articles),
                "articles": child_articles,
                "children": [],
            })

    # Then match remaining to parent
    parent_articles = []
    for a in articles:
        if a["slug"] in assigned:
            continue
        slug_tags = a["slug"] + " " + " ".join(a["tags"])
        if any(p in slug_tags for p in cat_patterns):
            parent_articles.append({"slug": a["slug"], "title": a["title"]})
            assigned.add(a["slug"])

    return parent_articles, child_results


def load_taxonomy(base_dir: Path | None = None) -> dict:
    """Load cached taxonomy."""
    cfg = load_config(base_dir)
    meta_dir = Path(cfg["paths"]["meta"])
    path = meta_dir / "taxonomy.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"categories": []}
