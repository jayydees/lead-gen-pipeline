import json
from datetime import date

from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY,
    MAX_COMPANIES_PER_RUN,
    MAX_RESULTS_PER_QUERY,
    SCORING_RUBRIC,
    SEED_SEARCH_TERMS,
    TWITTER_SEED_QUERIES,
)
from tools.apify_linkedin import scrape_linkedin_company as _linkedin
from tools.apify_twitter import search_twitter as _twitter
from tools.notify import send_notification as _send_notification
from tools.scrape import scrape as _scrape
from tools.search import search as _search
from tools.sheets import append_companies, get_seen_domains

MODEL = "gemini-3.1-flash-lite"

_COMPANY_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "Date Found": types.Schema(type=types.Type.STRING),
        "Company Name": types.Schema(type=types.Type.STRING),
        "Website": types.Schema(type=types.Type.STRING),
        "Location": types.Schema(type=types.Type.STRING),
        "Size Signal": types.Schema(type=types.Type.STRING),
        "Remote Signal": types.Schema(type=types.Type.STRING),
        "AI/Automation Stack": types.Schema(type=types.Type.STRING),
        "Founder Name": types.Schema(type=types.Type.STRING),
        "LinkedIn URL": types.Schema(type=types.Type.STRING),
        "Contact Email": types.Schema(type=types.Type.STRING),
        "Score": types.Schema(type=types.Type.NUMBER),
        "Why": types.Schema(type=types.Type.STRING),
        "Source": types.Schema(type=types.Type.STRING),
    },
    required=["Company Name", "Website", "Score"],
)

_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search",
            description=(
                "Search the web for agencies matching the target profile. "
                "Returns a list of results with title, url, and snippet."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="The search query to run",
                    )
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="scrape",
            description=(
                "Fetch and read the text content of a company website to extract "
                "signals: location, team size, tech stack, remote policy, contact info."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(
                        type=types.Type.STRING,
                        description="The URL to scrape",
                    )
                },
                required=["url"],
            ),
        ),
        types.FunctionDeclaration(
            name="append_to_sheet",
            description=(
                "Write the qualified companies to the Google Sheet. "
                "Call this once when you have your final list."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "companies": types.Schema(
                        type=types.Type.ARRAY,
                        description="List of company objects to append",
                        items=_COMPANY_SCHEMA,
                    )
                },
                required=["companies"],
            ),
        ),
        types.FunctionDeclaration(
            name="send_notification",
            description=(
                "Send a Gmail summary notification. Call this after appending to the sheet."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "summary": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Email body. Start the first line with 'Subject: ...' "
                            "to set the subject line."
                        ),
                    )
                },
                required=["summary"],
            ),
        ),
        types.FunctionDeclaration(
            name="scrape_linkedin_company",
            description=(
                "Scrape a LinkedIn company page to get employee count, specialties, "
                "headquarters, and description. Use this to enrich promising leads "
                "when you have their LinkedIn URL."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "linkedin_url": types.Schema(
                        type=types.Type.STRING,
                        description="Full LinkedIn company URL, e.g. https://linkedin.com/company/acme",
                    )
                },
                required=["linkedin_url"],
            ),
        ),
        types.FunctionDeclaration(
            name="search_twitter",
            description=(
                "Search Twitter/X for agencies and leads. Use for TWO purposes: "
                "(1) Discovery — search for 'AI automation agency hiring' or 'n8n agency remote' "
                "to find agencies posting about their work. "
                "(2) Enrichment — verify a known company's activity level. "
                "Run at least 2-3 Twitter searches per pipeline run."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="Search query, e.g. 'AI automation agency remote hiring'",
                    )
                },
                required=["query"],
            ),
        ),
    ]
)


def _execute_tool(name: str, args: dict) -> str:
    if name == "search":
        results = _search(args["query"], max_results=MAX_RESULTS_PER_QUERY)
        return json.dumps(results)
    elif name == "scrape":
        return _scrape(args["url"])
    elif name == "append_to_sheet":
        return append_companies(args["companies"])
    elif name == "send_notification":
        return _send_notification(args["summary"])
    elif name == "scrape_linkedin_company":
        return _linkedin(args["linkedin_url"])
    elif name == "search_twitter":
        return _twitter(args["query"])
    return f"Unknown tool: {name}"


