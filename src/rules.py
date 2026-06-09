"""
rules.py
All deterministic business rules, urgency scoring, alert generation,
recommended actions, workload scoring, and simple redeployment matching.
"""

import pandas as pd
from datetime import datetime

TODAY = pd.Timestamp.now().normalize()

# ---------------------------------------------------------------------------
# Assignment urgency
# ---------------------------------------------------------------------------

URGENCY_CRITICAL_COLOR = "#7B0000"   # dark red
URGENCY_RED_COLOR      = "#E53935"
URGENCY_ORANGE_COLOR   = "#FB8C00"
URGENCY_YELLOW_COLOR   = "#FDD835"
URGENCY_GREEN_COLOR    = "#43A047"

CRITICAL_REDEPLOY_EXCLUDED = ["Redeployed", "Not Available"]


def assignment_urgency(row) -> str:
    """Return urgency label for an assignment row."""
    days = row.get("days_remaining", None)
    redeploy = str(row.get("redeployment_status", "")).strip()
    if pd.isna(days):
        return "Unknown"
    if days < 0 and redeploy not in CRITICAL_REDEPLOY_EXCLUDED:
        return "Critical"
    if days <= 7:
        return "Red"
    if days <= 14:
        return "Orange"
    if days <= 30:
        return "Yellow"
    return "Green"


def urgency_color(urgency: str) -> str:
    mapping = {
        "Critical": URGENCY_CRITICAL_COLOR,
        "Red":      URGENCY_RED_COLOR,
        "Orange":   URGENCY_ORANGE_COLOR,
        "Yellow":   URGENCY_YELLOW_COLOR,
        "Green":    URGENCY_GREEN_COLOR,
        "Unknown":  "#9E9E9E",
    }
    return mapping.get(urgency, "#9E9E9E")


