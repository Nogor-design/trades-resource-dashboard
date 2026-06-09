"""
actions_engine.py
Generates prioritized recruiter action queue from match results.
Adapted from tradesresource/src/actions.py.
"""
from datetime import date, timedelta
import pandas as pd

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def generate_actions(match_results: pd.DataFrame, max_workers: int = 8) -> pd.DataFrame:
    actions = []
    actionable = match_results[
        (match_results["match_tier"] != "Not Recommended") |
        (match_results["total_score"] >= 50)
    ].head(max_workers)

    for _, row in actionable.iterrows():
        flags = str(row.get("risk_flags", ""))
        tier  = row.get("match_tier", "")

        if tier in ["Strong Fit", "Good Fit"]:
            actions.append(_action(row, "High", "Call worker today",
                                   "Top match for active job order"))
            actions.append(_action(row, "High", "Confirm interest and start date",
                                   "Recruiter must verify interest before submittal"))
        if "Second-shift" in flags or "availability needs confirmation" in flags:
            actions.append(_action(row, "High", "Confirm shift availability",
                                   "Shift preference does not fully match request"))
        if "experience not confirmed" in flags:
            actions.append(_action(row, "Medium", "Verify equipment or control experience",
                                   "Preferred machine or control experience needs confirmation"))
        if "Availability" in flags:
            actions.append(_action(row, "Medium", "Confirm earliest possible start date",
                                   "Start window is within required window"))
        if "Missing required" in flags or "not confirmed" in flags:
            actions.append(_action(row, "Low", "Do not submit until must-have is verified",
                                   "Must-have requirement needs recruiter verification"))
        missing = str(row.get("missing_information", "")).strip()
        if missing:
            actions.append(_action(row, "Medium", "Resolve missing worker profile fields",
                                   missing))

    if not actions:
        return pd.DataFrame(columns=[
            "action_id", "priority", "worker_id", "worker_name",
            "match_score", "action", "reason", "due_date", "status",
        ])

    frame = pd.DataFrame(actions).drop_duplicates(subset=["worker_id", "action"], keep="first")
    frame["_ord"] = frame["priority"].map(PRIORITY_ORDER)
    frame = (frame.sort_values(["_ord", "match_score", "due_date"],
                               ascending=[True, False, True])
             .drop(columns=["_ord"])
             .reset_index(drop=True))
    frame.insert(0, "action_id",
                 [f"ACT-{i+1:03d}" for i in range(len(frame))])
    return frame


def _action(row: pd.Series, priority: str, action: str, reason: str) -> dict:
    due_days = {"High": 0, "Medium": 2, "Low": 5}[priority]
    return {
        "priority":    priority,
        "worker_id":   row.get("worker_id", ""),
        "worker_name": row.get("name", row.get("worker_name", "")),
        "match_score": row.get("total_score", 0),
        "action":      action,
        "reason":      reason,
        "due_date":    date.today() + timedelta(days=due_days),
        "status":      "Not Started",
    }
