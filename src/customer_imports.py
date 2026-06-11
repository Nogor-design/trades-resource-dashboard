"""
customer_imports.py
Normalize customer-provided spreadsheets/documents into dashboard-ready tables.

Raw source files are intentionally treated as local/private inputs. The returned
tables are previews/staging data; they should be reviewed before replacing the
demo CSV contracts.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd


_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
DATA_DIR = _ROOT / "data"

ROSTER_FILE = "Roster of techs 6.9.26 + open orders.xlsx"
INTAKE_PDF = "TEMPLATE Machinist (Client Technical Questions + Kick off).pdf"

CANDIDATE_FILES = {
    "main": "Candidate Tracking 2026(Joe Candidate Sheet).csv",
    "available": "Candidate Tracking 2026(Available - pending pre-employ).csv",
    "no": "Candidate Tracking 2026(NO).csv",
    "pending_deployment": "Candidate Tracking 2026(Pending Deployment).csv",
    "cnc_tests": "Candidate Tracking 2026(CNC Test Results).csv",
    "welder_tests": "Candidate Tracking 2026(Welder Test Results).csv",
}

SOURCE_LABELS = {
    "roster": "Roster / open orders workbook",
    "main": "Main candidate tracker",
    "available": "Available / pending pre-employ candidates",
    "cnc_tests": "CNC test results",
    "welder_tests": "Welder test results",
    "intake_pdf": "Client intake PDF",
}

SOURCE_ORDER = ["roster", "main", "available", "cnc_tests", "welder_tests", "intake_pdf"]


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", text)


def _safe_date(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or _clean(value) == "":
        return pd.NaT
    return pd.to_datetime(value, errors="coerce")


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(_clean(part).lower() for part in parts if _clean(part))
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8].upper() if raw else "00000000"
    return f"{prefix}-{digest}"


def _infer_trade(role: Any) -> str:
    text = _clean(role).lower()
    if any(term in text for term in ["welder", "weld", "fabricator"]):
        return "Welding"
    if any(term in text for term in ["cnc", "machinist", "mill", "lathe", "deburr", "polisher", "grinder"]):
        return "CNC"
    if "maintenance" in text:
        return "Maintenance"
    if any(term in text for term in ["gis", "designer", "engineer"]):
        return "Engineering"
    if "operator" in text:
        return "Operator"
    return "Other"


def _read_csv_with_fallback(path: Path, **kwargs) -> tuple[pd.DataFrame, str]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding, dtype=str, keep_default_na=False, **kwargs), encoding
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Unable to read {path.name}: {last_error}")


def _filename_tokens(path: Path) -> set[str]:
    text = re.sub(r"[^a-z0-9]+", " ", path.stem.lower())
    return {token for token in text.split() if token}


def _candidate_source_key(path: Path) -> str | None:
    if path.name.startswith("~$"):
        return None

    suffix = path.suffix.lower()
    tokens = _filename_tokens(path)
    stem = " ".join(sorted(tokens))

    if suffix in {".xlsx", ".xls", ".xlsm"}:
        if {"roster", "techs"} & tokens or ({"open", "orders"} <= tokens):
            return "roster"

    if suffix == ".pdf":
        if {"intake", "template", "technical", "questions", "kick", "machinist"} & tokens:
            return "intake_pdf"

    if suffix != ".csv":
        return None

    if "cnc" in tokens and ({"test", "tests", "results"} & tokens):
        return "cnc_tests"
    if ({"welder", "weld"} & tokens) and ({"test", "tests", "results"} & tokens):
        return "welder_tests"
    if {"available", "pre", "employ"} & tokens:
        return "available"
    if "pending" in tokens and "deployment" in tokens:
        return "pending_deployment"
    if "no" in tokens and "candidate" in tokens:
        return "no"
    if "candidate" in tokens and not any(word in stem for word in ["available", "pending", "cnc", "welder", "test", "results"]):
        return "main"

    return None


def _source_inventory(data_dir: Path) -> tuple[dict[str, Path], pd.DataFrame]:
    recognized: dict[str, Path] = {}
    rows: list[dict[str, str]] = []
    if not data_dir.exists():
        return recognized, pd.DataFrame(columns=["filename", "recognized_as", "status"])

    for path in sorted(item for item in data_dir.iterdir() if item.is_file()):
        key = _candidate_source_key(path)
        if key and key not in recognized:
            recognized[key] = path
            rows.append({
                "filename": path.name,
                "recognized_as": SOURCE_LABELS.get(key, key.replace("_", " ").title()),
                "status": "used",
            })
        elif key:
            rows.append({
                "filename": path.name,
                "recognized_as": SOURCE_LABELS.get(key, key.replace("_", " ").title()),
                "status": "duplicate ignored",
            })
        else:
            rows.append({
                "filename": path.name,
                "recognized_as": "",
                "status": "unrecognized",
            })
    return recognized, pd.DataFrame(rows)


def _source_path(data_dir: Path, source_key: str) -> Path | None:
    recognized, _ = _source_inventory(data_dir)
    return recognized.get(source_key)


def _candidate_key(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(name).lower()).strip()


def _parse_percent(value: Any) -> float | None:
    text = _clean(value)
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1))
    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if match and float(match.group(2)):
        return round(float(match.group(1)) / float(match.group(2)) * 100, 2)
    return None


def _status_is_yes(value: Any) -> bool:
    return _clean(value).lower().startswith("yes")


def _process_status(row: dict[str, Any]) -> str:
    app_done = _status_is_yes(row.get("application_status"))
    testing_done = _status_is_yes(row.get("proficiency_testing"))
    interview_done = _status_is_yes(row.get("interview_completed"))
    references_done = _status_is_yes(row.get("references_completed"))
    profile_done = _status_is_yes(row.get("profile_completed"))

    if all([app_done, testing_done, interview_done, references_done, profile_done]):
        return "Ready"
    if not app_done:
        return "Needs application"
    if not testing_done:
        return "Needs testing"
    if not interview_done:
        return "Needs interview"
    if not references_done:
        return "Needs references"
    return "Needs profile"


def _load_roster(data_dir: Path, diagnostics: list[dict[str, str]]) -> dict[str, pd.DataFrame]:
    path = _source_path(data_dir, "roster")
    if path is None:
        diagnostics.append({"source": ROSTER_FILE, "status": "missing", "detail": "Roster workbook not found."})
        return {
            "customer_assignments": pd.DataFrame(),
            "customer_open_positions": pd.DataFrame(),
            "customer_ended_assignments": pd.DataFrame(),
        }

    try:
        roster = pd.read_excel(path, sheet_name="Current Roster")
        ended = pd.read_excel(path, sheet_name="Assignments ended")
    except Exception as exc:
        diagnostics.append({"source": ROSTER_FILE, "status": "error", "detail": str(exc)})
        return {
            "customer_assignments": pd.DataFrame(),
            "customer_open_positions": pd.DataFrame(),
            "customer_ended_assignments": pd.DataFrame(),
        }

    roster = roster.dropna(how="all")
    tech_name = roster.get("Tech Name", pd.Series(dtype=str)).map(_clean)
    open_mask = tech_name.str.upper().eq("OPEN") | tech_name.str.contains("open", case=False, na=False)
    assignment_rows = []
    open_position_rows = []

    today = pd.Timestamp.now().normalize()
    for idx, row in roster.iterrows():
        worker_name = _clean(row.get("Tech Name"))
        role = _clean(row.get("Position"))
        client = _clean(row.get("Company Name"))
        start_date = _safe_date(row.get("Start Date"))
        commitment = _safe_date(row.get("Iniitial Committment"))
        final_day = _safe_date(row.get("Final Day"))
        end_date = final_day if pd.notna(final_day) else commitment
        notes = _clean(row.get("Notes"))
        extensions = _clean(row.get("Extensions"))

        if bool(open_mask.loc[idx]):
            submitted_name = ""
            stage = "Open"
            pending_match = re.search(r"pending\s*\(open\)\s*-\s*(.+)", worker_name, flags=re.I)
            if pending_match:
                submitted_name = _clean(pending_match.group(1))
                stage = "Candidate Pending"
            open_position_rows.append({
                "position_id": _stable_id("REAL-POS", client, role, idx),
                "client_name": client,
                "role": role or "Open role",
                "trade_category": _infer_trade(role),
                "location": "",
                "state": "",
                "priority": "Medium",
                "recruiter_owner": "Unassigned",
                "date_opened": pd.NaT,
                "target_start_date": pd.NaT,
                "days_open": None,
                "stage": stage,
                "candidates_submitted": 1 if submitted_name else 0,
                "client_response_status": "Unknown",
                "intake_complete": False,
                "pay_range": "",
                "shift": _clean(row.get("Shift")),
                "duration": "",
                "notes": notes,
                "candidate_submitted_names": submitted_name,
                "candidate_submission_dates": "",
                "approval_status": "Pending" if submitted_name else "Needs Candidates",
                "interview_status": "",
                "client_feedback": "",
                "last_order_update": pd.NaT,
                "next_order_action": "Complete intake and source candidates",
                "source_file": ROSTER_FILE,
            })
            continue

        if not worker_name or not client:
            continue

        days_remaining = (end_date - today).days if pd.notna(end_date) else None
        renewal_due = end_date - pd.Timedelta(days=30) if pd.notna(end_date) else pd.NaT
        assignment_rows.append({
            "assignment_id": _stable_id("REAL-ASG", worker_name, client, start_date),
            "worker_id": _stable_id("REAL-W", worker_name),
            "worker_name": worker_name,
            "client_name": client,
            "role": role,
            "trade_category": _infer_trade(role),
            "location": "",
            "state": "",
            "recruiter_owner": "Unassigned",
            "start_date": start_date,
            "end_date": end_date,
            "days_remaining": days_remaining,
            "status": "Active",
            "last_worker_contact": pd.NaT,
            "last_client_contact": pd.NaT,
            "pay_rate": None,
            "bill_rate": None,
            "margin": None,
            "extension_possible": "Yes" if extensions else "Unknown",
            "redeployment_status": "Not Started",
            "notes": "; ".join(part for part in [notes, f"Extensions: {extensions}" if extensions else ""] if part),
            "original_duration": _clean(row.get("Iniitial Committment")),
            "current_projected_end_date": end_date,
            "extension_status": "Extension noted" if extensions else "Unknown",
            "renewal_due_date": renewal_due,
            "time_off_start": pd.NaT,
            "time_off_end": pd.NaT,
            "forecast_status": "Ending soon" if days_remaining is not None and days_remaining <= 30 else "Active / healthy",
            "last_check_in_date": pd.NaT,
            "next_check_in_due": pd.NaT,
            "next_action": "Confirm extension or redeployment plan" if days_remaining is not None and days_remaining <= 30 else "Monitor",
            "travel_status": "",
            "per_diem_approved": False,
            "lodging_confirmed": False,
            "source_file": ROSTER_FILE,
        })

    ended_rows = []
    ended = ended.dropna(how="all")
    for idx, row in ended.iterrows():
        worker_name = _clean(row.get("Tech Name"))
        client = _clean(row.get("Company Name"))
        if not worker_name or not client:
            continue
        ended_rows.append({
            "ended_assignment_id": _stable_id("REAL-END", worker_name, client, row.get("Start Date"), idx),
            "worker_name": worker_name,
            "client_name": client,
            "role": _clean(row.get("Position")),
            "trade_category": _infer_trade(row.get("Position")),
            "start_date": _safe_date(row.get("Start Date")),
            "end_date": _safe_date(row.get("End Date")),
            "notes": _clean(row.get("Notes")),
            "source_file": ROSTER_FILE,
        })

    diagnostics.append({
        "source": path.name,
        "status": "loaded",
        "detail": f"{len(assignment_rows)} assignments, {len(open_position_rows)} open positions, {len(ended_rows)} ended assignments.",
    })
    return {
        "customer_assignments": pd.DataFrame(assignment_rows),
        "customer_open_positions": pd.DataFrame(open_position_rows),
        "customer_ended_assignments": pd.DataFrame(ended_rows),
    }


def _load_test_scores(data_dir: Path, diagnostics: list[dict[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    cnc_path = _source_path(data_dir, "cnc_tests")
    if cnc_path is not None:
        try:
            cnc, _ = _read_csv_with_fallback(cnc_path)
            for _, row in cnc.iterrows():
                name = _clean(row.get("Name.1")) or _clean(row.get("Name"))
                if not name:
                    continue
                rows.append({
                    "candidate_key": _candidate_key(name),
                    "candidate_name": name,
                    "test_type": "CNC",
                    "raw_score": _clean(row.get("Total Score")) or _clean(row.get("Score.1")) or _clean(row.get("Score")),
                    "score_percent": _parse_percent(row.get("Total Score")) or _parse_percent(row.get("Score.1")) or _parse_percent(row.get("Score")),
                    "source_file": cnc_path.name,
                })
            diagnostics.append({"source": cnc_path.name, "status": "loaded", "detail": f"{len(cnc)} CNC test rows."})
        except Exception as exc:
            diagnostics.append({"source": cnc_path.name, "status": "error", "detail": str(exc)})

    welder_path = _source_path(data_dir, "welder_tests")
    if welder_path is not None:
        try:
            welder, _ = _read_csv_with_fallback(welder_path)
            for _, row in welder.iterrows():
                name = _clean(row.get("Full Name"))
                if not name:
                    continue
                rows.append({
                    "candidate_key": _candidate_key(name),
                    "candidate_name": name,
                    "test_type": "Welder",
                    "raw_score": _clean(row.get("Score")),
                    "score_percent": _parse_percent(row.get("Score")),
                    "source_file": welder_path.name,
                })
            diagnostics.append({"source": welder_path.name, "status": "loaded", "detail": f"{len(welder)} welder test rows."})
        except Exception as exc:
            diagnostics.append({"source": welder_path.name, "status": "error", "detail": str(exc)})

    return pd.DataFrame(rows)


def _load_candidate_process(data_dir: Path, tests: pd.DataFrame, diagnostics: list[dict[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    test_lookup: dict[str, dict[str, Any]] = {}
    if not tests.empty:
        for key, group in tests.groupby("candidate_key"):
            best = group.sort_values("score_percent", ascending=False, na_position="last").iloc[0]
            test_lookup[key] = {
                "best_test_type": best.get("test_type", ""),
                "best_test_score": best.get("raw_score", ""),
                "best_test_percent": best.get("score_percent"),
            }

    main_path = _source_path(data_dir, "main")
    if main_path is not None:
        try:
            raw, enc = _read_csv_with_fallback(main_path, header=None)
            if len(raw) >= 2:
                owners = [_clean(v) for v in raw.iloc[0].tolist()]
                labels = [_clean(v) for v in raw.iloc[1].tolist()]
                body = raw.iloc[2:].reset_index(drop=True)
                body.columns = [label or f"col_{i}" for i, label in enumerate(labels)]
                for _, row in body.iterrows():
                    name = _clean(row.get("Candidate Name"))
                    if not name:
                        continue
                    key = _candidate_key(name)
                    record = {
                        "candidate_id": _stable_id("REAL-CAND", name, row.get("Email"), row.get("Phone")),
                        "candidate_name": name,
                        "phone": _clean(row.get("Phone")),
                        "email": _clean(row.get("Email")),
                        "primary_trade": _clean(row.get("Primary Trade")),
                        "application_status": _clean(row.get("Application (Initial)")),
                        "proficiency_testing": _clean(row.get("Proficiency Testing")),
                        "test_results_or_photos": _clean(row.get("Test results or weld photos(Machining)")),
                        "interview_completed": _clean(row.get("Interview Completed?")),
                        "references_completed": _clean(row.get("References completed? (Requested, Completed)")),
                        "profile_completed": _clean(row.get("Profile Completed")),
                        "notes": _clean(row.get("Notes")),
                        "joe_update": _clean(row.get("Joe Update")),
                        "laura_follow_up": _clean(row.get("Laura Follow up update from Joe notes")),
                        "action_item": _clean(row.get("Action Item")),
                        "recruiter_owner": "Laura/Joe",
                        "source_status": "Candidate Process",
                        "source_file": main_path.name,
                    }
                    record.update(test_lookup.get(key, {
                        "best_test_type": "",
                        "best_test_score": "",
                        "best_test_percent": None,
                    }))
                    record["process_status"] = _process_status(record)
                    rows.append(record)
            diagnostics.append({"source": main_path.name, "status": "loaded", "detail": f"{max(0, len(raw) - 2)} candidate process rows ({enc})."})
        except Exception as exc:
            diagnostics.append({"source": main_path.name, "status": "error", "detail": str(exc)})
    else:
        diagnostics.append({"source": CANDIDATE_FILES["main"], "status": "missing", "detail": "Main candidate tracker export not found."})

    available_path = _source_path(data_dir, "available")
    if available_path is not None:
        try:
            available, _ = _read_csv_with_fallback(available_path)
            existing = {_candidate_key(row["candidate_name"]) for row in rows if row.get("candidate_name")}
            for _, row in available.iterrows():
                name = _clean(row.get("Name"))
                if not name or _candidate_key(name) in existing:
                    continue
                rows.append({
                    "candidate_id": _stable_id("REAL-CAND", name, row.get("Skillset"), row.get("Availability")),
                    "candidate_name": name,
                    "phone": "",
                    "email": "",
                    "primary_trade": _clean(row.get("Skillset")),
                    "application_status": "",
                    "proficiency_testing": "",
                    "test_results_or_photos": "",
                    "interview_completed": "",
                    "references_completed": "",
                    "profile_completed": "",
                    "notes": f"Availability: {_clean(row.get('Availability'))}",
                    "joe_update": "",
                    "laura_follow_up": _clean(row.get("Laura Reach out")),
                    "action_item": f"Submit: {_clean(row.get('Submit'))}" if _clean(row.get("Submit")) else "",
                    "recruiter_owner": "Laura",
                    "source_status": "Available - pending pre-employ",
                    "source_file": available_path.name,
                    "best_test_type": "",
                    "best_test_score": "",
                    "best_test_percent": None,
                    "process_status": "Available",
                })
            diagnostics.append({"source": available_path.name, "status": "loaded", "detail": f"{len(available)} available/pending rows."})
        except Exception as exc:
            diagnostics.append({"source": available_path.name, "status": "error", "detail": str(exc)})

    return pd.DataFrame(rows)


def _load_intake_questions(data_dir: Path, diagnostics: list[dict[str, str]]) -> pd.DataFrame:
    path = _source_path(data_dir, "intake_pdf")
    if path is None:
        diagnostics.append({"source": INTAKE_PDF, "status": "missing", "detail": "Client intake PDF not found."})
        return pd.DataFrame()

    try:
        from pypdf import PdfReader
    except Exception as exc:
        diagnostics.append({"source": INTAKE_PDF, "status": "error", "detail": f"pypdf unavailable: {exc}"})
        return pd.DataFrame()

    section = "Client Intake"
    rows = []
    current = ""
    try:
        reader = PdfReader(str(path))
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            lines = [_clean(line) for line in text.splitlines() if _clean(line)]
            for line in lines:
                lower = line.lower()
                if "client technical questions" in lower:
                    section = "Client Technical Questions"
                    continue
                if "onboarding contractor" in lower:
                    section = "Onboarding and Timecards"
                    continue
                if "safety questions" in lower:
                    section = "Safety Questions"
                    continue
                if line.endswith(":") and len(line) < 80:
                    section = line.rstrip(":")
                    continue

                is_question = line.endswith("?")
                is_field = page_number == 1 and any(token in lower for token in [
                    "client name", "client location", "positions open", "contract term",
                    "potential for extensions", "shift", "poc", "contact information",
                ])
                if is_question or is_field:
                    if current:
                        rows.append({
                            "section": section,
                            "question": current,
                            "page": page_number,
                            "timecard_related": bool(re.search(r"timecard|clock|pay week|break|lunch", current, re.I)),
                            "source_file": path.name,
                        })
                    current = line
                elif current and len(current) < 220 and not re.search(r"brands that make", line, re.I):
                    current = f"{current} {line}"
        if current:
            rows.append({
                "section": section,
                "question": current,
                "page": len(reader.pages),
                "timecard_related": bool(re.search(r"timecard|clock|pay week|break|lunch", current, re.I)),
                "source_file": path.name,
            })
        diagnostics.append({"source": path.name, "status": "loaded", "detail": f"{len(rows)} intake prompts from {len(reader.pages)} pages."})
    except Exception as exc:
        diagnostics.append({"source": INTAKE_PDF, "status": "error", "detail": str(exc)})
        return pd.DataFrame()

    return pd.DataFrame(rows)


def _build_timecard_blueprint(intake_questions: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "workflow_area": "Technician weekly timecard",
            "field": "assignment_id",
            "type": "hidden/link parameter",
            "why_it_matters": "Connects the submission to the active assignment and client.",
        },
        {
            "workflow_area": "Technician weekly timecard",
            "field": "worker name and week ending",
            "type": "prefilled + date",
            "why_it_matters": "Makes each card auditable and easy to group in the dashboard.",
        },
        {
            "workflow_area": "Technician weekly timecard",
            "field": "daily regular/overtime hours",
            "type": "number grid",
            "why_it_matters": "Captures the billable payload that can be exported or emailed.",
        },
        {
            "workflow_area": "Technician weekly timecard",
            "field": "lunch/break confirmation",
            "type": "checkbox/select",
            "why_it_matters": "Matches intake questions about paid lunch and break policies.",
        },
        {
            "workflow_area": "Technician weekly timecard",
            "field": "technician signature",
            "type": "typed signature",
            "why_it_matters": "Creates lightweight attestation for the submitted hours.",
        },
        {
            "workflow_area": "Office dashboard",
            "field": "submitted/pending/late status",
            "type": "derived status",
            "why_it_matters": "Gives the owner a weekly exception list instead of hunting emails.",
        },
        {
            "workflow_area": "Office dashboard",
            "field": "client approver / timecard sender",
            "type": "intake-derived contact",
            "why_it_matters": "The intake form asks who sends timecards; that should drive routing.",
        },
    ]

    if not intake_questions.empty:
        related = intake_questions[intake_questions["timecard_related"] == True]
        for _, row in related.head(8).iterrows():
            rows.append({
                "workflow_area": "Intake-driven setup",
                "field": row.get("question", ""),
                "type": "client setup question",
                "why_it_matters": "Answer once during client intake, then reuse for timecard instructions/routing.",
            })

    return pd.DataFrame(rows)


def _trade_to_primary_trade(value: Any) -> str:
    trade = _clean(value)
    if trade == "CNC":
        return "CNC Machinist"
    if trade == "Welding":
        return "Welder/Fabricator"
    if trade == "Maintenance":
        return "Maintenance Tech"
    return trade or "Skilled Trades"


def _candidate_fields_complete(row: pd.Series) -> bool:
    required = [
        "application_status", "proficiency_testing", "interview_completed",
        "references_completed", "profile_completed",
    ]
    return all(_status_is_yes(row.get(field)) for field in required)


def _customer_candidates_to_workers(candidates: pd.DataFrame, assignments: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    if not candidates.empty:
        for _, row in candidates.iterrows():
            name = _clean(row.get("candidate_name"))
            if not name:
                continue
            primary_trade = _clean(row.get("primary_trade")) or "Skilled Trades"
            trade_category = _infer_trade(primary_trade)
            fields_complete = _candidate_fields_complete(row)
            score = row.get("best_test_percent")
            score_text = _clean(row.get("best_test_score"))
            rows.append({
                "worker_id": _clean(row.get("candidate_id")) or _stable_id("REAL-CAND", name),
                "worker_name": name,
                "primary_trade": primary_trade,
                "trade_category": trade_category,
                "home_state": "",
                "skills": primary_trade,
                "certifications": "",
                "machine_brands": "",
                "controls": "",
                "materials_experience": "",
                "industry_experience": "",
                "cnc_mill_experience": trade_category == "CNC",
                "five_axis_experience": False,
                "setup_ability": False,
                "preferred_locations": "",
                "preferred_region": "",
                "preferred_states": "",
                "willing_to_travel": False,
                "shift_preference": "Any",
                "prior_assignment_rating": 0,
                "availability_date": pd.NaT,
                "current_assignment_id": "",
                "recruiter_owner": _clean(row.get("recruiter_owner")) or "Unassigned",
                "last_contact": pd.NaT,
                "redeployment_status": "Available",
                "missing_information_flags": ", ".join(field for field in [
                    "Application" if not _status_is_yes(row.get("application_status")) else "",
                    "Testing" if not _status_is_yes(row.get("proficiency_testing")) else "",
                    "Interview" if not _status_is_yes(row.get("interview_completed")) else "",
                    "References" if not _status_is_yes(row.get("references_completed")) else "",
                    "Profile" if not _status_is_yes(row.get("profile_completed")) else "",
                ] if field),
                "recruiter_notes": "; ".join(part for part in [
                    _clean(row.get("notes")),
                    _clean(row.get("action_item")),
                    f"Best test: {score_text}" if score_text else "",
                ] if part),
                "status": "Available",
                "notes": _clean(row.get("joe_update")) or _clean(row.get("laura_follow_up")),
                "candidate_fields_complete": fields_complete,
                "missing_fields": ", ".join(field for field in [
                    "Application" if not _status_is_yes(row.get("application_status")) else "",
                    "Proficiency Testing" if not _status_is_yes(row.get("proficiency_testing")) else "",
                    "Interview" if not _status_is_yes(row.get("interview_completed")) else "",
                    "References" if not _status_is_yes(row.get("references_completed")) else "",
                    "Profile" if not _status_is_yes(row.get("profile_completed")) else "",
                ] if field),
                "proficiency_test_status": "Complete" if _status_is_yes(row.get("proficiency_testing")) else "Pending Proficiency",
                "proficiency_test_score": score,
                "spreadsheet_updated": True,
                "last_update_timestamp": pd.NaT,
                "process_status": _clean(row.get("process_status")) or "Needs update",
            })

    existing_names = {_candidate_key(row["worker_name"]) for row in rows if row.get("worker_name")}
    if not assignments.empty:
        for _, row in assignments.iterrows():
            name = _clean(row.get("worker_name"))
            if not name or _candidate_key(name) in existing_names:
                continue
            rows.append({
                "worker_id": _clean(row.get("worker_id")) or _stable_id("REAL-W", name),
                "worker_name": name,
                "primary_trade": _trade_to_primary_trade(row.get("trade_category")),
                "trade_category": _clean(row.get("trade_category")) or _infer_trade(row.get("role")),
                "home_state": _clean(row.get("state")),
                "skills": _clean(row.get("role")),
                "certifications": "",
                "machine_brands": "",
                "controls": "",
                "materials_experience": "",
                "industry_experience": "",
                "cnc_mill_experience": _clean(row.get("trade_category")) == "CNC",
                "five_axis_experience": False,
                "setup_ability": False,
                "preferred_locations": _clean(row.get("location")),
                "preferred_region": "",
                "preferred_states": _clean(row.get("state")),
                "willing_to_travel": False,
                "shift_preference": "Any",
                "prior_assignment_rating": 0,
                "availability_date": row.get("end_date"),
                "current_assignment_id": _clean(row.get("assignment_id")),
                "recruiter_owner": _clean(row.get("recruiter_owner")) or "Unassigned",
                "last_contact": pd.NaT,
                "redeployment_status": _clean(row.get("redeployment_status")) or "Not Started",
                "missing_information_flags": "Candidate profile not imported",
                "recruiter_notes": _clean(row.get("notes")),
                "status": "Active",
                "notes": _clean(row.get("notes")),
                "candidate_fields_complete": False,
                "missing_fields": "Candidate profile",
                "proficiency_test_status": "Unknown",
                "proficiency_test_score": None,
                "spreadsheet_updated": False,
                "last_update_timestamp": pd.NaT,
                "process_status": "Needs update",
            })

    return pd.DataFrame(rows)


def _customer_clients(assignments: pd.DataFrame, positions: pd.DataFrame) -> pd.DataFrame:
    names = sorted(set(
        assignments.get("client_name", pd.Series(dtype=str)).dropna().map(_clean).tolist()
        + positions.get("client_name", pd.Series(dtype=str)).dropna().map(_clean).tolist()
    ))
    rows = []
    for name in [n for n in names if n]:
        rows.append({
            "client_id": _stable_id("REAL-CL", name),
            "client_name": name,
            "industry": "",
            "location": "",
            "state": "",
            "active_assignments": int((assignments.get("client_name", pd.Series(dtype=str)).map(_clean) == name).sum()) if not assignments.empty else 0,
            "open_positions": int((positions.get("client_name", pd.Series(dtype=str)).map(_clean) == name).sum()) if not positions.empty else 0,
            "last_contact": pd.NaT,
            "account_status": "Active",
            "notes": "Imported from customer roster",
        })
    return pd.DataFrame(rows)


def build_customer_dashboard_data(preview: dict[str, Any]) -> dict[str, pd.DataFrame] | None:
    tables = preview.get("tables", {})
    assignments = tables.get("customer_assignments", pd.DataFrame()).copy()
    positions = tables.get("customer_open_positions", pd.DataFrame()).copy()
    candidates = tables.get("customer_candidates", pd.DataFrame()).copy()

    if assignments.empty and positions.empty and candidates.empty:
        return None

    workers = _customer_candidates_to_workers(candidates, assignments)
    clients = _customer_clients(assignments, positions)
    recruiter_activity = pd.DataFrame(columns=[
        "activity_id", "recruiter_name", "date", "activity_type", "related_worker",
        "related_client", "related_position", "status", "next_action", "due_date", "notes",
    ])
    job_orders = positions.rename(columns={
        "position_id": "job_order_id",
        "state": "client_state",
        "location": "client_city",
        "priority": "urgency",
        "notes": "client_notes",
        "date_opened": "created_date",
    }).copy() if not positions.empty else pd.DataFrame()

    if not job_orders.empty:
        job_orders["client_industry"] = ""
        job_orders["quantity"] = 1
        job_orders["contract_length_months"] = ""
        job_orders["machine_type"] = ""
        job_orders["required_skills"] = job_orders.get("role", "")
        job_orders["preferred_skills"] = ""
        job_orders["machine_brands_preferred"] = ""
        job_orders["controls_preferred"] = ""
        job_orders["materials_required"] = ""
        job_orders["industry_experience_preferred"] = ""
        job_orders["start_window_days"] = ""
        job_orders["travel_required"] = False
        job_orders["pay_range_optional"] = job_orders.get("pay_range", "")
        job_orders["per_diem_required"] = ""
        job_orders["compliance_requirements"] = ""
        job_orders["status"] = job_orders.get("stage", "")

    return {
        "assignments": assignments,
        "workers": workers,
        "open_positions": positions,
        "recruiter_activity": recruiter_activity,
        "clients": clients,
        "job_orders": job_orders,
    }


def load_customer_import_preview(data_dir: str | os.PathLike[str] = DATA_DIR) -> dict[str, Any]:
    data_path = Path(data_dir)
    diagnostics: list[dict[str, str]] = []
    _, source_inventory = _source_inventory(data_path)

    roster_tables = _load_roster(data_path, diagnostics)
    tests = _load_test_scores(data_path, diagnostics)
    candidates = _load_candidate_process(data_path, tests, diagnostics)
    intake_questions = _load_intake_questions(data_path, diagnostics)
    timecard_blueprint = _build_timecard_blueprint(intake_questions)

    tables: dict[str, pd.DataFrame] = {
        **roster_tables,
        "customer_candidates": candidates,
        "customer_candidate_tests": tests,
        "customer_intake_questions": intake_questions,
        "timecard_blueprint": timecard_blueprint,
        "import_diagnostics": pd.DataFrame(diagnostics),
        "source_inventory": source_inventory,
    }

    summary = {
        "assignments": len(tables["customer_assignments"]),
        "open_positions": len(tables["customer_open_positions"]),
        "ended_assignments": len(tables["customer_ended_assignments"]),
        "candidates": len(tables["customer_candidates"]),
        "candidate_tests": len(tables["customer_candidate_tests"]),
        "intake_questions": len(tables["customer_intake_questions"]),
        "timecard_setup_fields": len(tables["timecard_blueprint"]),
        "loaded_sources": sum(1 for item in diagnostics if item["status"] == "loaded"),
        "missing_or_error_sources": sum(1 for item in diagnostics if item["status"] != "loaded"),
        "recognized_files": int((source_inventory["status"] == "used").sum()) if not source_inventory.empty else 0,
        "unrecognized_files": int((source_inventory["status"] == "unrecognized").sum()) if not source_inventory.empty else 0,
        "duplicate_files": int((source_inventory["status"] == "duplicate ignored").sum()) if not source_inventory.empty else 0,
    }

    return {"summary": summary, "tables": tables, "diagnostics": diagnostics}
