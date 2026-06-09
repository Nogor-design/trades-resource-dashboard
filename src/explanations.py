"""explanations.py — copied from tradesresource."""
import pandas as pd


def build_match_explanation(match_result: pd.Series) -> dict:
    risk_flags = _split(match_result.get("risk_flags", ""))
    missing    = _split(match_result.get("missing_information", ""))
    strengths  = _split(match_result.get("reason_for_score", ""))

    if not strengths or strengths == ["Limited match against stated requirements"]:
        strengths = ["Limited confirmed alignment with the stated job requirements"]

    if risk_flags:
        decision = "Hold for recruiter verification before any client submittal."
    elif match_result.get("match_tier") in ["Strong Fit", "Good Fit"]:
        decision = "Good candidate for recruiter outreach and potential client submittal."
    else:
        decision = "Keep in bench view for a better-fit role."

    return {
        "strengths":             strengths,
        "verification_needed":   risk_flags + missing,
        "decision_support_note": decision,
    }


def _split(value) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [t.strip() for t in str(value).split(";") if t.strip()]
