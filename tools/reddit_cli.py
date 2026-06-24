import subprocess


def search_reddit(query: str, max_posts: int = 10) -> str:
    """Search Reddit via rdt-cli (no login needed for search)."""
    try:
        result = subprocess.run(
            ["rdt", "search", query, "--limit", str(max_posts)],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return f"Reddit CLI error: {result.stderr.strip()}"
        return (result.stdout or "No results found.")[:4000]
    except FileNotFoundError:
        return "rdt-cli not installed. Run: pipx install rdt-cli"
    except subprocess.TimeoutExpired:
        return "Reddit search timed out."
    except Exception as e:
        return f"Reddit search error: {e}"
