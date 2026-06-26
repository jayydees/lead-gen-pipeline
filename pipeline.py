import time
from datetime import datetime, timezone

from eval import eval_companies
from tools.monitor import log_run
from tools.notify import send_notification
from tools.sheets import append_companies, get_seen_domains
from tools.validate import validate_batch

last_run: dict = {}


def _pre_discover() -> str:
    """Run Twitter searches before the agent to guarantee channel coverage."""
    from config import TWITTER_SEED_QUERIES
    from tools.apify_twitter import search_twitter

    parts = []
    for query in TWITTER_SEED_QUERIES[:2]:
        try:
            result = search_twitter(query, max_tweets=5)
            preview = (result or "")[:120].replace("\n", " ")
            print(f"[pipeline] Twitter '{query}' → {preview!r}")
            if result and "error" not in result.lower() and result != "No tweets found.":
                parts.append(f"TWITTER — '{query}':\n{result}")
                print(f"[pipeline] Twitter pre-discovery OK: {query}")
            else:
                print(f"[pipeline] Twitter pre-discovery empty: {query}")
        except Exception as e:
            print(f"[pipeline] Twitter pre-discovery failed: {e}")

    return "\n\n---\n\n".join(parts)


def run_pipeline(agent_fn=None, pre_discover_fn=None) -> dict:
    if agent_fn is None:
        from agent import run_agent as agent_fn
    if pre_discover_fn is None:
        pre_discover_fn = _pre_discover
    started_at = datetime.now(timezone.utc)
    t0 = time.monotonic()
    errors = ""

    try:
        # ── 1. Collect seen domains for dedup context ──────────────────────
        seen_domains = get_seen_domains()

        # ── 2. Pre-discover via Twitter + Reddit (guaranteed channel coverage)
        print("[pipeline] Pre-discovering via Twitter + Reddit...")
        seed_context = pre_discover_fn()
        print(f"[pipeline] Seed context: {'collected' if seed_context else 'none (tools may be unavailable)'}")

        # ── 3. Run agent (buffers companies, does NOT write to sheet) ───────
        agent_result = agent_fn(seen_domains=seen_domains, seed_context=seed_context)
        raw = agent_result["submitted_companies"]
        notification_summary = agent_result["notification_summary"]

        # ── 4. Hard validation ──────────────────────────────────────────────
        valid, invalid = validate_batch(raw)
        validation_rejections = [
            f"{c.get('Company Name','?')}: {c.get('rejection_reason','')}"
            for c in invalid
        ]
        score_inflation_warning = ""
        if valid and any(c.get("score_inflation_warning") for c in valid):
            score_inflation_warning = valid[0].get("score_inflation_warning", "")

        print(f"[pipeline] Raw: {len(raw)} | Valid: {len(valid)} | Invalid: {len(invalid)}")
        if invalid:
            print(f"[pipeline] Validation rejections: {validation_rejections}")

        # ── 5. LLM eval pass ────────────────────────────────────────────────
        eval_results = eval_companies(valid)
        passed = [c for c in eval_results if c.get("eval_pass", True)]
        eval_rejected = [c for c in eval_results if not c.get("eval_pass", True)]
        eval_rejection_notes = [
            f"{c.get('Company Name','?')} [{c.get('eval_confidence','?')}]: {c.get('eval_issue','')}"
            for c in eval_rejected
        ]

        print(f"[pipeline] Eval passed: {len(passed)} | Eval rejected: {len(eval_rejected)}")
        if eval_rejected:
            print(f"[pipeline] Eval rejections: {eval_rejection_notes}")

        # ── 6. Write to sheet ───────────────────────────────────────────────
        # Strip internal eval fields before writing
        clean = [
            {k: v for k, v in c.items() if not k.startswith("eval_") and k != "score_inflation_warning"}
            for c in passed
        ]
        write_result = append_companies(clean) if clean else "No companies passed eval."
        written = len(clean)

        print(f"[pipeline] {write_result}")

        # ── 7. Send notification ────────────────────────────────────────────
        notification_sent = False
        if notification_summary:
            eval_footer = ""
            if eval_rejected:
                eval_footer = f"\n\n⚠️ Eval rejected {len(eval_rejected)} companies: " + \
                              "; ".join(c.get('Company Name','?') for c in eval_rejected)
            if validation_rejections:
                eval_footer += f"\n🚫 Validation blocked {len(invalid)}: " + \
                               "; ".join(c.get('Company Name','?') for c in invalid)
            send_result = send_notification(notification_summary + eval_footer)
            notification_sent = "sent" in send_result.lower()
            print(f"[pipeline] {send_result}")

        # ── 8. Log run to Runs Log tab ──────────────────────────────────────
        elapsed = time.monotonic() - t0
        log_run(
            duration_s=elapsed,
            raw_submitted=len(raw),
            passed_validation=len(valid),
            failed_validation=len(invalid),
            passed_eval=len(passed),
            failed_eval=len(eval_rejected),
            written=written,
            score_inflation_warning=score_inflation_warning,
            eval_rejections="; ".join(eval_rejection_notes),
            errors=errors,
        )

        status = {
            "status": "ok",
            "started_at": started_at.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "companies_raw": len(raw),
            "companies_written": written,
            "eval_rejected": len(eval_rejected),
            "validation_rejected": len(invalid),
            "notification_sent": notification_sent,
            "summary": agent_result["agent_summary"] or f"Done. {written} companies written.",
        }

    except Exception as exc:
        elapsed = time.monotonic() - t0
        errors = str(exc)
        print(f"[pipeline] ERROR: {exc}")
        try:
            log_run(
                duration_s=elapsed,
                raw_submitted=0, passed_validation=0, failed_validation=0,
                passed_eval=0, failed_eval=0, written=0,
                errors=errors,
            )
        except Exception:
            pass
        status = {
            "status": "error",
            "started_at": started_at.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "error": errors,
        }

    last_run.update(status)
    return status


if __name__ == "__main__":
    result = run_pipeline()
    print(result)
