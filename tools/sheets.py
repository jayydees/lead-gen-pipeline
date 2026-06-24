import json
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON, SHEET_COLUMNS

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _client():
    creds_data = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    return gspread.authorize(creds)


def get_seen_domains() -> set[str]:
    """Return the set of website domains already in the sheet."""
    gc = _client()
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1

    records = sheet.get_all_records()
    if not records:
        return set()

    seen = set()
    for row in records:
        url = row.get("Website", "").strip().lower()
        if url:
            domain = url.replace("https://", "").replace("http://", "").rstrip("/").split("/")[0]
            seen.add(domain)
    return seen


def ensure_header(sheet):
    existing = sheet.row_values(1)
    if existing != SHEET_COLUMNS:
        sheet.insert_row(SHEET_COLUMNS, 1)


def append_companies(companies: list[dict]) -> str:
    """Append a list of company dicts to the sheet. Returns a status string."""
    if not companies:
        return "No companies to append."

    gc = _client()
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
    ensure_header(sheet)

    rows = []
    for c in companies:
        rows.append([c.get(col, "") for col in SHEET_COLUMNS])

    sheet.append_rows(rows, value_input_option="USER_ENTERED")
    return f"Appended {len(rows)} companies to Google Sheet."
