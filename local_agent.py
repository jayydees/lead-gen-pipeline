"""Local agent: same Gemini loop as agent.py, but uses better local tools."""
from agent import run_agent as _run_agent
from config import TWITTER_SEED_QUERIES
from tools.scrape_jina import scrape as _jina_scrape
from tools.reddit_cli import search_reddit as _rdt
from tools.twitter_cli import search_twitter as _twitter_cli


def _local_pre_discover() -> str:
    """Pre-discovery using local CLI tools (rdt-cli + twitter-cli)."""
    parts = []

    for query in ["AI automation agency recommend hire remote", "n8n agency OR make.com agency hire freelancer"]:
        result = _rdt(query, max_posts=5)
        if result and "error" not in result.lower() and "not installed" not in result.lower():
            parts.append(f"REDDIT — '{query}':\n{result}")
            print(f"[local] Reddit pre-discovery OK: {query}")
        else:
            print(f"[local] Reddit pre-discovery skipped: {result[:80]}")

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
        print("[local] Running local pre-discovery (Reddit + Twitter CLI)...")
        seed_context = _local_pre_discover()

    return _run_agent(
        seen_domains=seen_domains,
        seed_context=seed_context,
        tools_override={
            "scrape": _jina_scrape,        # Jina Reader > requests+BS4
            "search_reddit": _rdt,          # rdt-cli, free, no Apify
            "search_twitter": _twitter_cli, # twitter-cli, free, no Apify
        },
    )
