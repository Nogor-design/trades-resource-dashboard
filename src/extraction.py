"""extraction.py — copied from tradesresource. Parses free-text client requests."""
DEMO_JOB_TEXT = (
    "Need two travel-ready CNC setup machinists for a 3-month aerospace project "
    "in Ohio. Must have 5-axis experience. Mazak or Okuma preferred. Second shift. "
    "Start within two weeks. Aerospace tolerance experience preferred."
)


def requirements_from_job_order(row) -> dict:
    return {
        "role":                    row["role"],
        "quantity":                int(row.get("quantity", 1)),
        "location_state":          row.get("client_state", row.get("state", "")),
        "contract_length_months":  int(row.get("contract_length_months", 3)),
        "machine_type":            row.get("machine_type", ""),
        "preferred_machine_brands": _split(row.get("machine_brands_preferred", "")),
        "controls_preferred":       _split(row.get("controls_preferred", "")),
        "materials_required":       _split(row.get("materials_required", "")),
        "industry":                row.get("industry_experience_preferred", row.get("trade_category", "")),
        "shift":                   row.get("shift", "Any"),
        "start_window_days":       int(row.get("start_window_days", 14)),
        "travel_required":         bool(row.get("travel_required", True)),
        "urgency":                 row.get("urgency", row.get("priority", "Normal")),
        "raw_request":             row.get("client_notes", row.get("notes", "")),
    }


def extract_job_requirements(raw_text: str) -> dict:
    """Deterministic rule-based extractor for common trades scenarios."""
    text = raw_text.lower()
    role = "CNC Machinist"
    if "setup machinist" in text:
        role = "CNC Setup Machinist"
    elif "welder" in text:
        role = "Welder"
    elif "quality inspector" in text or "inspector" in text:
        role = "Quality Inspector"
    elif "maintenance technician" in text or "maintenance tech" in text:
        role = "Maintenance Technician"

    state = ""
    for label, abbr in [
        ("ohio", "OH"), ("pennsylvania", "PA"), ("north carolina", "NC"),
        ("georgia", "GA"), ("michigan", "MI"), ("indiana", "IN"),
        ("texas", "TX"), ("illinois", "IL"), ("arizona", "AZ"),
        ("california", "CA"), ("wisconsin", "WI"), ("kentucky", "KY"),
    ]:
        if label in text:
            state = abbr

    shift = "Any"
    if "first shift" in text or "1st shift" in text:
        shift = "1st shift"
    elif "second shift" in text or "2nd shift" in text:
        shift = "2nd shift"
    elif "third shift" in text or "3rd shift" in text:
        shift = "3rd shift"

    return {
        "role":                   role,
        "quantity":               _qty(text),
        "location_state":         state,
        "contract_length_months": _months(text),
        "machine_type":           _machine(text),
        "preferred_machine_brands": [
            b for b in ["Mazak", "Okuma", "Lincoln", "Miller", "CMM",
                        "Keyence", "Allen-Bradley", "Siemens", "Haas",
                        "Fanuc", "Makino"] if b.lower() in text
        ],
        "controls_preferred": [
            c for c in ["Mazatrol", "OSP", "Fanuc", "PC-DMIS", "PLC", "Heidenhain"]
            if c.lower() in text
        ],
        "materials_required": [
            m for m in ["Aluminum", "Titanium", "Stainless Steel", "Carbon Steel",
                        "Inconel", "Steel"] if m.lower() in text
        ],
        "industry":               _industry(text),
        "shift":                  shift,
        "start_window_days":      _start_window(text),
        "travel_required":        "travel" in text,
        "urgency":                "High" if ("within two weeks" in text or "urgent" in text) else "Normal",
        "raw_request":            raw_text or DEMO_JOB_TEXT,
    }


def _split(value) -> list[str]:
    if not value or str(value).lower() in ("nan", ""):
        return []
    return [t.strip() for t in str(value).replace(",", ";").split(";") if t.strip()]

def _qty(text: str) -> int:
    if "three" in text or " 3 " in text:
        return 3
    if "two" in text or " 2 " in text:
        return 2
    return 1

def _months(text: str):
    for n, w in [(4, "four"), (3, "three"), (2, "two"), (6, "six")]:
        if f"{n}-month" in text or f"{w}-month" in text:
            return n
    return None

def _machine(text: str) -> str:
    if "5-axis" in text:
        return "5-axis mill"
    if "cmm" in text:
        return "CMM inspection"
    if "plc" in text or "maintenance" in text:
        return "industrial maintenance"
    if "weld" in text:
        return "structural welding"
    return ""

def _industry(text: str) -> str:
    for i in ["Aerospace", "Medical Device", "Shipbuilding", "Industrial",
              "Food Manufacturing", "Packaging", "Defense", "Automotive"]:
        if i.lower() in text:
            return i
    return ""

def _start_window(text: str):
    if "two weeks" in text or "within 14" in text:
        return 14
    if "three weeks" in text or "within 21" in text:
        return 21
    if "30 days" in text or "within 30" in text:
        return 30
    return 14
