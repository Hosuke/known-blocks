"""Rekt.news reference source plugin."""

PLUGIN_ID = "rekt"
PLUGIN_NAME = {
    "en": "Rekt News",
    "zh": "Rekt 安全事件",
    "ja": "Rekt ニュース",
}


def get_source_url(source: dict) -> str:
    """Build rekt.news permalink from source metadata."""
    return source.get("url", "")
