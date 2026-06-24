"""One-time script to clean up the Google Sheet: dedup, fix malformed dates, remove N/A."""
import json
import os
import re
from datetime import date
from dotenv import load_dotenv

load_dotenv()

import gspread
from google.oauth2.service_account import Credentials

# Load only what this script needs — avoids requiring all env vars
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
SHEET_COLUMNS = [
    "Date Found", "Company Name", "Website", "Location", "Size Signal",
    "Remote Signal", "AI/Automation Stack", "Founder Name", "LinkedIn URL",
    "Contact Email", "Score", "Why", "Source",
]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _normalize_domain(url: str) -> str:
    url = url.strip().lower()
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    return url.rstrip("/").split("/")[0]


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _clean_date(val: str) -> str:
    """Extract just the date portion from malformed Date Found values."""
    if not val:
        return date.today().isoformat()
    match = re.search(r"\d{4}-\d{2}-\d{2}", val)
    return match.group(0) if match else date.today().isoformat()


def _clean_value(val: str) -> str:
    """Replace N/A placeholder with empty string."""
    return "" if str(val).strip() in ("N/A", "n/a", "N/a") else str(val).strip()


def main():
    creds_data = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1

    all_rows = sheet.get_all_values()
    print(f"Total rows (including headers): {len(all_rows)}")

    # Collect data rows — skip any row that looks like a header
    data_rows = []
    for row in all_rows:
        if not row or row[0] in ("Date Found", ""):
            continue
        # Pad row to match column count
        while len(row) < len(SHEET_COLUMNS):
            row.append("")
        data_rows.append(row)

    print(f"Data rows found: {len(data_rows)}")

    # Map to dicts using the position of SHEET_COLUMNS
    # Detect column order from header row (first row)
    header = all_rows[0] if all_rows else SHEET_COLUMNS
    col_idx = {col: i for i, col in enumerate(header) if col in SHEET_COLUMNS}

    def get(row, col):
        idx = col_idx.get(col)
        if idx is None or idx >= len(row):
            return ""
        return row[idx]

    # Deduplicate — keep first occurrence by domain, then by name
    seen_domains, seen_names = set(), set()
    clean_rows = []
    skipped = []

    for row in data_rows:
        website = get(row, "Website")
        name = get(row, "Company Name")
        domain = _normalize_domain(website)
        norm_name = _normalize_name(name)

        if domain and domain in seen_domains:
            skipped.append(name or domain)
            continue
        if norm_name and norm_name in seen_names:
            skipped.append(name)
            continue

        # Clean each field
        cleaned = {col: _clean_value(get(row, col)) for col in SHEET_COLUMNS}
        cleaned["Date Found"] = _clean_date(cleaned["Date Found"])

        clean_rows.append([cleaned[col] for col in SHEET_COLUMNS])

        if domain:
            seen_domains.add(domain)
        if norm_name:
            seen_names.add(norm_name)

    print(f"Unique companies after dedup: {len(clean_rows)}")
    print(f"Skipped duplicates: {skipped}")

    # Rewrite sheet: clear → header → data
    sheet.clear()
    sheet.append_row(SHEET_COLUMNS, value_input_option="USER_ENTERED")
    if clean_rows:
        sheet.append_rows(clean_rows, value_input_option="USER_ENTERED")

    print("Sheet cleaned and rewritten successfully.")
    for r in clean_rows:
        print(f"  {r[1]} | {r[2]} | score={r[10]}")


if __name__ == "__main__":
    main()
