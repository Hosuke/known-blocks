"""L2Beat reference source plugin."""

PLUGIN_ID = "l2beat"
PLUGIN_NAME = {
    "en": "L2Beat",
    "zh": "L2Beat",
    "ja": "L2Beat",
}


def get_source_url(source: dict) -> str:
    """Build L2Beat permalink from source metadata."""
    l2_name = source.get("l2_name", "")
    if l2_name:
        return f"https://l2beat.com/scaling/projects/{l2_name}"
    return source.get("url", "")
