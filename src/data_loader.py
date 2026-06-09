"""
data_loader.py
Load and parse all CSV data files.
Auto-generates demo data if CSVs are missing.
"""

import pandas as pd
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

DATA_DIR = os.path.join(_ROOT, "data")

DATE_COLS = {
    "assignments":        ["start_date", "end_date", "last_worker_contact", "last_client_contact",
                           "current_projected_end_date", "renewal_due_date", "time_off_start",
                           "time_off_end", "last_check_in_date", "next_check_in_due"],
    "workers":            ["availability_date", "last_contact", "last_update_timestamp"],
    "open_positions":     ["date_opened", "target_start_date", "last_order_update"],
    "recruiter_activity": ["date", "due_date"],
    "clients":            ["last_contact"],
    "job_orders":         ["created_date"],
}

BOOL_COLS = {
    "workers":    ["willing_to_travel", "cnc_mill_experience",
                   "five_axis_experience", "setup_ability",
                   "candidate_fields_complete", "spreadsheet_updated"],
    "assignments":["per_diem_approved", "lodging_confirmed"],
    "job_orders": ["travel_required"],
}


def _ensure_data_exists():
    required = [
        "assignments.csv", "workers.csv", "open_positions.csv",
        "recruiter_activity.csv", "clients.csv",
    ]
    missing = [f for f in required if not os.path.exists(os.path.join(DATA_DIR, f))]
    if missing:
        from src.demo_data_generator import generate_all
        generate_all(DATA_DIR)


def _parse_dates(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _parse_bools(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = df[col].map(
                lambda v: True if str(v).strip().lower() in ("true", "1", "yes") else False
            )
    return df


def load_assignments() -> pd.DataFrame:
    _ensure_data_exists()
    df = pd.read_csv(os.path.join(DATA_DIR, "assignments.csv"))
    df = _parse_dates(df, DATE_COLS["assignments"])
    df = _parse_bools(df, BOOL_COLS["assignments"])
    today = pd.Timestamp.now().normalize()
    df["days_remaining"] = (df["end_date"] - today).dt.days
    return df


def load_workers() -> pd.DataFrame:
    _ensure_data_exists()
    df = pd.read_csv(os.path.join(DATA_DIR, "workers.csv"))
    df = _parse_dates(df, DATE_COLS["workers"])
    df = _parse_bools(df, BOOL_COLS["workers"])
    return df


def load_open_positions() -> pd.DataFrame:
    _ensure_data_exists()
    df = pd.read_csv(os.path.join(DATA_DIR, "open_positions.csv"))
    df = _parse_dates(df, DATE_COLS["open_positions"])
    today = pd.Timestamp.now().normalize()
    df["days_open"]     = (today - df["date_opened"]).dt.days
    df["days_to_start"] = (df["target_start_date"] - today).dt.days
    return df


def load_recruiter_activity() -> pd.DataFrame:
    _ensure_data_exists()
    df = pd.read_csv(os.path.join(DATA_DIR, "recruiter_activity.csv"))
    df = _parse_dates(df, DATE_COLS["recruiter_activity"])
    return df


def load_clients() -> pd.DataFrame:
    _ensure_data_exists()
    df = pd.read_csv(os.path.join(DATA_DIR, "clients.csv"))
    df = _parse_dates(df, DATE_COLS["clients"])
    return df


def load_job_orders() -> pd.DataFrame:
    """Load job_orders.csv (from tradesresource mock data)."""
    path = os.path.join(DATA_DIR, "job_orders.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    df = _parse_dates(df, DATE_COLS["job_orders"])
    df = _parse_bools(df, BOOL_COLS["job_orders"])
    return df


def load_all():
    """Return all dataframes as a dict."""
    return {
        "assignments":        load_assignments(),
        "workers":            load_workers(),
        "open_positions":     load_open_positions(),
        "recruiter_activity": load_recruiter_activity(),
        "clients":            load_clients(),
        "job_orders":         load_job_orders(),
    }
