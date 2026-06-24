"""LLM critic pass — separate Gemini call that reviews companies before they hit the sheet."""
import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

MODEL = "gemini-3.1-flash-lite"

_SYSTEM = """You are a strict quality evaluator for a B2B lead generation pipeline targeting freelance outreach.

Reject a company if ANY of these are true:
- It is a large enterprise (500+ employees, Fortune 500 language, "global offices in 40 countries")
- It is a solo freelancer / individual consultant (not an agency)
- It is a software product company (SaaS), not a services/agency
- It does NOT work in AI, automation, or product engineering
- The score looks inflated (score ≥ 90 but evidence is thin or generic)
- The company name or website looks hallucinated or placeholder-like
- Region is clearly outside US/UK/EU/Canada/Australia/NZ/Eastern Europe/Israel/Singapore and not remote-first

For each company return exactly this JSON shape (array, one object per company):
[
  {
    "company_name": "<exact name as given>",
    "pass": true or false,
    "confidence": "high" | "medium" | "low",
    "issue": "<empty string if pass=true, otherwise short reason>"
  }
]

Be strict. A score of 95-100 requires clear, specific evidence in the Why field."""


def eval_companies(companies: list[dict]) -> list[dict]:
    """
    Run LLM eval on a batch of companies.
    Returns companies with added fields: eval_pass, eval_confidence, eval_issue.
    Falls through (pass=True, confidence=low) if the eval call itself fails.
    """
    if not companies:
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)

    payload = json.dumps([
        {
            "Company Name": c.get("Company Name"),
            "Website": c.get("Website"),
            "Location": c.get("Location"),
            "Size Signal": c.get("Size Signal"),
            "AI/Automation Stack": c.get("AI/Automation Stack"),
            "Score": c.get("Score"),
            "Why": c.get("Why"),
            "Source": c.get("Source"),
        }
        for c in companies
    ], indent=2)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=f"Evaluate these companies:\n\n{payload}")]
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                response_mime_type="application/json",
            ),
        )
        evaluations = json.loads(response.text)
        if not isinstance(evaluations, list):
            raise ValueError("Eval response was not a list")
        eval_map = {e["company_name"].strip().lower(): e for e in evaluations}
    except Exception as exc:
        print(f"[eval] Eval call failed ({exc}), passing all companies through with low confidence")
        return [
            {**c, "eval_pass": True, "eval_confidence": "low", "eval_issue": f"eval unavailable: {exc}"}
            for c in companies
        ]

    result = []
    for c in companies:
        key = str(c.get("Company Name", "")).strip().lower()
        ev = eval_map.get(key)
        if ev is None:
            # Not evaluated — pass through with warning
            result.append({**c, "eval_pass": True, "eval_confidence": "low", "eval_issue": "not in eval response"})
        else:
            result.append({
                **c,
                "eval_pass": bool(ev.get("pass", True)),
                "eval_confidence": ev.get("confidence", "low"),
                "eval_issue": ev.get("issue", ""),
            })
    return result
