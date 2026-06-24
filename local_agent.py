"""Local agent: same Gemini loop as agent.py, but uses better local tools."""
from agent import run_agent as _run_agent
from tools.scrape_jina import scrape as _jina_scrape
from tools.reddit_cli import search_reddit as _rdt
from tools.twitter_cli import search_twitter as _twitter_cli


def run_agent(seen_domains=None) -> dict:
    return _run_agent(
        seen_domains=seen_domains,
        tools_override={
            "scrape": _jina_scrape,       # Jina Reader > requests+BS4
            "search_reddit": _rdt,         # rdt-cli, free, no Apify
            "search_twitter": _twitter_cli, # twitter-cli, free, no Apify
        },
    )
