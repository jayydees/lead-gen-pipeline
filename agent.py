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
)
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
    return f"Unknown tool: {name}"


def _build_system_prompt(seen_domains: set) -> str:
    today = date.today().isoformat()
    seen_list = "\n".join(sorted(seen_domains)) if seen_domains else "(none yet)"
    seed_queries = "\n".join(f"- {t}" for t in SEED_SEARCH_TERMS)

    return f"""You are a lead generation agent finding small-to-medium agencies for freelance outreach.

Today's date: {today}

## Goal
Find up to {MAX_COMPANIES_PER_RUN} new agencies matching this profile:
- Based in US, UK, or EU (or explicitly remote-first)
- Specialise in AI, automation, or product engineering
- Small to medium size (under 50 people)
- Likely to hire senior freelancers or contractors

## Scoring Rubric
{SCORING_RUBRIC}
Only include companies with a score of 50 or higher.

## Already Seen Domains — SKIP THESE
{seen_list}

## Seed Search Queries
Start with these, then generate your own variations:
{seed_queries}

## Workflow
1. Run search queries to discover candidates
2. Scrape each promising website to extract signals
3. Score each company using the rubric
4. Once done (or after exhausting reasonable leads), call append_to_sheet with all companies scoring >= 50
5. Call send_notification with a summary email

## append_to_sheet Field Format
- Date Found: {today}
- Company Name, Website (full URL), Location, Size Signal, Remote Signal
- AI/Automation Stack (tools mentioned, e.g. "n8n, Claude, Zapier")
- Founder Name, LinkedIn URL, Contact Email (leave blank if not found)
- Score (integer 0-100), Why (1-2 sentence justification)

## Notification Format
First line: "Subject: Lead Gen — N new agencies [{today}]"
Then list top 5 by score with a one-line summary each.
"""


def run_agent(seen_domains: set | None = None) -> dict:
    """Run the lead generation agent. Returns {"count": int, "notification_sent": bool, "summary": str}."""
    if seen_domains is None:
        seen_domains = get_seen_domains()

    client = genai.Client(api_key=GEMINI_API_KEY)
    system_prompt = _build_system_prompt(seen_domains)

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[_TOOLS],
    )

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    "Run the lead generation pipeline now. Find new agencies, score them, "
                    "append qualifying ones to the sheet, and send the notification email."
                )
            ],
        )
    ]

    companies_appended = 0
    notification_sent = False
    last_text = ""

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
            # No more tool calls — extract final text if present
            for part in candidate.content.parts:
                if part.text:
                    last_text = part.text
            break

        # Execute each function call and collect responses
        response_parts = []
        for part in function_calls:
            fc = part.function_call
            result = _execute_tool(fc.name, dict(fc.args))

            if fc.name == "append_to_sheet":
                companies_appended = len(fc.args.get("companies", []))
            elif fc.name == "send_notification":
                notification_sent = True

            response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                )
            )

        contents.append(types.Content(role="user", parts=response_parts))

    return {
        "count": companies_appended,
        "notification_sent": notification_sent,
        "summary": last_text or f"Agent completed. {companies_appended} companies appended.",
    }
