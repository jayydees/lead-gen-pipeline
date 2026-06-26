"""Local agent: same Gemini loop as agent.py, but uses Jina for scraping."""
from agent import run_agent as _run_agent
from tools.scrape_jina import scrape as _jina_scrape


def run_agent(seen_domains=None, seed_context="") -> dict:
    return _run_agent(
        seen_domains=seen_domains,
        seed_context=seed_context,
        tools_override={
            "scrape": _jina_scrape,
        },
    )
