"""Dune Spellbook reference source plugin."""

PLUGIN_ID = "spellbook"
PLUGIN_NAME = {
    "en": "Dune Spellbook",
    "zh": "Dune 魔法书",
    "ja": "Dune スペルブック",
}


def get_source_url(source: dict) -> str:
    """Build Spellbook GitHub permalink from source metadata."""
    protocol = source.get("protocol", "")
    if protocol:
        return f"https://github.com/duneanalytics/spellbook/tree/main/sources/{protocol}"
    return source.get("url", "")
