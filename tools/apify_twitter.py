import json
from apify_client import ApifyClient
from config import APIFY_API_KEY

_client = ApifyClient(token=APIFY_API_KEY)


def search_twitter(query: str, max_tweets: int = 10) -> str:
    """Search Twitter/X for recent posts about a company. Returns tweets as a string."""
    try:
        run = _client.actor("apidojo/tweet-scraper").call(
            run_input={
                "searchTerms": [query],
                "maxItems": max_tweets,
                "sort": "Latest",
            }
        )
        items = list(_client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return "No tweets found."
        tweets = [
            {
                "text": t.get("text", ""),
                "author": t.get("author", {}).get("userName", ""),
                "created_at": t.get("createdAt", ""),
                "likes": t.get("likeCount", 0),
            }
            for t in items[:max_tweets]
        ]
        return json.dumps(tweets)
    except Exception as e:
        return f"Twitter scrape error: {e}"
