"""Local agent: same Gemini loop as agent.py, but uses better local tools."""
from agent import run_agent as _run_agent
from config import TWITTER_SEED_QUERIES
from tools.scrape_jina import scrape as _jina_scrape
from tools.twitter_cli import search_twitter as _twitter_cli


def _local_pre_discover() -> str:
    """Pre-discovery using local Twitter CLI."""
    parts = []

    for query in TWITTER_SEED_QUERIES[:2]:
        result = _twitter_cli(query, limit=5)
        if result and "error" not in result.lower() and "not installed" not in result.lower():
            parts.append(f"TWITTER — '{query}':\n{result}")
            print(f"[local] Twitter pre-discovery OK: {query}")
        else:
            print(f"[local] Twitter pre-discovery skipped: {result[:80]}")

    return "\n\n---\n\n".join(parts)


def run_agent(seen_domains=None, seed_context="") -> dict:
    if not seed_context:
        print("[local] Running local pre-discovery (Twitter CLI)...")
        seed_context = _local_pre_discover()

    return _run_agent(
        seen_domains=seen_domains,
        seed_context=seed_context,
        tools_override={
            "scrape": _jina_scrape,
            "search_twitter": _twitter_cli,
        },
    )
