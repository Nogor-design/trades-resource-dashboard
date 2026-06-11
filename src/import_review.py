"""
Customer import review helpers.

These checks convert staged import tables into customer-facing review rows:
what loaded, what needs attention, and which dashboard area is affected.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _table(preview: dict[str, Any], name: str) -> pd.DataFrame:
    table = preview.get("tables", {}).get(name, pd.DataFrame())
    return table if isinstance(table, pd.DataFrame) else pd.DataFrame()


def _is_blank(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().isin(["", "nan", "None", "NaT"])


def _missing_count(df: pd.DataFrame, column: str) -> int:
    if df.empty or column not in df.columns:
        return 0
    return int(_is_blank(df[column]).sum())


def _add_issue(rows: list[dict[str, Any]], area: str, severity: str, issue: str, count: int, action: str) -> None:
    if count <= 0:
        return
    rows.append({
        "area": area,
        "severity": severity,
        "issue": issue,
        "affected_rows": count,
        "recommended_action": action,
    })


def build_import_review(preview: dict[str, Any]) -> dict[str, pd.DataFrame]:
    summary = preview.get("summary", {})
    diagnostics = _table(preview, "import_diagnostics")
    inventory = _table(preview, "source_inventory")
    assignments = _table(preview, "customer_assignments")
    positions = _table(preview, "customer_open_positions")
    candidates = _table(preview, "customer_candidates")
    tests = _table(preview, "customer_candidate_tests")
    intake = _table(preview, "customer_intake_questions")
    timecards = _table(preview, "timecard_blueprint")

    issue_rows: list[dict[str, Any]] = []

    if not diagnostics.empty and {"source", "status"}.issubset(diagnostics.columns):
        for _, row in diagnostics[diagnostics["status"] != "loaded"].iterrows():
            issue_rows.append({
                "area": "Loaded Sources",
                "severity": "Warning" if row.get("status") == "missing" else "Error",
                "issue": f"{row.get('source', 'Source')} is {row.get('status', 'not loaded')}",
                "affected_rows": 1,
                "recommended_action": row.get("detail", "Confirm the source file is expected for this review."),
            })

    _add_issue(issue_rows, "Assignments", "Warning", "Missing assignment end date",
               _missing_count(assignments, "end_date"), "Confirm commitment/final-day dates before relying on renewal forecasts.")
    _add_issue(issue_rows, "Assignments", "Warning", "Missing assignment client",
               _missing_count(assignments, "client_name"), "Add client name so assignment forecasting can group correctly.")
    _add_issue(issue_rows, "Assignments", "Warning", "Missing worker name",
               _missing_count(assignments, "worker_name"), "Confirm the roster row represents an active assignment.")

    _add_issue(issue_rows, "Open Orders", "Warning", "Missing open-order client",
               _missing_count(positions, "client_name"), "Add client name before using open-order follow-up views.")
    _add_issue(issue_rows, "Open Orders", "Warning", "Missing role/title",
               _missing_count(positions, "role"), "Add role/title so orders can be matched and discussed.")
    _add_issue(issue_rows, "Open Orders", "Info", "Missing submitted candidate names",
               _missing_count(positions, "candidate_submitted_names"), "Treat blank rows as needs-candidates unless the customer confirms otherwise.")

    _add_issue(issue_rows, "Candidates", "Warning", "Missing phone",
               _missing_count(candidates, "phone"), "Collect phone numbers before using outbound workflow features.")
    _add_issue(issue_rows, "Candidates", "Warning", "Missing email",
               _missing_count(candidates, "email"), "Collect emails before using submittal packet or communication workflows.")
    _add_issue(issue_rows, "Candidates", "Info", "Missing primary trade",
               _missing_count(candidates, "primary_trade"), "Add primary trade so matching and readiness filters are more useful.")

    if not candidates.empty and "process_status" in candidates.columns:
        incomplete = ~candidates["process_status"].astype(str).str.strip().isin(["Ready", "Available"])
        _add_issue(issue_rows, "Candidates", "Info", "Candidates not ready/available",
                   int(incomplete.sum()), "Review process steps before sending candidates to clients.")

    if intake.empty:
        _add_issue(issue_rows, "Intake & Timecards", "Warning", "No intake questions loaded",
                   1 if int(summary.get("loaded_sources", 0)) else 0, "Upload the intake PDF to map setup/timecard fields.")
    if timecards.empty:
        _add_issue(issue_rows, "Intake & Timecards", "Info", "No timecard blueprint generated",
                   1 if int(summary.get("loaded_sources", 0)) else 0, "Confirm intake source has timecard-related prompts.")

    review_rows = [
        {
            "dashboard_area": "Owner Today / Assignment Forecast",
            "staged_rows": len(assignments),
            "needs_attention": sum(1 for item in issue_rows if item["area"] == "Assignments"),
            "status": "Ready" if len(assignments) and not any(item["area"] == "Assignments" and item["severity"] == "Error" for item in issue_rows) else "Needs source data",
            "customer_value": "Shows active assignments, endings, renewals, extensions, and next action.",
        },
        {
            "dashboard_area": "Open Orders Board",
            "staged_rows": len(positions),
            "needs_attention": sum(1 for item in issue_rows if item["area"] == "Open Orders"),
            "status": "Ready" if len(positions) else "Needs source data",
            "customer_value": "Shows open orders, submitted candidates, approval state, and follow-up work.",
        },
        {
            "dashboard_area": "Recruiter Process Tracker",
            "staged_rows": len(candidates),
            "needs_attention": sum(1 for item in issue_rows if item["area"] == "Candidates"),
            "status": "Ready" if len(candidates) else "Needs source data",
            "customer_value": "Shows candidate readiness, missing process steps, and recruiter action queues.",
        },
        {
            "dashboard_area": "Testing / Skill Evidence",
            "staged_rows": len(tests),
            "needs_attention": 0,
            "status": "Ready" if len(tests) else "Optional / missing",
            "customer_value": "Adds CNC/welder test evidence to candidate review.",
        },
        {
            "dashboard_area": "Intake & Timecards",
            "staged_rows": len(intake),
            "needs_attention": sum(1 for item in issue_rows if item["area"] == "Intake & Timecards"),
            "status": "Ready" if len(intake) else "Optional / missing",
            "customer_value": "Turns client setup questions into reusable timecard/workflow fields.",
        },
    ]

    issues = pd.DataFrame(issue_rows)
    review = pd.DataFrame(review_rows)
    if issues.empty:
        issues = pd.DataFrame(columns=["area", "severity", "issue", "affected_rows", "recommended_action"])

    ready_count = int((review["status"] == "Ready").sum()) if not review.empty else 0
    warning_count = int((issues["severity"] == "Warning").sum()) if not issues.empty else 0
    error_count = int((issues["severity"] == "Error").sum()) if not issues.empty else 0
    info_count = int((issues["severity"] == "Info").sum()) if not issues.empty else 0
    loaded_count = int(summary.get("loaded_sources", 0) or 0)
    unrecognized_count = int(summary.get("unrecognized_files", 0) or 0)
    duplicate_count = int(summary.get("duplicate_files", 0) or 0)
    recognized_count = int(summary.get("recognized_files", 0) or 0)

    if error_count:
        readiness = "Blocked"
        readiness_action = "Fix errored source files before using the dashboard for a customer review."
    elif warning_count:
        readiness = "Review needed"
        readiness_action = "Use the dashboard, but confirm warning items with the customer."
    elif loaded_count:
        readiness = "Ready"
        readiness_action = "Uploaded data is ready for the guided demo flow."
    else:
        readiness = "Needs upload"
        readiness_action = "Upload roster, candidate tracker, test exports, and intake PDF."

    missing_fields = int(issues["affected_rows"].sum()) if not issues.empty else 0
    loaded_names = ", ".join(diagnostics[diagnostics["status"] == "loaded"]["source"].astype(str).tolist()) if not diagnostics.empty else ""
    unrecognized_names = ", ".join(inventory[inventory["status"] == "unrecognized"]["filename"].astype(str).tolist()) if not inventory.empty else ""

    checklist = pd.DataFrame([
        {
            "section": "Loaded Sources",
            "status": "Ready" if loaded_count else "Needs upload",
            "what_it_means": f"{loaded_count} source(s) loaded; {recognized_count} recognized file(s).",
            "next_action": loaded_names or "Upload customer source files.",
        },
        {
            "section": "Ready To Use",
            "status": readiness,
            "what_it_means": f"{ready_count} dashboard area(s) are ready; {warning_count} warning(s), {error_count} error(s).",
            "next_action": readiness_action,
        },
        {
            "section": "Needs Attention",
            "status": "Review needed" if (warning_count or error_count or info_count) else "Clear",
            "what_it_means": f"{len(issues)} review item(s): {error_count} error, {warning_count} warning, {info_count} info.",
            "next_action": "Review the items table below with the customer." if len(issues) else "No review items found.",
        },
        {
            "section": "Missing Fields",
            "status": "Review needed" if missing_fields else "Clear",
            "what_it_means": f"{missing_fields} row-level field issue(s) were detected.",
            "next_action": "Confirm blanks before relying on follow-up, matching, or communication workflows." if missing_fields else "No missing-field issues detected.",
        },
        {
            "section": "Dashboard Impact",
            "status": "Ready" if ready_count else "Needs source data",
            "what_it_means": f"{len(review)} dashboard area(s) reviewed for customer demo readiness.",
            "next_action": "Start with Owner Today, Assignment Forecast, Open Orders, and Recruiter Process Tracker.",
        },
        {
            "section": "Unrecognized Files",
            "status": "Review needed" if unrecognized_count else "Clear",
            "what_it_means": f"{unrecognized_count} unrecognized file(s); {duplicate_count} duplicate file(s) ignored.",
            "next_action": unrecognized_names or "All uploaded files were recognized or intentionally ignored.",
        },
    ])

    return {"review": review, "issues": issues, "checklist": checklist}
