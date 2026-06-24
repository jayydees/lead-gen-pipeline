from exa_py import Exa
from config import EXA_API_KEY

_client = Exa(api_key=EXA_API_KEY)


def search(query: str, max_results: int = 5) -> list[dict]:
    """Search via Exa and return title, url, and highlights for each result."""
    try:
        response = _client.search_and_contents(
            query,
            type="auto",
            num_results=max_results,
            highlights=True,
        )
        results = []
        for r in response.results:
            snippet = " ".join(r.highlights) if r.highlights else ""
            results.append({
                "title": r.title or "",
                "url": r.url,
                "snippet": snippet,
            })
        return results
    except Exception as e:
        print(f"Search error for '{query}': {e}")
        return []
