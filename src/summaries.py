"""summaries.py — client submittal draft generator with Ollama support."""
import pandas as pd
from src.ollama_client import DEFAULT_OLLAMA_MODEL, generate_with_ollama


def generate_client_summary(
    worker: pd.Series,
    match_result: pd.Series,
    requirements: dict,
    use_ai: bool = False,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> str:
    fallback = _deterministic_summary(worker, match_result, requirements, use_ai)
    if not use_ai:
        return fallback

    prompt = (
        "Draft a client-ready candidate submittal summary for a skilled-trades staffing recruiter. "
        "Use only the provided mock worker profile, match result, and job requirements. "
        "Do not invent credentials, dates, employers, or protected-class information. "
        "Do not imply the candidate is approved or selected. Include a short verification checklist. "
        "Keep it professional and under 180 words.\n\n"
        f"Job requirements: {requirements}\n\n"
        f"Worker profile: {worker.to_dict()}\n\n"
        f"Match result: {match_result.to_dict()}"
    )
    response, error = generate_with_ollama(prompt, model=model)
    if response:
        return (
            f"[Local LLM draft — {model}]\n\n"
            f"{response}\n\n"
            "DRAFT ONLY. Recruiter review and approval required before client submittal."
        )
    return f"{fallback}\n\n[Local LLM fallback note: {error}]"


def generate_recruiter_digest(
    match_results: pd.DataFrame,
    requirements: dict,
    use_ai: bool = False,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> str:
    fallback = _deterministic_digest(match_results, use_ai)
    if not use_ai:
        return fallback

    top_rows = match_results[[
        "name", "total_score", "match_tier",
        "reason_for_score", "risk_flags", "recommended_action",
    ]].head(5).to_dict(orient="records")
    prompt = (
        "Write a concise recruiter digest for a skilled-trades staffing matching dashboard. "
        "Use only these match results. Emphasize recruiter review, verification needs, and next actions. "
        "Do not say the AI selected or approved anyone. Keep it under 120 words.\n\n"
        f"Job: {requirements.get('role')} in {requirements.get('location_state')}\n\n"
        f"Top match results: {top_rows}"
    )
    response, error = generate_with_ollama(prompt, model=model)
    if response:
        return f"[Local LLM recruiter digest — {model}]\n\n{response}"
    return f"{fallback}\n\n[Local LLM fallback note: {error}]"


def generate_requirement_brief(
    requirements: dict,
    use_ai: bool = False,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> str:
    fallback = _deterministic_brief(requirements, use_ai)
    if not use_ai:
        return fallback

    prompt = (
        "Write a concise recruiter-facing job requirement brief for a skilled-trades staffing demo. "
        "Use only the facts provided. Do not invent candidate data. "
        "Keep it under 90 words.\n\n"
        f"Requirements: {requirements}"
    )
    response, error = generate_with_ollama(prompt, model=model)
    if response:
        return f"[Local LLM brief — {model}]: {response}"
    return f"{fallback}\n\n[Local LLM fallback note: {error}]"


def _deterministic_summary(worker, match_result, requirements, use_ai=False) -> str:
    flags        = str(match_result.get("risk_flags", "")).strip()
    verification = flags if flags else "Confirm final availability, interest, and travel logistics."
    prefix       = "AI-assisted draft" if use_ai else "Rule-based draft"
    name         = worker.get("worker_name", worker.get("name", "Worker"))
    return (
        f"{prefix}\n\n"
        f"{name} is a {match_result.get('match_tier','').lower()} for the "
        f"{requirements.get('location_state')} {requirements.get('industry')} "
        f"{requirements.get('role')} role with a rule-based match score of "
        f"{match_result.get('total_score')}.\n\n"
        f"Relevant strengths: {match_result.get('reason_for_score','')}\n\n"
        f"Recruiter verification before submittal: {verification}\n\n"
        "DRAFT ONLY. Recruiter review and approval required before client submittal."
    )


def _deterministic_digest(match_results: pd.DataFrame, use_ai=False) -> str:
    if match_results.empty:
        return "No matches to summarize."
    prefix  = "AI-assisted recruiter digest" if use_ai else "Rule-based recruiter digest"
    strong  = match_results[match_results["match_tier"] == "Strong Fit"]
    top     = match_results.iloc[0]
    blocked = (match_results["risk_flags"].fillna("").astype(str)
               .str.contains("Travel required|Missing required", regex=True).sum())
    return (
        f"{prefix}: {len(strong)} strong fit(s) surfaced for this role. "
        f"Top match is {top['name']} at {top['total_score']} — "
        f"rationale: {top['reason_for_score']}. "
        f"{blocked} worker(s) have a must-review blocker before any client submittal."
    )


def _deterministic_brief(requirements: dict, use_ai=False) -> str:
    prefix = "AI-assisted brief" if use_ai else "Rule-based brief"
    brands = ", ".join(requirements.get("preferred_machine_brands", [])) or "not specified"
    return (
        f"{prefix}: {requirements.get('urgency','Normal')} need for "
        f"{requirements.get('quantity',1)} {requirements.get('role')} in "
        f"{requirements.get('location_state')}. "
        f"Requires {requirements.get('machine_type','')}, {requirements.get('shift','any')} shift, "
        f"travel readiness, {requirements.get('start_window_days',14)}-day start window. "
        f"Preferred machines: {brands}."
    )
