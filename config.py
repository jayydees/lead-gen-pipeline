import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
EXA_API_KEY = os.environ["EXA_API_KEY"]
APIFY_API_KEY = os.environ["APIFY_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
PIPELINE_API_KEY = os.environ["PIPELINE_API_KEY"]

SEED_SEARCH_TERMS = [
    # Clutch directory
    'site:clutch.co "automation" "AI" "small business" remote agency',
    'site:clutch.co "n8n" OR "workflow automation" agency',
    'site:clutch.co "AI implementation" boutique agency UK',
    'site:clutch.co "product engineering" remote agency Europe',
    # Direct web
    '"n8n certified partner" agency',
    '"LLM integration" agency "product engineering" remote',
    '"built with Claude" OR "powered by Claude" agency',
    '"workflow automation agency" "we are a team" OR "small team" remote',
    # LinkedIn discovery (Exa finds company pages; use scrape_linkedin_company to enrich)
    'site:linkedin.com/company "AI automation" agency "11-50 employees"',
    'site:linkedin.com/company "workflow automation" boutique agency remote',
    # IndieHackers
    'site:indiehackers.com "automation agency" OR "AI agency"',
]

# Twitter discovery queries (passed to search_twitter tool)
TWITTER_SEED_QUERIES = [
    "n8n automation agency",
    "AI automation agency remote",
    "workflow automation consultancy",
]

# Target: 10-20 qualified new companies per day
MAX_COMPANIES_PER_RUN = 20
MAX_RESULTS_PER_QUERY = 5  # search results to follow up per query
SCRAPE_TIMEOUT_SECONDS = 10

SCORING_RUBRIC = """
Score each company 0-100 based on these criteria:

- Region match (US/UK/EU/Canada/Australia/NZ/Eastern Europe/Israel/Singapore confirmed): +25 points
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
    "Source",
]
