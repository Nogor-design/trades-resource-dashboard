"""readiness.py — copied from tradesresource."""
import pandas as pd


def calculate_candidate_readiness(match_result: pd.Series) -> str:
    flags   = str(match_result.get("risk_flags", "") or "")
    missing = str(match_result.get("missing_information", "") or "")
    tier    = match_result.get("match_tier", "")

    if tier == "Not Recommended":
        return "Not Recommended for This Role"
    if "Travel required" in flags or "Missing required" in flags:
        return "Blocked by Missing Info"
    if "travel readiness blocker" in missing.lower():
        return "Blocked by Missing Info"
    if missing.strip():
        return "Needs Verification"
    if flags.strip():
        return "Needs Verification"
    if tier == "Strong Fit":
        return "Ready for Recruiter Review"
    if tier == "Good Fit":
        return "Ready to Contact"
    return "Needs Verification"


def add_readiness_status(match_results: pd.DataFrame) -> pd.DataFrame:
    updated = match_results.copy()
    updated["readiness_status"] = updated.apply(calculate_candidate_readiness, axis=1)
    return updated