def _build_system_prompt(seen_domains: set) -> str:
    today = date.today().isoformat()
    seen_list = "\n".join(sorted(seen_domains)) if seen_domains else "(none yet)"
    seed_queries = "\n".join(f"- {t}" for t in SEED_SEARCH_TERMS)
    twitter_queries = "\n".join(f"- {t}" for t in TWITTER_SEED_QUERIES)

    return f"""You are a lead generation agent finding small-to-medium agencies for freelance outreach.

Today's date: {today}

## Goal
Find up to {MAX_COMPANIES_PER_RUN} new agencies matching this profile:
- Based in US, UK, EU, Canada, Australia/NZ, Eastern Europe (Poland, Romania, Czech Republic), Israel, or Singapore — OR explicitly remote-first anywhere
- Specialise in AI, automation, or product engineering
- Small to medium size (under 50 people)
- Likely to hire senior freelancers or contractors

## Scoring Rubric
{SCORING_RUBRIC}
Only include companies with a score of 50 or higher.

## Already Seen Domains — SKIP THESE
{seen_list}

## Seed Search Queries (Exa web search)
{seed_queries}

## Twitter Discovery Queries
Run ALL of these via search_twitter — they find agencies posting publicly about their work:
{twitter_queries}

## Workflow — use EVERY channel below, in order
1. **Exa web search** — run ALL seed queries above; scrape every promising agency URL you find
2. **Twitter** — run all 3 Twitter queries via search_twitter; any agency handle or website you find, scrape it
3. **LinkedIn discovery** — the seed queries include site:linkedin.com/company searches; for each LinkedIn URL found, call scrape_linkedin_company to enrich it
4. Score every candidate using the rubric; include all scoring >= 40
5. Call append_to_sheet once with all qualified companies
6. Call send_notification with a summary

Set Source accurately per company: "Exa search", "Twitter", "LinkedIn", "Clutch", "IndieHackers"

Do NOT give up early. Run every channel. Keep going until you have tried all seed queries or found {MAX_COMPANIES_PER_RUN} companies.

## append_to_sheet Field Format
- Date Found: {today} — ALWAYS set this, never leave blank
- Company Name, Website (full URL), Location
- Size Signal: estimate from the scraped page (e.g. "5-15 people", "team of 8", "10-20"). If unclear, write "small agency"
- Remote Signal: "remote-first", "hybrid", "on-site", or "unclear"
- AI/Automation Stack: tools mentioned, e.g. "n8n, Claude, Zapier". If none found write "not specified"
- Founder Name, LinkedIn URL, Contact Email — scrape the About/Team/Contact page; leave blank only if genuinely not found
- Score (integer 0-100), Why (1-2 sentence justification)
- Source: ALWAYS set — the channel where you found this lead. Use one of: "Exa search", "Clutch", "LinkedIn", "Twitter", "IndieHackers", "GitHub", "Reddit". Never leave blank.

## Notification Format
First line: "Subject: Lead Gen — N new agencies [{today}]"
Then list top 5 by score with a one-line summary each.
"""


def run_agent(seen_domains: set | None = None, tools_override: dict | None = None, seed_context: str = "") -> dict:
    """
    Run the lead generation agent.
    tools_override: optional dict to swap tool implementations, e.g.
        {"scrape": jina_scrape, "search_reddit": rdt_fn, "search_twitter": cli_fn}
    Returns {
        "submitted_companies": list[dict],  # raw, unvalidated — pipeline handles eval/write
        "notification_summary": str,        # agent-drafted email body
        "agent_summary": str,               # final agent text
    }
    """
    if seen_domains is None:
        seen_domains = get_seen_domains()
    _overrides = tools_override or {}

    client = genai.Client(api_key=GEMINI_API_KEY)
    system_prompt = _build_system_prompt(seen_domains)

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[_TOOLS],
    )

    initial_text = (
        "Run the lead generation pipeline now. Find new agencies, score them, "
        "submit qualifying ones via append_to_sheet, then call send_notification."
    )
    if seed_context:
        initial_text += (
            "\n\nIMPORTANT: The following leads were already discovered via Twitter and Reddit. "
            "You MUST scrape each URL found in these results, score them, and include all "
            "qualifying ones (score >= 40) in your append_to_sheet call. Set Source to "
            "'Twitter' or 'Reddit' accordingly.\n\n"
            + seed_context
        )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=initial_text)],
        )
    ]

    # Buffer: agent submits companies here; pipeline decides what actually hits the sheet
    submitted_companies: list[dict] = []
    notification_summary = ""
    last_text = ""

    def _execute_tool_buffered(name: str, args: dict) -> str:
        if name == "search":
            results = _search(args["query"], max_results=MAX_RESULTS_PER_QUERY)
            return json.dumps(results)
        elif name == "scrape":
            scrape_fn = _overrides.get("scrape", _scrape)
            return scrape_fn(args["url"])
        elif name == "append_to_sheet":
            batch = args.get("companies", [])
            today = date.today().isoformat()
            for c in batch:
                if not c.get("Date Found"):
                    c["Date Found"] = today
                if not c.get("Source"):
                    c["Source"] = "Exa search"
            submitted_companies.extend(batch)
            return f"Received {len(batch)} companies for validation. Running quality checks before writing."
        elif name == "send_notification":
            nonlocal notification_summary
            notification_summary = args.get("summary", "")
            return "Notification queued — will send after quality checks complete."
        elif name == "scrape_linkedin_company":
            return _linkedin(args["linkedin_url"])
        elif name == "search_twitter":
            twitter_fn = _overrides.get("search_twitter", _twitter)
            return twitter_fn(args["query"])
        return f"Unknown tool: {name}"

    while True:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        contents.append(candidate.content)

        function_calls = [p for p in candidate.content.parts if p.function_call]

        if not function_calls:
            for part in candidate.content.parts:
                if part.text:
                    last_text = part.text
            break

        response_parts = []
        for part in function_calls:
            fc = part.function_call
            result = _execute_tool_buffered(fc.name, dict(fc.args))
            response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                )
            )

        contents.append(types.Content(role="user", parts=response_parts))

    return {
        "submitted_companies": submitted_companies,
        "notification_summary": notification_summary,
        "agent_summary": last_text,
    }
