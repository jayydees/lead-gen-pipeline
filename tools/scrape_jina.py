import requests


def scrape(url: str) -> str:
    """Fetch a URL via Jina Reader — returns clean markdown, handles JS-heavy sites."""
    try:
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "text/plain", "X-Return-Format": "markdown"},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.text[:6000]
    except Exception as e:
        return f"Scrape error: {e}"
