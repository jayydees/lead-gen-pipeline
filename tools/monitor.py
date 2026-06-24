"""Writes a Runs Log tab to the Google Sheet after every pipeline run."""
import json
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

LOG_COLUMNS = [
    "Timestamp (UTC)",
    "Duration (s)",
    "Raw Submitted",
    "Passed Validation",
    "Failed Validation",
    "Passed Eval",
    "Failed Eval (LLM)",
    "Written to Sheet",
    "Score Inflation Warning",
    "Eval Rejections",
    "Errors",
]


def _client():
    creds_data = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_log_tab(gc):
    spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
    try:
        ws = spreadsheet.worksheet("Runs Log")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title="Runs Log", rows=500, cols=len(LOG_COLUMNS))
        ws.append_row(LOG_COLUMNS, value_input_option="USER_ENTERED")
        # Bold the header
        ws.format("A1:K1", {"textFormat": {"bold": True}})
    return ws


def log_run(
    duration_s: float,
    raw_submitted: int,
    passed_validation: int,
    failed_validation: int,
    passed_eval: int,
    failed_eval: int,
    written: int,
    score_inflation_warning: str = "",
    eval_rejections: str = "",
    errors: str = "",
):
    try:
        gc = _client()
        ws = _get_or_create_log_tab(gc)
        ws.append_row(
            [
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                round(duration_s, 1),
                raw_submitted,
                passed_validation,
                failed_validation,
                passed_eval,
                failed_eval,
                written,
                score_inflation_warning,
                eval_rejections,
                errors,
            ],
            value_input_option="USER_ENTERED",
        )
    except Exception as e:
        print(f"[monitor] Log failed: {e}")
