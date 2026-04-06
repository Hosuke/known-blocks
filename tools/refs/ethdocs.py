"""Ethereum.org documentation reference source plugin."""

PLUGIN_ID = "ethdocs"
PLUGIN_NAME = {
    "en": "Ethereum.org Docs",
    "zh": "以太坊官方文档",
    "ja": "Ethereum.org ドキュメント",
}


def get_source_url(source: dict) -> str:
    """Build ethereum.org permalink from source metadata."""
    section = source.get("section", "")
    if section:
        return f"https://ethereum.org/en/developers/docs/{section}/"
    return source.get("url", "")
