import json
from apify_client import ApifyClient
from config import APIFY_API_KEY

_client = ApifyClient(token=APIFY_API_KEY)


def scrape_linkedin_company(linkedin_url: str) -> str:
    """Scrape a LinkedIn company page via Apify. Returns company details as a string."""
    try:
        run = _client.actor("apify/linkedin-company-scraper").call(
            run_input={
                "startUrls": [{"url": linkedin_url}],
                "count": 1,
                "proxy": {"useApifyProxy": True},
            }
        )
        items = list(_client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return "No LinkedIn data found."
        c = items[0]
        result = {
            "name": c.get("name", ""),
            "description": c.get("description", ""),
            "website": c.get("website", ""),
            "employee_count": c.get("employeeCount", ""),
            "specialties": c.get("specialties", []),
            "headquarters": c.get("headquarters", ""),
            "founded": c.get("founded", ""),
        }
        return json.dumps(result)
    except Exception as e:
        return f"LinkedIn scrape error: {e}"
