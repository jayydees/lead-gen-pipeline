import re

REQUIRED_FIELDS = ["Company Name", "Website", "Score"]
_URL_RE = re.compile(r"^https?://\S+", re.IGNORECASE)


def validate_company(c: dict) -> tuple[bool, str]:
    """Hard deterministic validation. Returns (is_valid, reason)."""
    for field in REQUIRED_FIELDS:
        if not str(c.get(field, "")).strip():
            return False, f"Missing required field: {field}"

    website = c.get("Website", "")
    if not _URL_RE.match(website):
        return False, f"Invalid URL: {website!r}"

    try:
        score = float(c.get("Score", 0))
    except (ValueError, TypeError):
        return False, f"Non-numeric score: {c.get('Score')!r}"

    if not (0 <= score <= 100):
        return False, f"Score out of range: {score}"

    if score < 40:
        return False, f"Score below minimum threshold (40): {score}"

    name = str(c.get("Company Name", "")).strip()
    if len(name) < 2 or len(name) > 120:
        return False, f"Company name length suspicious: {name!r}"

    return True, ""


def validate_batch(companies: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split companies into (valid, invalid). Invalid entries get a rejection_reason field."""
    valid, invalid = [], []
    for c in companies:
        ok, reason = validate_company(c)
        if ok:
            valid.append(c)
        else:
            invalid.append({**c, "rejection_reason": reason})

    # Sanity check: if >70% score 95+, flag the whole batch as suspicious
    if valid:
        high_score_pct = sum(1 for c in valid if float(c.get("Score", 0)) >= 95) / len(valid)
        if high_score_pct > 0.7:
            for c in valid:
                c["score_inflation_warning"] = f"{int(high_score_pct*100)}% of batch scored 95+"

    return valid, invalid
