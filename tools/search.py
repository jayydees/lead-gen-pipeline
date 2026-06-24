from duckduckgo_search import DDGS


def search(query: str, max_results: int = 5) -> list[dict]:
    """Run a web search and return title, url, snippet for each result."""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception as e:
        print(f"Search error for '{query}': {e}")
    return results
