import json
import re
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON, SHEET_COLUMNS

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _client():
    creds_data = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    return gspread.authorize(creds)


def _normalize_domain(url: str) -> str:
    url = url.strip().lower()
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    return url.rstrip("/").split("/")[0]


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def get_seen_domains() -> set[str]:
    """Return the set of website domains already in the sheet."""
    gc = _client()
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
    records = sheet.get_all_records()
    seen = set()
    for row in records:
        url = row.get("Website", "")
        if url:
            seen.add(_normalize_domain(url))
    return seen


def _get_seen_keys(sheet) -> tuple[set[str], set[str]]:
    """Return (seen_domains, seen_names) from the current sheet contents."""
    records = sheet.get_all_records()
    domains, names = set(), set()
    for row in records:
        url = row.get("Website", "")
        name = row.get("Company Name", "")
        if url:
            domains.add(_normalize_domain(url))
        if name:
            names.add(_normalize_name(name))
    return domains, names


def ensure_header(sheet):
    existing = sheet.row_values(1)
    if existing != SHEET_COLUMNS:
        sheet.insert_row(SHEET_COLUMNS, 1)


def append_companies(companies: list[dict]) -> str:
    """Append companies to the sheet, skipping any duplicates. Returns a status string."""
    if not companies:
        return "No companies to append."

    gc = _client()
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
    ensure_header(sheet)

    seen_domains, seen_names = _get_seen_keys(sheet)

    rows = []
    skipped = []
    for c in companies:
        domain = _normalize_domain(c.get("Website", ""))
        name = _normalize_name(c.get("Company Name", ""))

        if domain and domain in seen_domains:
            skipped.append(c.get("Company Name", domain))
            continue
        if name and name in seen_names:
            skipped.append(c.get("Company Name", name))
            continue

        rows.append([c.get(col, "") for col in SHEET_COLUMNS])
        # Track inline so two entries in the same batch don't dupe each other
        if domain:
            seen_domains.add(domain)
        if name:
            seen_names.add(name)

    if rows:
        sheet.append_rows(rows, value_input_option="USER_ENTERED")

    msg = f"Appended {len(rows)} companies to Google Sheet."
    if skipped:
        msg += f" Skipped {len(skipped)} duplicates: {', '.join(skipped)}."
    return msg
