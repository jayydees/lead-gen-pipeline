import time
from datetime import datetime, timezone

from agent import run_agent
from tools.sheets import get_seen_domains

# Mutable state shared with main.py's /status endpoint
last_run: dict = {}


def run_pipeline() -> dict:
    """Run one full pipeline cycle. Returns a status dict."""
    started_at = datetime.now(timezone.utc)
    t0 = time.monotonic()

    try:
        seen_domains = get_seen_domains()
        result = run_agent(seen_domains=seen_domains)

        elapsed = time.monotonic() - t0
        status = {
            "status": "ok",
            "started_at": started_at.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "companies_found": result["count"],
            "notification_sent": result["notification_sent"],
            "summary": result["summary"],
        }
    except Exception as exc:
        elapsed = time.monotonic() - t0
        status = {
            "status": "error",
            "started_at": started_at.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "error": str(exc),
        }

    last_run.update(status)
    return status


if __name__ == "__main__":
    result = run_pipeline()
    print(result)
