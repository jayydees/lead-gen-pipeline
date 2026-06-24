import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
PIPELINE_API_KEY = os.environ["PIPELINE_API_KEY"]

SEED_SEARCH_TERMS = [
    '"n8n certified" agency',
    '"Claude partner" agency AI',
    '"automation agency" remote UK',
    '"automation agency" remote Europe',
    '"AI implementation" agency remote',
    '"product engineering" agency remote',
    '"workflow automation" agency "small team"',
    '"AI agency" UK OR Europe remote',
    'automation consulting agency distributed team',
]

# Target: 10-20 qualified new companies per day
MAX_COMPANIES_PER_RUN = 20
MAX_RESULTS_PER_QUERY = 5  # search results to follow up per query
SCRAPE_TIMEOUT_SECONDS = 10

SCORING_RUBRIC = """
Score each company 0-100 based on these criteria:

- Region match (US/UK/EU explicitly confirmed): +25 points
- Remote-friendly signals ("remote", "distributed", "async", "globally"): +20 points
- AI/automation depth (mentions n8n, Claude, LLM, workflow automation, AI implementation): +30 points
- Small-to-medium size (team of <50, startup, boutique agency language): +10 points
- Contact available (email address or founder LinkedIn profile found): +15 points

Deduct 20 points if the company appears to be a large enterprise (500+ employees, Fortune 500 client language).
Deduct 10 points if no English content found.
"""

SHEET_COLUMNS = [
    "Date Found",
    "Company Name",
    "Website",
    "Location",
    "Size Signal",
    "Remote Signal",
    "AI/Automation Stack",
    "Founder Name",
    "LinkedIn URL",
    "Contact Email",
    "Score",
    "Why",
]
