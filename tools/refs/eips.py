"""Ethereum EIP/ERC standards reference source plugin."""

PLUGIN_ID = "eips"
PLUGIN_NAME = {
    "en": "Ethereum EIPs",
    "zh": "以太坊改进提案",
    "ja": "イーサリアム改善提案",
}


def get_source_url(source: dict) -> str:
    """Build EIP permalink from source metadata."""
    eip_number = source.get("eip_number", "")
    if eip_number:
        return f"https://eips.ethereum.org/EIPS/eip-{eip_number}"
    return source.get("url", "")
