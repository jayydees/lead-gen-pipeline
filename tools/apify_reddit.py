import json
from apify_client import ApifyClient
from config import APIFY_API_KEY

_client = ApifyClient(token=APIFY_API_KEY)


def search_reddit(query: str, max_posts: int = 10) -> str:
    """Search Reddit for posts and comments matching a query. Returns posts as a string."""
    try:
        run = _client.actor("trudax/reddit-scraper-lite").call(
            run_input={
                "searches": [query],
                "maxPostCount": max_posts,
                "maxComments": 5,
            }
        )
        items = list(_client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return "No Reddit posts found."
        posts = [
            {
                "title": p.get("title", ""),
                "url": p.get("url", ""),
                "subreddit": p.get("subreddit", ""),
                "body": (p.get("body") or "")[:500],
                "score": p.get("score", 0),
                "comments": [
                    c.get("body", "")[:300]
                    for c in (p.get("comments") or [])[:3]
                ],
            }
            for p in items[:max_posts]
        ]
        return json.dumps(posts)
    except Exception as e:
        return f"Reddit scrape error: {e}"
