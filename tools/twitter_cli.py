import subprocess


def search_twitter(query: str, limit: int = 10) -> str:
    """Search Twitter via twitter-cli. Requires TWITTER_AUTH_TOKEN + TWITTER_CT0 env vars."""
    try:
        result = subprocess.run(
            ["twitter", "search", query, "-n", str(limit), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return f"Twitter CLI error: {result.stderr.strip()}"
        return (result.stdout or "No results found.")[:4000]
    except FileNotFoundError:
        return "twitter-cli not installed. Run: pipx install twitter-cli"
    except subprocess.TimeoutExpired:
        return "Twitter search timed out."
    except Exception as e:
        return f"Twitter search error: {e}"
