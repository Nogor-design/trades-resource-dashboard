"""candidate_state.py — session-state overrides and notes. Copied from tradesresource."""
from datetime import datetime
import pandas as pd

EDITABLE_FIELDS = [
    "availability_date", "willing_to_travel", "shift_preference",
    "preferred_region", "redeployment_status", "missing_information_flags",
    "recruiter_notes",
]

NOTE_TYPES = [
    "Call Note", "Availability Update", "Skill Verification",
    "Travel / Logistics", "Redeployment Interest", "Client Feedback", "Profile Cleanup",
]


def apply_worker_overrides(workers: pd.DataFrame, overrides: dict) -> pd.DataFrame:
    updated = workers.copy()
    if not overrides:
        return updated
    for worker_id, fields in overrides.items():
        mask = updated["worker_id"] == worker_id
        if not mask.any():
            continue
        for field, value in fields.items():
            if field in updated.columns:
                if field in ["availability_date", "last_assignment_end_date"]:
                    value = pd.to_datetime(value)
                updated.loc[mask, field] = value
    return updated


def update_worker_override(overrides: dict, worker_id: str, field_values: dict) -> dict:
    nxt = dict(overrides)
    existing = dict(nxt.get(worker_id, {}))
    for field, value in field_values.items():
        if field in EDITABLE_FIELDS:
            existing[field] = value
    nxt[worker_id] = existing
    return nxt


def add_worker_note(notes: list, worker_id: str, job_order_id: str,
                    note_type: str, note_text: str, recruiter: str) -> list:
    if not str(note_text).strip():
        return notes
    nxt = list(notes)
    nxt.append({
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "worker_id":    worker_id,
        "job_order_id": job_order_id,
        "recruiter":    recruiter,
        "note_type":    note_type,
        "note_text":    str(note_text).strip(),
    })
    return nxt


def get_worker_notes(worker_id: str, notes: list) -> list:
    filtered = [n for n in notes if n["worker_id"] == worker_id]
    return sorted(filtered, key=lambda n: n["timestamp"], reverse=True)


# ---------------------------------------------------------------------------
# Position overrides (for unblocking / stage updates)
# ---------------------------------------------------------------------------

EDITABLE_POSITION_FIELDS = [
    "intake_complete", "stage", "priority", "notes"
]

def apply_position_overrides(positions: pd.DataFrame, overrides: dict) -> pd.DataFrame:
    updated = positions.copy()
    if not overrides:
        return updated
    for position_id, fields in overrides.items():
        mask = updated["position_id"] == position_id
        if not mask.any():
            continue
        for field, value in fields.items():
            if field in updated.columns:
                updated.loc[mask, field] = value
    return updated


def update_position_override(overrides: dict, position_id: str, field_values: dict) -> dict:
    nxt = dict(overrides)
    existing = dict(nxt.get(position_id, {}))
    for field, value in field_values.items():
        if field in EDITABLE_POSITION_FIELDS:
            existing[field] = value
    nxt[position_id] = existing
    return nxt

