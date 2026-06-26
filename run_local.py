"""
Local pipeline runner — uses Jina scraping, rdt-cli Reddit, twitter-cli Twitter.
Run: python run_local.py
"""
import os
import re
import sys

# BOM-aware .env loading (handles files saved by Notepad/VS Code on Windows)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8-sig") as _f:
        _content = _f.read()

    def _extract_env(content, key):
        m = re.search(rf"^{key}\s*=\s*'(.*?)'", content, re.DOTALL | re.MULTILINE)
        if m:
            return m.group(1)
        m = re.search(rf'^{key}\s*=\s*"(.*?)"', content, re.DOTALL | re.MULTILINE)
        if m:
            return m.group(1)
        m = re.search(rf"^{key}\s*=\s*(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return ""

    _keys = [
        "GEMINI_API_KEY", "EXA_API_KEY", "APIFY_API_KEY",
        "GOOGLE_SHEET_ID", "GOOGLE_CREDENTIALS_JSON",
        "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "PIPELINE_API_KEY",
        "TWITTER_AUTH_TOKEN", "TWITTER_CT0",
    ]
    for _k in _keys:
        _v = _extract_env(_content, _k)
        if _v:
            os.environ.setdefault(_k, _v)
else:
    print("WARNING: .env file not found — using system environment variables.")

from local_agent import run_agent
from pipeline import run_pipeline

print("=" * 60)
print("  Lead Gen — Local Runner")
print("  Channels: Exa · Jina scraping · Twitter (Apify) · LinkedIn (Apify)")
print("=" * 60)
print()

result = run_pipeline(agent_fn=run_agent, pre_discover_fn=lambda: "")  # local_agent handles pre-discovery itself

print()
print("=" * 60)
status = result.get("status", "unknown")
if status == "ok":
    print(f"  ✓ Done in {result.get('elapsed_seconds', '?')}s")
    print(f"  Raw found:          {result.get('companies_raw', 0)}")
    print(f"  Validation passed:  {result.get('companies_raw', 0) - result.get('validation_rejected', 0)}")
    print(f"  Eval passed:        {result.get('companies_raw', 0) - result.get('validation_rejected', 0) - result.get('eval_rejected', 0)}")
    print(f"  Written to sheet:   {result.get('companies_written', 0)}")
    print(f"  Notification sent:  {result.get('notification_sent', False)}")
else:
    print(f"  ✗ Error: {result.get('error', 'unknown')}")
print("=" * 60)
