"""DefiLlama reference source plugin."""

PLUGIN_ID = "defillama"
PLUGIN_NAME = {
    "en": "DefiLlama",
    "zh": "DefiLlama",
    "ja": "DefiLlama",
}


def get_source_url(source: dict) -> str:
    """Build DefiLlama permalink from source metadata."""
    protocol = source.get("protocol", "")
    if protocol:
        return f"https://defillama.com/protocol/{protocol}"
    chain = source.get("chain", "")
    if chain:
        return f"https://defillama.com/chain/{chain}"
    return source.get("url", "")
