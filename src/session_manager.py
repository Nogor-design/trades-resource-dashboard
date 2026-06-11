"""
Runtime session helpers for customer uploads.

Customer-provided files should never be treated like repository data. This
module keeps uploads in per-session runtime folders and provides one reset path
that clears both files and Streamlit state.
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT_DIR / "runtime_sessions"
UPLOAD_DIR = ROOT_DIR / "runtime_uploads"
EXPORT_DIR = ROOT_DIR / "runtime_exports"
DEFAULT_SESSION_TTL_HOURS = 24.0

ALLOWED_UPLOAD_EXTENSIONS = {".csv", ".pdf", ".xls", ".xlsx", ".xlsm"}

CUSTOMER_SESSION_STATE_KEYS = [
    "worker_overrides",
    "position_overrides",
    "worker_notes",
    "action_statuses",
    "added_workers",
    "demo_sent_emails",
    "demo_sent_sms",
    "customer_upload_manifest",
    "customer_upload_last_saved",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_utc_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def safe_session_id(value: str | None = None) -> str:
    if value and re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", value):
        return value
    return uuid.uuid4().hex[:12]


def safe_filename(name: str) -> str:
    cleaned = Path(name).name
    cleaned = re.sub(r"[^A-Za-z0-9 ._()#+-]+", "_", cleaned).strip(" .")
    return cleaned or f"upload-{uuid.uuid4().hex[:8]}"


def session_paths(session_id: str) -> dict[str, Path]:
    session_id = safe_session_id(session_id)
    return {
        "session": RUNTIME_DIR / session_id,
        "raw": UPLOAD_DIR / session_id / "raw",
        "normalized": UPLOAD_DIR / session_id / "normalized",
        "exports": EXPORT_DIR / session_id,
        "manifest": RUNTIME_DIR / session_id / "manifest.json",
        "audit": RUNTIME_DIR / session_id / "audit.jsonl",
    }


def ensure_runtime_session(state: Any) -> str:
    session_id = safe_session_id(str(state.get("upload_session_id", "")) if "upload_session_id" in state else None)
    state["upload_session_id"] = session_id
    paths = session_paths(session_id)
    paths["session"].mkdir(parents=True, exist_ok=True)
    paths["raw"].mkdir(parents=True, exist_ok=True)
    paths["normalized"].mkdir(parents=True, exist_ok=True)
    paths["exports"].mkdir(parents=True, exist_ok=True)
    return session_id


def list_raw_uploads(session_id: str) -> list[Path]:
    raw_dir = session_paths(session_id)["raw"]
    if not raw_dir.exists():
        return []
    return sorted(path for path in raw_dir.iterdir() if path.is_file())


def read_manifest(session_id: str) -> dict[str, Any]:
    manifest_path = session_paths(session_id)["manifest"]
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_manifest(session_id: str, manifest: dict[str, Any]) -> None:
    paths = session_paths(session_id)
    paths["session"].mkdir(parents=True, exist_ok=True)
    paths["manifest"].write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def append_audit_event(session_id: str, event: str, details: dict[str, Any] | None = None) -> None:
    paths = session_paths(session_id)
    paths["session"].mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": utc_now_iso(),
        "event": event,
        "details": details or {},
    }
    with paths["audit"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")


def save_uploaded_files(session_id: str, uploaded_files: list[Any], label: str = "") -> dict[str, Any]:
    paths = session_paths(session_id)
    paths["raw"].mkdir(parents=True, exist_ok=True)
    previous = read_manifest(session_id)
    now = utc_now_iso()

    saved = []
    rejected = []
    for uploaded in uploaded_files:
        filename = safe_filename(getattr(uploaded, "name", "upload"))
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
            rejected.append({"filename": filename, "reason": "Unsupported file type"})
            continue

        target = paths["raw"] / filename
        target.write_bytes(uploaded.getbuffer())
        saved.append({
            "filename": filename,
            "size_bytes": target.stat().st_size,
            "extension": suffix,
        })

    current_files = [
        {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "extension": path.suffix.lower(),
        }
        for path in list_raw_uploads(session_id)
    ]
    manifest = {
        "session_id": session_id,
        "label": label.strip(),
        "created_at": previous.get("created_at") or now,
        "updated_at": now,
        "raw_dir": str(paths["raw"]),
        "saved_files": current_files,
        "rejected_files": previous.get("rejected_files", []) + rejected,
    }
    write_manifest(session_id, manifest)
    append_audit_event(session_id, "upload_saved", {
        "saved_count": len(saved),
        "rejected_count": len(rejected),
        "label_present": bool(label.strip()),
    })
    return manifest


def update_manifest_import_summary(session_id: str, preview: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    manifest = read_manifest(session_id)
    if not manifest:
        return {}

    summary = preview.get("summary", {})
    review_df = review.get("review")
    issues_df = review.get("issues")
    manifest["import_summary"] = {
        "updated_at": utc_now_iso(),
        "assignments": int(summary.get("assignments", 0) or 0),
        "open_positions": int(summary.get("open_positions", 0) or 0),
        "candidates": int(summary.get("candidates", 0) or 0),
        "candidate_tests": int(summary.get("candidate_tests", 0) or 0),
        "intake_questions": int(summary.get("intake_questions", 0) or 0),
        "loaded_sources": int(summary.get("loaded_sources", 0) or 0),
        "missing_or_error_sources": int(summary.get("missing_or_error_sources", 0) or 0),
        "review_areas": int(len(review_df)) if review_df is not None else 0,
        "review_items": int(len(issues_df)) if issues_df is not None else 0,
    }
    write_manifest(session_id, manifest)
    return manifest


def session_expiration(session_id: str, ttl_hours: float = DEFAULT_SESSION_TTL_HOURS) -> dict[str, Any]:
    manifest = read_manifest(session_id)
    created = parse_utc_iso(manifest.get("created_at") or manifest.get("updated_at"))
    if created is None:
        return {
            "created_at": "",
            "expires_at": "",
            "is_expired": False,
            "hours_until_expiry": None,
        }
    expires = created + timedelta(hours=max(float(ttl_hours), 0.0))
    now = datetime.now(timezone.utc)
    hours_until = round((expires - now).total_seconds() / 3600, 2)
    return {
        "created_at": created.replace(microsecond=0).isoformat(),
        "expires_at": expires.replace(microsecond=0).isoformat(),
        "is_expired": now >= expires,
        "hours_until_expiry": hours_until,
    }


def session_is_expired(session_id: str, ttl_hours: float = DEFAULT_SESSION_TTL_HOURS) -> bool:
    return bool(session_expiration(session_id, ttl_hours).get("is_expired"))


def purge_expired_sessions(ttl_hours: float = DEFAULT_SESSION_TTL_HOURS) -> int:
    purged = 0
    if not RUNTIME_DIR.exists():
        return purged
    for session_dir in RUNTIME_DIR.iterdir():
        if not session_dir.is_dir():
            continue
        session_id = session_dir.name
        if session_is_expired(session_id, ttl_hours):
            for target in (
                session_paths(session_id)["raw"],
                session_paths(session_id)["normalized"],
                session_paths(session_id)["exports"],
                session_paths(session_id)["session"],
            ):
                shutil.rmtree(target, ignore_errors=True)
            purged += 1
    return purged


def clear_customer_runtime_state(state: Any) -> None:
    defaults = {
        "worker_overrides": {},
        "position_overrides": {},
        "worker_notes": [],
        "action_statuses": {},
        "added_workers": [],
        "demo_sent_emails": [],
        "demo_sent_sms": [],
    }
    for key in CUSTOMER_SESSION_STATE_KEYS:
        if key in defaults:
            state[key] = defaults[key]
        elif key in state:
            del state[key]
    state["data_source"] = "Demo Data"
    state["presentation_mode"] = "Client Demo Mode"


def reset_runtime_session(session_id: str, state: Any | None = None) -> None:
    paths = session_paths(session_id)
    append_audit_event(session_id, "reset_requested", {})
    for key in ("raw", "normalized", "exports"):
        shutil.rmtree(paths[key], ignore_errors=True)
    if paths["manifest"].exists():
        paths["manifest"].unlink()
    if state is not None:
        clear_customer_runtime_state(state)
        state["upload_session_id"] = safe_session_id()
        ensure_runtime_session(state)


def runtime_summary(session_id: str, ttl_hours: float = DEFAULT_SESSION_TTL_HOURS) -> dict[str, Any]:
    uploads = list_raw_uploads(session_id)
    manifest = read_manifest(session_id)
    expiration = session_expiration(session_id, ttl_hours)
    return {
        "session_id": session_id,
        "label": manifest.get("label", ""),
        "created_at": manifest.get("created_at", ""),
        "updated_at": manifest.get("updated_at", ""),
        "expires_at": expiration.get("expires_at", ""),
        "is_expired": expiration.get("is_expired", False),
        "hours_until_expiry": expiration.get("hours_until_expiry"),
        "import_summary": manifest.get("import_summary", {}),
        "file_count": len(uploads),
        "total_bytes": sum(path.stat().st_size for path in uploads),
        "files": [path.name for path in uploads],
    }
