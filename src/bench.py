"""
bench.py
Bench depth signals — adapted from tradesresource for the unified worker table.
Operates on workers who are Available or Ending Soon (not actively on assignment).
"""
import pandas as pd


def build_bench_insights(workers: pd.DataFrame, match_results: pd.DataFrame) -> dict:
    """
    workers: the full unified workers DataFrame (all statuses)
    match_results: scored results from matching_engine.score_all_workers()
    """
    avail = workers[workers["status"].isin(["Available", "Ending Soon", "On Bench"])] \
        if "status" in workers.columns else workers

    travel_ready = int(avail["willing_to_travel"].fillna(False).astype(bool).sum()) \
        if "willing_to_travel" in avail.columns else 0
    five_axis    = int(avail["five_axis_experience"].fillna(False).astype(bool).sum()) \
        if "five_axis_experience" in avail.columns else 0
    aerospace    = int(avail["industry_experience"].fillna("").str.contains("Aerospace", case=False).sum()) \
        if "industry_experience" in avail.columns else 0
    missing_data = int(avail["missing_information_flags"].fillna("").astype(str).str.len().gt(0).sum()) \
        if "missing_information_flags" in avail.columns else 0
    strong_good  = int(match_results["match_tier"].isin(["Strong Fit", "Good Fit"]).sum()) \
        if not match_results.empty else 0
    total_avail  = len(avail)

    role_depth = pd.DataFrame([
        {"Bench Signal":    "Workers available / ending soon",  "Count": total_avail},
        {"Bench Signal":    "Travel-ready",                     "Count": travel_ready},
        {"Bench Signal":    "5-axis CNC experience",            "Count": five_axis},
        {"Bench Signal":    "Aerospace-experienced",            "Count": aerospace},
        {"Bench Signal":    "Strong / Good fit for active role","Count": strong_good},
        {"Bench Signal":    "Profiles needing cleanup",         "Count": missing_data},
    ])

    recommendations = []
    if five_axis < 4:
        recommendations.append("Build a deeper 5-axis bench — aerospace demand is high.")
    if missing_data:
        recommendations.append(f"Clean {missing_data} worker profiles to improve match confidence.")
    if travel_ready >= 6:
        recommendations.append("Travel-ready bench is a strong differentiator for rapid deployment.")
    if strong_good >= 3:
        recommendations.append("Current bench can produce a shortlist quickly for the active role.")
    if total_avail < 5:
        recommendations.append("Bench is thin — prioritize redeployment outreach for ending assignments.")

    return {"role_depth": role_depth, "recommendations": recommendations}