def apply_assignment_urgency(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["urgency"] = df.apply(assignment_urgency, axis=1)
    df["urgency_color"] = df["urgency"].map(urgency_color)
    df["urgency_order"] = df["urgency"].map(
        {"Critical": 0, "Red": 1, "Orange": 2, "Yellow": 3, "Green": 4, "Unknown": 5}
    )
    return df


# ---------------------------------------------------------------------------
# Worker / client follow-up rules
# ---------------------------------------------------------------------------

def worker_checkin_needed(row) -> bool:
    """True if last_worker_contact is more than 14 days ago."""
    lc = row.get("last_worker_contact")
    if pd.isna(lc):
        return True
    return (TODAY - pd.Timestamp(lc)).days > 14


def client_followup_needed(row) -> bool:
    """True if assignment ends within 14 days and last_client_contact > 7 days ago."""
    days = row.get("days_remaining", 999)
    lcc = row.get("last_client_contact")
    if pd.isna(days) or days > 14:
        return False
    if pd.isna(lcc):
        return True
    return (TODAY - pd.Timestamp(lcc)).days > 7


def apply_worker_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["checkin_needed"] = df.apply(worker_checkin_needed, axis=1)
    df["client_followup_needed"] = df.apply(client_followup_needed, axis=1)
    return df


# ---------------------------------------------------------------------------
# Recommended assignment action
# ---------------------------------------------------------------------------

def recommended_action(row) -> str:
    urgency = row.get("urgency", "Green")
    checkin = row.get("checkin_needed", False)
    if urgency == "Critical":
        return "Resolve ended assignment / redeployment gap"
    if urgency == "Red":
        return "Urgent: confirm extension or next placement"
    if urgency == "Orange":
        return "Contact worker and client about next step"
    if urgency == "Yellow":
        return "Start redeployment planning"
    if checkin:
        return "Worker check-in needed"
    return "No immediate action"


def apply_recommended_actions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["recommended_action"] = df.apply(recommended_action, axis=1)
    return df


# ---------------------------------------------------------------------------
# Open position stuck rules
# ---------------------------------------------------------------------------

def position_is_stuck(row) -> bool:
    intake_complete = row.get("intake_complete", True)
    days_open = row.get("days_open", 0) or 0
    submitted = row.get("candidates_submitted", 0) or 0
    priority = str(row.get("priority", "")).strip()
    days_to_start = row.get("days_to_start", 99) 
    if pd.isna(days_to_start):
        days_to_start = 99
    stage = str(row.get("stage", "")).strip()
    filled_stages = ["Filled", "Offer / Confirmation"]

    if not intake_complete:
        return True
    if days_open > 7 and submitted == 0:
        return True
    if priority == "High" and submitted == 0:
        return True
    if days_to_start <= 7 and stage not in filled_stages:
        return True
    return False


def position_stuck_reason(row) -> str:
    reasons = []
    if not row.get("intake_complete", True):
        reasons.append("Intake incomplete")
    days_open = row.get("days_open", 0) or 0
    submitted = row.get("candidates_submitted", 0) or 0
    priority = str(row.get("priority", "")).strip()
    days_to_start = row.get("days_to_start", 99)
    if pd.isna(days_to_start):
        days_to_start = 99
    stage = str(row.get("stage", "")).strip()
    filled_stages = ["Filled", "Offer / Confirmation"]
    if days_open > 7 and submitted == 0:
        reasons.append(f"Open {days_open}d, no submissions")
    if priority == "High" and submitted == 0:
        reasons.append("High priority, no submissions")
    if days_to_start <= 7 and stage not in filled_stages:
        reasons.append(f"Start in {max(0,int(days_to_start))}d, not filled")
    return "; ".join(reasons) if reasons else ""


def apply_position_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_stuck"] = df.apply(position_is_stuck, axis=1)
    df["stuck_reason"] = df.apply(position_stuck_reason, axis=1)
    return df


# ---------------------------------------------------------------------------
# Recruiter activity overdue
# ---------------------------------------------------------------------------

def activity_is_overdue(row) -> bool:
    due = row.get("due_date")
    status = str(row.get("status", "")).strip().lower()
    completed_statuses = {"complete", "completed", "cancelled"}
    if status in completed_statuses:
        return False
    if pd.isna(due):
        return False
    return pd.Timestamp(due) < TODAY


def apply_activity_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_overdue"] = df.apply(activity_is_overdue, axis=1)
    return df


# ---------------------------------------------------------------------------
# Recruiter workload scoring
# ---------------------------------------------------------------------------

WORKLOAD_LABELS = {
    (0, 10):  ("Light",     "#43A047"),
    (10, 20): ("Balanced",  "#1E88E5"),
    (20, 32): ("Heavy",     "#FB8C00"),
    (32, 999):("Overloaded","#E53935"),
}


def workload_label(score: float):
    for (lo, hi), (label, color) in WORKLOAD_LABELS.items():
        if lo <= score < hi:
            return label, color
    return "Overloaded", "#E53935"


def compute_recruiter_workload(assignments_df, positions_df, activity_df) -> pd.DataFrame:
    """Return one row per recruiter with workload metrics."""
    recruiters = sorted(set(
        list(assignments_df["recruiter_owner"].dropna().unique()) +
        list(positions_df["recruiter_owner"].dropna().unique())
    ))

    today = TODAY
    rows = []
    for rec in recruiters:
        a_rec = assignments_df[assignments_df["recruiter_owner"] == rec]
        p_rec = positions_df[positions_df["recruiter_owner"] == rec]
        act_rec = activity_df[activity_df["recruiter_name"] == rec]

        active_assignments = len(a_rec[a_rec.get("status", pd.Series()).eq("Active") if "status" in a_rec.columns else a_rec.index])
        open_positions = len(p_rec[~p_rec["stage"].isin(["Filled", "On Hold"])])
        high_priority = len(p_rec[p_rec["priority"] == "High"])
        ending_soon = len(a_rec[a_rec["days_remaining"].between(0, 30)])
        overdue_actions = len(act_rec[act_rec.apply(activity_is_overdue, axis=1)])
        checkin_needed = len(a_rec[a_rec.apply(worker_checkin_needed, axis=1)])

        score = (
            open_positions * 2 +
            high_priority * 3 +
            overdue_actions * 2 +
            ending_soon * 2
        )
        label, color = workload_label(score)

        rows.append({
            "recruiter": rec,
            "open_positions": open_positions,
            "active_assignments": active_assignments,
            "high_priority_positions": high_priority,
            "ending_soon": ending_soon,
            "overdue_actions": overdue_actions,
            "checkin_needed": checkin_needed,
            "workload_score": score,
            "workload_label": label,
            "workload_color": color,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Redeployment recommended actions
# ---------------------------------------------------------------------------

def redeployment_action(row) -> str:
    days = row.get("days_remaining", 999)
    if pd.isna(days):
        days = 999
    status = str(row.get("redeployment_status", "Not Started")).strip()
    possible_match = str(row.get("possible_next_match", "")).strip()

    not_contacted = status == "Not Started"

    if days <= 7:
        return "🔴 Urgent: confirm extension or next placement"
    if days <= 14 and not_contacted:
        return "🟠 Contact worker about next assignment"
    if days <= 30 and status == "Not Started":
        return "🟡 Start redeployment planning"
    if not possible_match or possible_match.lower() in ("", "none", "nan"):
        return "🔍 Begin sourcing matching open roles"
    if possible_match:
        return "✅ Review match and contact worker"
    return "No immediate action"


# ---------------------------------------------------------------------------
# Simple redeployment matching
# ---------------------------------------------------------------------------

def match_workers_to_positions(assignments_df, positions_df) -> pd.DataFrame:
    """
    For each assignment ending in 60 days, find the best matching open position
    based on trade_category match and state compatibility.
    Returns assignments_df with 'possible_next_match' column added.
    """
    df = assignments_df.copy()
    open_pos = positions_df[~positions_df["stage"].isin(["Filled", "On Hold"])].copy()

    def find_match(row):
        trade = row.get("trade_category", "")
        state = row.get("state", "")
        matches = open_pos[open_pos["trade_category"] == trade]
        # Prefer same state
        same_state = matches[matches["state"] == state]
        if not same_state.empty:
            best = same_state.sort_values("priority", key=lambda x: x.map({"High": 0, "Medium": 1, "Low": 2})).iloc[0]
            return f"{best['role']} @ {best['client_name']}"
        if not matches.empty:
            best = matches.sort_values("priority", key=lambda x: x.map({"High": 0, "Medium": 1, "Low": 2})).iloc[0]
            return f"{best['role']} @ {best['client_name']}"
        return ""

    ending_mask = df["days_remaining"].between(-999, 60)
    df["possible_next_match"] = ""
    df.loc[ending_mask, "possible_next_match"] = df[ending_mask].apply(find_match, axis=1)
    df["recommended_redeploy_action"] = df.apply(redeployment_action, axis=1)
    return df


# ---------------------------------------------------------------------------
# Build alerts list
# ---------------------------------------------------------------------------

def build_alerts(assignments_df, positions_df, activity_df, workers_df=None) -> pd.DataFrame:
    alerts = []

    # 1. Assignment Rules
    for _, row in assignments_df.iterrows():
        days = row.get("days_remaining", 999)
        if pd.isna(days):
            days = 999
        worker = row.get("worker_name", "")
        client = row.get("client_name", "")
        role = row.get("role", "")
        recruiter = row.get("recruiter_owner", "")
        
        # Ending warnings
        if days < 0:
            alerts.append({
                "severity": "Critical",
                "category": "Assignment Ending",
                "subject": worker,
                "detail": f"{role} @ {client} ended {abs(int(days))} days ago",
                "action": "Resolve ended assignment / redeployment gap",
                "recruiter": recruiter,
            })
        elif days <= 7:
            alerts.append({
                "severity": "Red",
                "category": "Assignment Ending",
                "subject": worker,
                "detail": f"{role} @ {client} ends in {int(days)} days",
                "action": "Urgent extension/redeployment action",
                "recruiter": recruiter,
            })
        elif days <= 14:
            alerts.append({
                "severity": "Orange",
                "category": "Assignment Ending",
                "subject": worker,
                "detail": f"{role} @ {client} ends in {int(days)} days",
                "action": "Contact client and worker about next step",
                "recruiter": recruiter,
            })
        elif days <= 30:
            alerts.append({
                "severity": "Yellow",
                "category": "Assignment Ending",
                "subject": worker,
                "detail": f"{role} @ {client} ends in {int(days)} days",
                "action": "Start renewal/redeployment review",
                "recruiter": recruiter,
            })

        # Extension status unknown / decision needed
        ext_possible = row.get("extension_possible", "Unknown")
        ext_status = row.get("extension_status", "")
        if days <= 30 and (ext_possible == "Unknown" or ext_status == "Extension pending"):
            alerts.append({
                "severity": "Yellow",
                "category": "Assignment Forecast",
                "subject": worker,
                "detail": f"Extension status is '{ext_status}' or possible: '{ext_possible}'",
                "action": "Extension decision needed",
                "recruiter": recruiter,
            })

        # Upcoming time off
        to_start = row.get("time_off_start", "")
        if pd.notna(to_start) and to_start != "":
            try:
                to_date = pd.to_datetime(to_start)
                to_days = (to_date - TODAY).days
                if 0 <= to_days <= 14:
                    alerts.append({
                        "severity": "Yellow",
                        "category": "Assignment Forecast",
                        "subject": worker,
                        "detail": f"Scheduled time off starting {to_start} ({int(to_days)} days out)",
                        "action": "Time off visibility alert",
                        "recruiter": recruiter,
                    })
            except:
                pass

        # Check-in needed
        if row.get("checkin_needed", False):
            alerts.append({
                "severity": "Yellow",
                "category": "Assignment Forecast",
                "subject": worker,
                "detail": f"Last contact was {row.get('last_worker_contact', 'N/A')}",
                "action": "Check-in needed",
                "recruiter": recruiter,
            })

    # 2. Open Order Rules
    for _, row in positions_df.iterrows():
        stage = row.get("stage", "")
        filled_stages = ["Filled", "Offer / Confirmation"]
        if stage in filled_stages:
            continue
            
        client = row.get("client_name", "")
        role = row.get("role", "")
        recruiter = row.get("recruiter_owner", "")
        days_open = row.get("days_open", 0) or 0
        submitted = row.get("candidates_submitted", 0) or 0
        priority = row.get("priority", "Medium")
        intake_complete = row.get("intake_complete", True)
        approval_status = row.get("approval_status", "")

        # Intake incomplete
        if not intake_complete:
            alerts.append({
                "severity": "Orange",
                "category": "Open Order",
                "subject": f"{role} @ {client}",
                "detail": "Intake form is incomplete",
                "action": "Intake incomplete: missing client information",
                "recruiter": recruiter,
            })

        # No candidates
        if submitted == 0 and days_open > 7:
            alerts.append({
                "severity": "Yellow",
                "category": "Open Order",
                "subject": f"{role} @ {client}",
                "detail": f"Open {int(days_open)} days with no candidate submissions",
                "action": "Open order has no candidates: needs sourcing",
                "recruiter": recruiter,
            })

        # Urgent order has no activity
        if priority == "High" and submitted == 0:
            alerts.append({
                "severity": "Red",
                "category": "Open Order",
                "subject": f"{role} @ {client}",
                "detail": "High priority order has 0 submissions",
                "action": "Urgent order has no activity: escalate sourcing",
                "recruiter": recruiter,
            })

        # Submitted but pending approval
        if approval_status == "Pending Client Review":
            alerts.append({
                "severity": "Yellow",
                "category": "Open Order",
                "subject": f"{role} @ {client}",
                "detail": f"Candidates submitted: {row.get('candidate_submitted_names', '')}",
                "action": "Candidate submitted but not approved: waiting on client approval",
                "recruiter": recruiter,
            })

        # Stuck order
        if days_open > 21:
            alerts.append({
                "severity": "Orange",
                "category": "Open Order",
                "subject": f"{role} @ {client}",
                "detail": f"Order open for {int(days_open)} days",
                "action": "Order open too long: stuck order review",
                "recruiter": recruiter,
            })

    # 3. Recruiter Process Rules (from workers DataFrame)
    if workers_df is not None:
        for _, row in workers_df.iterrows():
            recruiter = row.get("recruiter_owner", "")
            worker = row.get("worker_name", "")
            fields_complete = row.get("candidate_fields_complete", True)
            test_status = row.get("proficiency_test_status", "Complete")
            spreadsheet_updated = row.get("spreadsheet_updated", True)
            process_status = row.get("process_status", "")

            # Missing fields
            if not fields_complete:
                alerts.append({
                    "severity": "Yellow",
                    "category": "Recruiter Process",
                    "subject": worker,
                    "detail": f"Missing required fields: {row.get('missing_fields', '')}",
                    "action": "Candidate spreadsheet fields missing: data completion needed",
                    "recruiter": recruiter,
                })

            # Proficiency test pending
            if test_status in ["Pending CNC Proficiency", "Pending Welder Safety"]:
                alerts.append({
                    "severity": "Orange",
                    "category": "Recruiter Process",
                    "subject": worker,
                    "detail": f"Test status: {test_status}",
                    "action": "Proficiency test not done: testing required",
                    "recruiter": recruiter,
                })

            # No update / compliance
            if not spreadsheet_updated or process_status == "Needs update" or process_status == "Needs countries":
                alerts.append({
                    "severity": "Orange",
                    "category": "Recruiter Process",
                    "subject": worker,
                    "detail": f"Candidate profile not updated in real time",
                    "action": "No update in X days: real-time update compliance needed",
                    "recruiter": recruiter,
                })

    # 4. Overdue recruiter actions (original activity)
    for _, row in activity_df.iterrows():
        if row.get("is_overdue", False):
            alerts.append({
                "severity": "Red",
                "category": "Overdue Action",
                "subject": row.get("recruiter_name", ""),
                "detail": f"{row.get('activity_type','')} — due {str(row.get('due_date',''))[:10]}",
                "action": row.get("next_action", "Follow up"),
                "recruiter": row.get("recruiter_name", ""),
            })

    df = pd.DataFrame(alerts)
    if df.empty:
        return df
    order = {"Critical": 0, "Red": 1, "Orange": 2, "Yellow": 3, "Green": 4}
    df["_order"] = df["severity"].map(order).fillna(5)
    df = df.sort_values("_order").drop(columns=["_order"])
    return df
