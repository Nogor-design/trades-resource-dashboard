"""
matching_engine.py
Weighted candidate-to-job-order scoring engine.
Adapted from tradesresource/src/matching.py for the unified worker model.

Score weights (must sum to 1.0):
  required_skill  30%
  machine_control 20%
  industry        15%
  travel          15%
  availability    10%
  rating          10%
"""

from datetime import date

import pandas as pd

MATCH_WEIGHTS = {
    "required_skill": 0.30,
    "machine_control": 0.20,
    "industry":        0.15,
    "travel":          0.15,
    "availability":    0.10,
    "rating":          0.10,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _contains(value, term: str) -> bool:
    if pd.isna(value):
        return False
    return term.lower() in str(value).lower()


def _any_contains(value, terms) -> bool:
    return any(_contains(value, t) for t in terms)


def _days_until(value) -> int | None:
    if pd.isna(value):
        return None
    return (pd.to_datetime(value).date() - date.today()).days


def _split_terms(value) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [t.strip() for t in str(value).replace(",", ";").split(";") if t.strip()]


# ---------------------------------------------------------------------------
# Per-role skill scoring
# ---------------------------------------------------------------------------

def _required_skill_score(candidate: pd.Series, role: str) -> int:
    role_l = role.lower()
    if "cnc" in role_l and "setup" in role_l:
        if (bool(candidate.get("cnc_mill_experience")) and
                bool(candidate.get("setup_ability")) and
                bool(candidate.get("five_axis_experience"))):
            return 100
        if bool(candidate.get("cnc_mill_experience")) and bool(candidate.get("setup_ability")):
            return 70
        if bool(candidate.get("cnc_mill_experience")):
            return 40
        return 0
    if "welder" in role_l or "welding" in role_l:
        certs = str(candidate.get("certifications", ""))
        brands = str(candidate.get("machine_brands", ""))
        if _any_contains(brands, ["Lincoln", "Miller"]) and _contains(certs, "AWS"):
            return 100
        if _contains(certs, "AWS") or _any_contains(
                candidate.get("materials_experience", ""), ["Carbon Steel", "Stainless Steel"]):
            return 75
        return 20 if _any_contains(candidate.get("industry_experience", ""),
                                    ["Industrial", "Shipbuilding"]) else 0
    if "quality" in role_l or "inspector" in role_l:
        if (_any_contains(candidate.get("machine_brands", ""), ["CMM", "Keyence"]) and
                _contains(candidate.get("certifications", ""), "GD&T")):
            return 100
        if (_any_contains(candidate.get("controls", ""), ["PC-DMIS"]) or
                _contains(candidate.get("certifications", ""), "GD&T")):
            return 75
        return 20 if _contains(candidate.get("industry_experience", ""), "Aerospace") else 0
    if "maintenance" in role_l:
        if (_any_contains(candidate.get("machine_brands", ""), ["Allen-Bradley", "Siemens"]) and
                _contains(candidate.get("controls", ""), "PLC")):
            return 100
        if _contains(candidate.get("controls", ""), "PLC"):
            return 75
        return 20 if _contains(candidate.get("industry_experience", ""), "Manufacturing") else 0
    # Generic CNC
    if "cnc" in role_l:
        if bool(candidate.get("cnc_mill_experience")):
            return 70
        return 0
    return 30  # Unknown role — partial credit


def _role_risk_flags(candidate: pd.Series, role: str) -> list[str]:
    role_l = role.lower()
    if "cnc" in role_l and "setup" in role_l:
        if not bool(candidate.get("five_axis_experience")):
            return ["Missing required 5-axis experience"]
    if "welder" in role_l:
        if not _contains(candidate.get("certifications", ""), "AWS"):
            return ["AWS welding certification not confirmed"]
    if "quality" in role_l or "inspector" in role_l:
        if not _any_contains(candidate.get("machine_brands", ""), ["CMM", "Keyence"]):
            return ["CMM inspection experience not confirmed"]
    if "maintenance" in role_l:
        if not _contains(candidate.get("controls", ""), "PLC"):
            return ["PLC troubleshooting experience not confirmed"]
    return []


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

def score_candidate(candidate: pd.Series, requirements: dict) -> dict:
    role = requirements.get("role", "")

    # Required skill
    required_skill = _required_skill_score(candidate, role)

    # Machine / control
    preferred_brands    = requirements.get("preferred_machine_brands", [])
    preferred_controls  = requirements.get("controls_preferred", []) or ["Mazatrol", "OSP"]
    has_brand    = _any_contains(candidate.get("machine_brands", ""), preferred_brands)
    has_controls = _any_contains(candidate.get("controls", ""), preferred_controls)
    if has_brand and has_controls:
        machine_control = 100
    elif has_brand:
        machine_control = 80
    elif bool(candidate.get("five_axis_experience")):
        machine_control = 55
    else:
        machine_control = 20 if bool(candidate.get("cnc_mill_experience")) else 0

    # Industry
    target_industries = _split_terms(requirements.get("industry", ""))
    if target_industries and _any_contains(candidate.get("industry_experience", ""), target_industries):
        industry = 100
    elif _any_contains(candidate.get("industry_experience", ""),
                       ["Defense", "Medical", "Precision", "Industrial", "Packaging"]):
        industry = 70
    elif _contains(candidate.get("industry_experience", ""), "Manufacturing"):
        industry = 40
    else:
        industry = 0

    # Travel
    travel = 100 if bool(candidate.get("willing_to_travel")) else 0

    # Availability
    days_avail = _days_until(candidate.get("availability_date"))
    if days_avail is None:
        availability = 0
    elif days_avail <= requirements.get("start_window_days", 14):
        availability = 100
    elif days_avail <= 21:
        availability = 70
    elif days_avail <= 30:
        availability = 40
    else:
        availability = 0

    # Rating
    rating = min(float(candidate.get("prior_assignment_rating", 0)) / 5 * 100, 100)

    components = dict(required_skill=required_skill, machine_control=machine_control,
                      industry=industry, travel=travel, availability=availability, rating=rating)
    total_score = round(sum(components[k] * MATCH_WEIGHTS[k] for k in components), 1)

    # Flags
    risk_flags   = _role_risk_flags(candidate, role)
    missing_info = []
    reasons      = []

    if requirements.get("travel_required") and not bool(candidate.get("willing_to_travel")):
        risk_flags.append("Travel required but candidate is not travel-ready")
    if availability < 100:
        risk_flags.append("Availability needs recruiter review")
    if (requirements.get("shift") not in (None, "", "Any") and
            candidate.get("shift_preference") not in [requirements.get("shift"), "Any"]):
        risk_flags.append(f"{requirements.get('shift')} availability needs confirmation")
    if preferred_brands and not has_brand:
        risk_flags.append(f"{'/'.join(preferred_brands)} experience not confirmed")
    flags_field = candidate.get("missing_information_flags", "")
    if not pd.isna(flags_field) and str(flags_field).strip():
        missing_info.append(str(flags_field))

    if required_skill >= 100:
        reasons.append(f"Meets core {role} requirements")
    if has_brand:
        reasons.append("Has preferred machine brand exposure")
    if industry >= 100:
        reasons.append("Has target industry experience")
    if travel == 100:
        reasons.append("Travel-ready")

    if total_score >= 85:
        tier = "Strong Fit"
    elif total_score >= 70:
        tier = "Good Fit"
    elif total_score >= 55:
        tier = "Needs Review"
    else:
        tier = "Not Recommended"

    recommended = _recommended_action(tier, risk_flags)

    return {
        "worker_id":              candidate.get("worker_id", candidate.get("candidate_id", "")),
        "name":                   candidate.get("worker_name", candidate.get("name", "")),
        "total_score":            total_score,
        "match_tier":             tier,
        "required_skill_score":   required_skill,
        "machine_control_score":  machine_control,
        "industry_score":         industry,
        "travel_score":           travel,
        "availability_score":     availability,
        "rating_score":           round(rating, 1),
        "reason_for_score":       "; ".join(reasons) if reasons else "Limited match against stated requirements",
        "missing_information":    "; ".join(missing_info),
        "risk_flags":             "; ".join(risk_flags),
        "recommended_action":     recommended,
    }


def _recommended_action(tier: str, risk_flags: list[str]) -> str:
    if tier == "Strong Fit" and not risk_flags:
        return "Call today — prepare recruiter-reviewed submittal"
    if tier in ["Strong Fit", "Good Fit"]:
        return "Verify flagged items before submittal"
    if tier == "Needs Review":
        return "Review manually for partial fit or future role"
    return "Do not submit for this job — keep for better-fit role"


def score_all_workers(workers: pd.DataFrame, requirements: dict) -> pd.DataFrame:
    """Score all workers in the unified table against a set of job requirements."""
    results = [score_candidate(row, requirements) for _, row in workers.iterrows()]
    return (pd.DataFrame(results)
            .sort_values("total_score", ascending=False)
            .reset_index(drop=True))
