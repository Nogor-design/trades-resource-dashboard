"""
demo_data_generator.py
Generates all fake/demo CSV data for the Trades Resource Command Center.
Run independently with: python src/demo_data_generator.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

random.seed(42)
np.random.seed(42)

TODAY = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

CLIENTS = [
    {"client_id": "C01", "client_name": "Apex Precision Manufacturing",    "industry": "Aerospace & Defense",  "location": "Denver",        "state": "CO"},
    {"client_id": "C02", "client_name": "Mountain Tool & Die",              "industry": "Tooling & Machining",  "location": "Colorado Springs","state": "CO"},
    {"client_id": "C03", "client_name": "ForgeWorks Industrial",            "industry": "Heavy Manufacturing",  "location": "Pueblo",        "state": "CO"},
    {"client_id": "C04", "client_name": "Summit Aerospace Components",      "industry": "Aerospace & Defense",  "location": "Aurora",        "state": "CO"},
    {"client_id": "C05", "client_name": "Rocky Mountain Fabrication",       "industry": "Metal Fabrication",    "location": "Longmont",      "state": "CO"},
    {"client_id": "C06", "client_name": "Prime Motion Systems",             "industry": "Industrial Equipment", "location": "Fort Collins",  "state": "CO"},
    {"client_id": "C07", "client_name": "Western CNC Solutions",            "industry": "Precision Machining",  "location": "Albuquerque",   "state": "NM"},
    {"client_id": "C08", "client_name": "High Plains Manufacturing",        "industry": "Agricultural Equipment","location": "Amarillo",      "state": "TX"},
    {"client_id": "C09", "client_name": "Titan Industrial Group",           "industry": "Oil & Gas Equipment",  "location": "Midland",       "state": "TX"},
    {"client_id": "C10", "client_name": "Front Range Components",           "industry": "Precision Machining",  "location": "Boulder",       "state": "CO"},
    {"client_id": "C11", "client_name": "Mesa Verde Manufacturing",         "industry": "Automotive Parts",     "location": "Grand Junction", "state": "CO"},
    {"client_id": "C12", "client_name": "Pikes Peak Precision",             "industry": "Defense & Aerospace",  "location": "Colorado Springs","state": "CO"},
    {"client_id": "C13", "client_name": "Desert Sun Fabricators",           "industry": "Solar & Energy",        "location": "Phoenix",       "state": "AZ"},
    {"client_id": "C14", "client_name": "Redrock Industrial Services",      "industry": "Mining & Extraction",  "location": "Salt Lake City", "state": "UT"},
    {"client_id": "C15", "client_name": "Cascade Precision Works",          "industry": "Precision Machining",  "location": "Boise",         "state": "ID"},
]

ROLES_BY_TRADE = {
    "CNC":          ["CNC Machinist", "CNC Lathe Operator", "CNC Mill Machinist",
                     "5-Axis Machinist", "Swiss Machinist", "CNC Programmer"],
    "Welding":      ["TIG Welder", "MIG Welder", "Pipe Welder", "Structural Welder"],
    "Maintenance":  ["Maintenance Technician", "Maintenance Mechanic", "Industrial Maintenance Tech"],
    "Electrical":   ["Industrial Electrician", "Controls Technician", "PLC Technician"],
    "Quality":      ["Quality Inspector", "CMM Inspector", "Quality Technician"],
    "Tooling":      ["Tool & Die Maker", "Manual Machinist", "Die Setter"],
    "Field Service":["Field Service Technician", "Field Maintenance Tech"],
}

RECRUITERS = ["Sarah Mitchell", "Jason Torres", "Amy Chen", "Derek Williams"]

FIRST_NAMES = ["James","Michael","Robert","John","David","William","Richard","Joseph","Thomas","Charles",
               "Maria","Jennifer","Patricia","Linda","Barbara","Elizabeth","Susan","Jessica","Karen","Sarah",
               "Kevin","Brian","George","Edward","Ronald","Timothy","Jason","Jeffrey","Ryan","Gary",
               "Lisa","Nancy","Betty","Margaret","Sandra","Dorothy","Ashley","Emily","Donna","Michelle"]

LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
              "Wilson","Anderson","Taylor","Thomas","Hernandez","Moore","Jackson","Martin","Lee","Perez",
              "Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker","Young",
              "Hall","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores","Green"]

CERTIFICATIONS_POOL = [
    "OSHA 10", "OSHA 30", "AWS CWI", "AWS D1.1", "CWB", "Forklift", "Overhead Crane",
    "Blueprint Reading", "GD&T", "CMM Operation", "Mastercam", "Fanuc", "Haas", "Mazak",
    "Siemens 840D", "PLC Programming", "Electrical Safety", "Arc Flash",
]

SKILLS_POOL = {
    "CNC":          ["G-code Programming", "Fanuc Controls", "Haas Controls", "Mazak Controls",
                     "Tight Tolerance Work", "5-Axis Programming", "CAM Software", "Blueprint Reading"],
    "Welding":      ["TIG Welding", "MIG Welding", "Stick Welding", "Pipe Welding",
                     "Stainless Steel", "Aluminum Welding", "Structural Welding", "Pressure Vessel"],
    "Maintenance":  ["Hydraulics", "Pneumatics", "PLC Troubleshooting", "Predictive Maintenance",
                     "Mechanical Repairs", "Electrical Troubleshooting", "PM Scheduling"],
    "Electrical":   ["PLC Programming", "VFD Drives", "Panel Building", "Conduit Installation",
                     "Motor Controls", "480V 3-Phase", "HMI Programming"],
    "Quality":      ["CMM Operation", "GD&T", "SPC", "First Article Inspection",
                     "AS9100", "ISO 9001", "Gage R&R", "Inspection Reports"],
    "Tooling":      ["Die Design", "Progressive Dies", "Manual Machining", "Fixture Building",
                     "Jig & Fixture", "Heat Treatment", "EDM"],
    "Field Service":["Equipment Troubleshooting", "Preventive Maintenance", "Customer Support",
                     "Travel-Ready", "Service Documentation", "Hydraulics", "Electrical"],
}

STATES_POOL = ["CO", "TX", "NM", "AZ", "UT", "ID", "WY", "MT", "NV", "KS"]
CITIES_BY_STATE = {
    "CO": ["Denver", "Colorado Springs", "Aurora", "Boulder", "Fort Collins", "Longmont", "Pueblo"],
    "TX": ["Amarillo", "Midland", "Lubbock", "El Paso", "Abilene"],
    "NM": ["Albuquerque", "Santa Fe", "Las Cruces", "Roswell"],
    "AZ": ["Phoenix", "Tucson", "Mesa", "Tempe"],
    "UT": ["Salt Lake City", "Provo", "Ogden"],
    "ID": ["Boise", "Nampa", "Meridian"],
    "WY": ["Cheyenne", "Casper", "Laramie"],
    "MT": ["Billings", "Missoula", "Great Falls"],
    "NV": ["Las Vegas", "Reno", "Henderson"],
    "KS": ["Wichita", "Topeka", "Overland Park"],
}

REDEPLOYMENT_STATUSES = [
    "Not Started", "Worker Contacted", "Interested",
    "Matched to Open Role", "Submitted", "Redeployed", "Not Available", "Follow Up Later"
]

SHIFTS = ["Day", "Swing", "Night", "Weekend", "Rotating"]
DURATIONS = ["Temp-to-Hire", "6 months", "3 months", "12 months", "Open-ended", "Project-based"]

POSITION_STAGES = [
    "New Intake", "Intake Incomplete", "Sourcing", "Candidates Identified",
    "Submitted to Client", "Interviewing", "Offer / Confirmation", "On Hold"
]

ACTIVITY_TYPES = [
    "Worker Check-In", "Client Follow-Up", "Candidate Submission",
    "Interview Scheduled", "Offer Extended", "Redeployment Call",
    "Intake Meeting", "Reference Check", "Onboarding Support", "Position Review"
]

ACTIVITY_STATUSES = ["Complete", "Pending", "Overdue", "In Progress", "Cancelled"]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def random_date(min_days_ago: int, max_days_ago: int) -> datetime:
    """Return a random date between min_days_ago and max_days_ago in the past."""
    days = random.randint(min_days_ago, max_days_ago)
    return TODAY - timedelta(days=days)

def future_date(min_days: int, max_days: int) -> datetime:
    days = random.randint(min_days, max_days)
    return TODAY + timedelta(days=days)

def fmt(dt: datetime) -> str:
    if pd.isna(dt) or dt is None:
        return ""
    return dt.strftime("%Y-%m-%d")

def pick_client():
    return random.choice(CLIENTS)

def pick_trade():
    return random.choice(list(ROLES_BY_TRADE.keys()))

def pick_role(trade):
    return random.choice(ROLES_BY_TRADE[trade])

def pick_state():
    return random.choice(STATES_POOL)

def pick_city(state):
    return random.choice(CITIES_BY_STATE.get(state, ["Denver"]))


# Matching-engine brand/control pools by trade
_BRANDS_BY_TRADE = {
    "CNC":         ["Mazak", "Okuma", "Haas", "Fanuc", "Makino", "Mori Seiki", "Doosan", "Hermle"],
    "Welding":     ["Lincoln", "Miller", "ESAB", "Hobart"],
    "Maintenance": ["Allen-Bradley", "Siemens", "Yaskawa", "ABB"],
    "Electrical":  ["Allen-Bradley", "Siemens", "Schneider"],
    "Quality":     ["CMM", "Keyence", "Zeiss", "Renishaw"],
    "Tooling":     ["Haas", "Mazak", "Fanuc"],
    "Field Service":["Allen-Bradley", "Siemens"],
}
_CONTROLS_BY_TRADE = {
    "CNC":         ["Mazatrol", "OSP", "Fanuc", "Heidenhain", "Siemens 840D"],
    "Welding":     [],
    "Maintenance": ["PLC", "HMI", "SCADA"],
    "Electrical":  ["PLC", "VFD", "HMI"],
    "Quality":     ["PC-DMIS", "CMM", "Calypso"],
    "Tooling":     ["Fanuc", "Mazatrol"],
    "Field Service":["PLC", "HMI"],
}
_MATERIALS_BY_TRADE = {
    "CNC":         ["Aluminum", "Titanium", "Inconel", "Stainless Steel", "Steel"],
    "Welding":     ["Carbon Steel", "Stainless Steel", "Aluminum", "Inconel"],
    "Maintenance": [],
    "Electrical":  [],
    "Quality":     ["Aluminum", "Titanium"],
    "Tooling":     ["Tool Steel", "Aluminum", "Steel"],
    "Field Service":[],
}
_INDUSTRY_BY_TRADE = {
    "CNC":         ["Aerospace", "Defense", "Medical Device", "Precision Manufacturing", "Automotive"],
    "Welding":     ["Shipbuilding", "Industrial", "Structural", "Pressure Vessel", "Aerospace"],
    "Maintenance": ["Food Manufacturing", "Packaging", "Automotive", "Industrial Equipment"],
    "Electrical":  ["Industrial Equipment", "Food Manufacturing", "Packaging"],
    "Quality":     ["Aerospace", "Medical Device", "Defense", "Precision Manufacturing"],
    "Tooling":     ["Automotive", "Precision Manufacturing", "Defense"],
    "Field Service":["Industrial Equipment", "Oil & Gas", "Mining"],
}

# ---------------------------------------------------------------------------
# Generate workers
# ---------------------------------------------------------------------------

def generate_workers(n=70) -> pd.DataFrame:
    rows = []
    
    # ── SPECIFIC SEEDS FROM CLIENT CONVERSATION NOTES ─────────────────────────
    # Mike R., Jason T., Robert L.
    
    # Mike R.: CNC Machinist, missing pay rate, availability; test complete; Ready
    rows.append({
        "worker_id":               "W001",
        "worker_name":             "Mike R.",
        "primary_trade":           "CNC Machinist",
        "trade_category":          "CNC",
        "home_state":              "CO",
        "skills":                  "G-code Programming; Haas Controls; Tight Tolerance Work",
        "certifications":          "OSHA 10; Blueprint Reading",
        "machine_brands":          "Haas; Mazak",
        "controls":                "Fanuc",
        "materials_experience":    "Aluminum; Stainless Steel",
        "industry_experience":     "Aerospace; Precision Manufacturing",
        "cnc_mill_experience":     True,
        "five_axis_experience":    False,
        "setup_ability":           True,
        "preferred_locations":     "Denver",
        "preferred_region":        "CO",
        "preferred_states":        "CO; TX",
        "willing_to_travel":       True,
        "shift_preference":        "1st shift",
        "prior_assignment_rating": 4.6,
        "availability_date":       "",  # Missing!
        "current_assignment_id":   "",
        "recruiter_owner":         "Sarah Mitchell",
        "last_contact":            fmt(random_date(10, 15)),
        "redeployment_status":     "Not Started",
        "missing_information_flags": "pay_rate, availability missing",
        "recruiter_notes":         "Needs checkin to obtain pay rate preference.",
        "status":                  "Active",
        "notes":                   "Highly recommended by past clients.",
        # Recruiter Quality Tracker fields
        "candidate_fields_complete": False,
        "missing_fields":          "Pay rate, availability",
        "proficiency_test_status": "Complete",
        "spreadsheet_updated":     False,
        "last_update_timestamp":   fmt(random_date(1, 3)),
        "process_status":          "Ready",
    })
    
    # Jason T.: Welder, missing travel preference; test pending welder safety; Needs update
    rows.append({
        "worker_id":               "W002",
        "worker_name":             "Jason T.",
        "primary_trade":           "TIG Welder",
        "trade_category":          "Welding",
        "home_state":              "TX",
        "skills":                  "TIG Welding; Stainless Steel; Aluminum Welding",
        "certifications":          "Forklift",
        "machine_brands":          "Lincoln; Miller",
        "controls":                "",
        "materials_experience":    "Stainless Steel; Aluminum",
        "industry_experience":     "Industrial; Aerospace",
        "cnc_mill_experience":     False,
        "five_axis_experience":    False,
        "setup_ability":           False,
        "preferred_locations":     "Midland",
        "preferred_region":        "TX",
        "preferred_states":        "TX",
        "willing_to_travel":       None,  # Missing!
        "shift_preference":        "Any",
        "prior_assignment_rating": 4.2,
        "availability_date":       fmt(future_date(10, 20)),
        "current_assignment_id":   "",
        "recruiter_owner":         "Jason Torres",
        "last_contact":            fmt(random_date(5, 8)),
        "redeployment_status":     "Not Started",
        "missing_information_flags": "travel readiness blocker",
        "recruiter_notes":         "Awaiting travel commitment and safety testing.",
        "status":                  "Active",
        "notes":                   "Skilled TIG welder, needs safety test completed.",
        # Recruiter Quality Tracker fields
        "candidate_fields_complete": False,
        "missing_fields":          "Travel preference",
        "proficiency_test_status": "Pending Welder Safety",
        "spreadsheet_updated":     False,
        "last_update_timestamp":   fmt(random_date(4, 6)),
        "process_status":          "Needs update",
    })
    
    # Robert L.: Maintenance Tech, missing certifications; test complete; Submitted
    rows.append({
        "worker_id":               "W003",
        "worker_name":             "Robert L.",
        "primary_trade":           "Maintenance Technician",
        "trade_category":          "Maintenance",
        "home_state":              "CO",
        "skills":                  "Hydraulics; PLC Troubleshooting; Mechanical Repairs",
        "certifications":          "",  # Missing!
        "machine_brands":          "Allen-Bradley; Siemens",
        "controls":                "PLC; HMI",
        "materials_experience":    "",
        "industry_experience":     "Food Manufacturing; Packaging",
        "cnc_mill_experience":     False,
        "five_axis_experience":    False,
        "setup_ability":           False,
        "preferred_locations":     "Colorado Springs",
        "preferred_region":        "CO",
        "preferred_states":        "CO; UT; WY",
        "willing_to_travel":       True,
        "shift_preference":        "2nd shift",
        "prior_assignment_rating": 4.8,
        "availability_date":       fmt(future_date(2, 5)),
        "current_assignment_id":   "",
        "recruiter_owner":         "Sarah Mitchell",
        "last_contact":            fmt(random_date(1, 3)),
        "redeployment_status":     "Matched to Open Role",
        "missing_information_flags": "certifications missing",
        "recruiter_notes":         "Needs to submit physical copies of OSHA cards.",
        "status":                  "Active",
        "notes":                   "Outstanding past reviews, highly reliable.",
        # Recruiter Quality Tracker fields
        "candidate_fields_complete": False,
        "missing_fields":          "Certifications",
        "proficiency_test_status": "Complete",
        "spreadsheet_updated":     True,
        "last_update_timestamp":   fmt(random_date(0, 1)),
        "process_status":          "Submitted",
    })

    # Standard loop for generating the rest of the 70 workers (from ID W004 onwards)
    for i in range(4, n + 1):
        trade = pick_trade()
        state = pick_state()
        skills = random.sample(SKILLS_POOL[trade], k=min(4, len(SKILLS_POOL[trade])))
        certs = random.sample(CERTIFICATIONS_POOL, k=random.randint(1, 4))
        preferred_states = [state] + random.sample(
            [s for s in STATES_POOL if s != state], k=random.randint(0, 2)
        )
        # Matching engine fields
        brands_pool   = _BRANDS_BY_TRADE.get(trade, [])
        controls_pool = _CONTROLS_BY_TRADE.get(trade, [])
        materials_pool= _MATERIALS_BY_TRADE.get(trade, [])
        industry_pool = _INDUSTRY_BY_TRADE.get(trade, [])
        machine_brands    = "; ".join(random.sample(brands_pool, k=min(random.randint(1,2), len(brands_pool)))) if brands_pool else ""
        controls_used     = "; ".join(random.sample(controls_pool, k=min(random.randint(1,2), len(controls_pool)))) if controls_pool else ""
        materials_exp     = "; ".join(random.sample(materials_pool, k=min(random.randint(1,2), len(materials_pool)))) if materials_pool else ""
        industry_exp      = "; ".join(random.sample(industry_pool, k=min(random.randint(1,2), len(industry_pool)))) if industry_pool else ""
        willing_to_travel = random.random() < 0.65
        cnc_mill  = trade in ("CNC", "Tooling")
        five_axis = cnc_mill and random.random() < 0.45
        setup_ab  = cnc_mill and random.random() < 0.70
        rating    = round(random.uniform(3.5, 5.0), 1)
        
        # Determine completeness
        complete_bucket = random.random()
        if complete_bucket < 0.15:  # 15% incomplete
            fields_complete = False
            missing = random.choice(["Prior references", "Availability date", "Certifications", "Shift preference"])
            test_status = random.choice(["Complete", "Pending CNC Proficiency", "Pending Welder Safety"])
            status_val = "Needs update"
            updated = False
        else:
            fields_complete = True
            missing = ""
            test_status = "Complete"
            status_val = random.choice(["Ready", "Submitted"])
            updated = True

        missing_flags = ""
        if not fields_complete:
            missing_flags = f"{missing.lower()} missing"
        elif trade == "CNC" and not five_axis and random.random() < 0.3:
            missing_flags = "5-axis experience missing"
        elif not willing_to_travel and random.random() < 0.2:
            missing_flags = "travel readiness blocker"

        rows.append({
            "worker_id":               f"W{i:03d}",
            "worker_name":             random_name(),
            "primary_trade":           pick_role(trade),
            "trade_category":          trade,
            "home_state":              state,
            "skills":                  "; ".join(skills),
            "certifications":          "; ".join(certs) if fields_complete else "",
            "machine_brands":          machine_brands,
            "controls":                controls_used,
            "materials_experience":    materials_exp,
            "industry_experience":     industry_exp,
            "cnc_mill_experience":     cnc_mill,
            "five_axis_experience":    five_axis,
            "setup_ability":           setup_ab,
            "preferred_locations":     pick_city(state),
            "preferred_region":        state,
            "preferred_states":        "; ".join(preferred_states),
            "willing_to_travel":       willing_to_travel,
            "shift_preference":        random.choice(["1st shift", "2nd shift", "Any", "Any"]),
            "prior_assignment_rating": rating,
            "availability_date":       fmt(future_date(0, 90)) if fields_complete else "",
            "current_assignment_id":   "",
            "recruiter_owner":         random.choice(RECRUITERS),
            "last_contact":            fmt(random_date(0, 30)),
            "redeployment_status":     "Not Started",
            "missing_information_flags": missing_flags,
            "recruiter_notes":         "Candidate screened successfully." if fields_complete else "Awaiting candidate follow-up details.",
            "status":                  "Active",
            "notes":                   "",
            # Quality Tracker fields
            "candidate_fields_complete": fields_complete,
            "missing_fields":          missing,
            "proficiency_test_status": test_status,
            "spreadsheet_updated":     updated,
            "last_update_timestamp":   fmt(random_date(1, 10)),
            "process_status":          status_val,
        })
        
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Generate assignments (60 active)
# ---------------------------------------------------------------------------

def generate_assignments(workers_df: pd.DataFrame, n=60) -> pd.DataFrame:
    rows = []
    worker_pool = workers_df.sample(n=n, random_state=42).reset_index(drop=True)

    for i, worker in worker_pool.iterrows():
        client = pick_client()
        trade = worker["trade_category"]
        role = worker["primary_trade"]
        state = client["state"]
        city = client["location"]
        recruiter = worker["recruiter_owner"]

        # Distribute end dates realistically
        bucket = random.random()
        if bucket < 0.05:        # ~3 already ended (critical)
            start = random_date(120, 180)
            end = random_date(5, 20)
            redeploy_status = random.choice(["Not Started", "Worker Contacted"])
            time_off = False
        elif bucket < 0.12:      # ~4 ending within 7 days (red)
            start = random_date(90, 150)
            end = future_date(1, 6)
            redeploy_status = random.choice(["Not Started", "Worker Contacted", "Interested"])
            time_off = False
        elif bucket < 0.25:      # ~8 ending within 14 days (orange)
            start = random_date(60, 120)
            end = future_date(7, 13)
            redeploy_status = random.choice(["Not Started", "Worker Contacted", "Interested", "Matched to Open Role"])
            time_off = random.random() < 0.2  # 20% scheduled time off soon
        elif bucket < 0.45:      # ~12 ending within 30 days (yellow)
            start = random_date(30, 90)
            end = future_date(14, 29)
            redeploy_status = random.choice(["Not Started", "Worker Contacted", "Follow Up Later"])
            time_off = random.random() < 0.15
        else:                    # ~33 healthy (green)
            start = random_date(0, 60)
            end = future_date(30, 180)
            redeploy_status = random.choice(["Not Started", "Redeployed", "Not Available", ""])
            time_off = random.random() < 0.10

        pay_rate = round(random.uniform(22, 55), 2)
        bill_rate = round(pay_rate * random.uniform(1.35, 1.65), 2)
        margin = round(bill_rate - pay_rate, 2)

        last_worker_contact = random_date(0, 25)  # 0-25 days ago
        last_client_contact = random_date(0, 20)  # 0-20 days ago

        # Time off calculation
        to_start = ""
        to_end = ""
        if time_off:
            offset = random.randint(1, 20)
            to_start = fmt(TODAY + timedelta(days=offset))
            to_end = fmt(TODAY + timedelta(days=offset + random.randint(1, 5)))

        # Travel parameters (Trades Resource traveling workforce model)
        willing_travel = worker["willing_to_travel"]
        is_traveler = willing_travel if willing_travel is not None else random.choice([True, False])
        if is_traveler:
            travel_status = random.choice(["On Site", "On Site", "En Route", "Returned"])
            per_diem = True
            lodging = random.choice([True, True, False])  # Mostly confirmed
        else:
            travel_status = "Not Applicable"
            per_diem = False
            lodging = False

        # Extension status choices:
        # Active / healthy, Check-in needed, Time off upcoming, Renewal needed, Extension pending, Ending soon, Redeployment needed, Forecast risk
        days_rem = (end - TODAY).days
        
        # Predict status statically
        if days_rem < 0:
            ext_status = "Redeployment needed"
            fc_status = "At Risk"
        elif days_rem <= 7:
            ext_status = "Ending soon"
            fc_status = "At Risk"
        elif days_rem <= 14:
            ext_status = "Renewal needed"
            fc_status = "Pending Extension"
        elif days_rem <= 30:
            ext_status = "Extension pending"
            fc_status = "Pending Extension"
        elif time_off:
            ext_status = "Time off upcoming"
            fc_status = "Healthy"
        elif (TODAY - last_worker_contact).days > 14:
            ext_status = "Check-in needed"
            fc_status = "Healthy"
        else:
            ext_status = "Active / healthy"
            fc_status = "Healthy"

        original_dur = random.choice(["3 months", "6 months", "12 months", "Project-based"])
        projected_end = end
        # 10% have extension end date pushed out
        if random.random() < 0.10:
            projected_end = end + timedelta(days=random.choice([30, 60]))
            ext_status = "Extension pending"

        # Checkin history
        checkin_due = last_worker_contact + timedelta(days=14)

        rows.append({
            "assignment_id": f"A{i+1:03d}",
            "worker_id": worker["worker_id"],
            "worker_name": worker["worker_name"],
            "client_name": client["client_name"],
            "role": role,
            "trade_category": trade,
            "location": city,
            "state": state,
            "recruiter_owner": recruiter,
            "start_date": fmt(start),
            "end_date": fmt(end),
            "status": "Active",
            "last_worker_contact": fmt(last_worker_contact),
            "last_client_contact": fmt(last_client_contact),
            "pay_rate": pay_rate,
            "bill_rate": bill_rate,
            "margin": margin,
            "extension_possible": random.choice(["Yes", "No", "Unknown"]),
            "redeployment_status": redeploy_status if redeploy_status else "Not Started",
            "notes": random.choice([
                "Worker performing exceptionally.", "Client extremely satisfied.",
                "Discussed extension options.", "Worker open to redeployment.",
                "Reviewing per diem expenses.", "Travel logistics finalized.",
            ]),
            # NEW FORECASTING & WORKFORCE FIELDS
            "original_duration": original_dur,
            "current_projected_end_date": fmt(projected_end),
            "extension_status": ext_status,
            "renewal_due_date": fmt(end - timedelta(days=14)),
            "time_off_start": to_start,
            "time_off_end": to_end,
            "forecast_status": fc_status,
            "last_check_in_date": fmt(last_worker_contact),
            "next_check_in_due": fmt(checkin_due),
            "next_action": random.choice(["Conduct worker check-in", "Propose formal extension", "Source next traveling assignment", "Approve per diem", "No action needed"]),
            "travel_status": travel_status,
            "per_diem_approved": per_diem,
            "lodging_confirmed": lodging,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Generate open positions (20)
# ---------------------------------------------------------------------------

def generate_open_positions(n=20) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        client = pick_client()
        trade = pick_trade()
        role = pick_role(trade)
        priority = random.choices(["High", "Medium", "Low"], weights=[4, 4, 2])[0]
        stage = random.choice(POSITION_STAGES)
        days_open = random.randint(1, 45)
        date_opened = TODAY - timedelta(days=days_open)
        target_start = future_date(3, 35)
        submitted_cnt = random.randint(0, 5) if stage not in ["New Intake", "Intake Incomplete", "Sourcing"] else 0
        intake_complete = stage not in ["New Intake", "Intake Incomplete"]
        pay_low = round(random.uniform(20, 40), 2)
        pay_high = round(pay_low * random.uniform(1.1, 1.4), 2)

        # Generate submitted candidate names
        names = []
        dates = []
        if submitted_cnt > 0:
            for c in range(submitted_cnt):
                names.append(random_name())
                dates.append(fmt(date_opened + timedelta(days=random.randint(1, max(1, days_open - 1)))))

        approval = "No Submissions"
        if submitted_cnt > 0:
            if stage in ["Submitted to Client", "Interviewing"]:
                approval = random.choice(["Pending Client Review", "Pending Client Review", "Client Rejected"])
            elif stage in ["Offer / Confirmation"]:
                approval = "Client Approved"
            else:
                approval = "Pending Client Review"

        interview = "Not Scheduled"
        if stage == "Interviewing":
            interview = "Scheduled"
        elif stage in ["Offer / Confirmation"]:
            interview = "Completed"

        feedback_pool = [
            "Resume looks solid, schedule technical screen.",
            "Client requested proficiency test results.",
            "Candidate unavailable for rotating shifts.",
            "Strong local CNC Machinist, interview set.",
            "Welder AWS certifications verified successfully.",
            "Excellent per diem rates negotiated."
        ]

        rows.append({
            "position_id": f"P{i:03d}",
            "client_name": client["client_name"],
            "role": role,
            "trade_category": trade,
            "location": client["location"],
            "state": client["state"],
            "priority": priority,
            "recruiter_owner": random.choice(RECRUITERS),
            "date_opened": fmt(date_opened),
            "target_start_date": fmt(target_start),
            "days_open": days_open,
            "stage": stage,
            "candidates_submitted": submitted_cnt,
            "client_response_status": random.choice(
                ["Pending", "Responded", "Pending", "No Response", "Active"]
            ),
            "intake_complete": intake_complete,
            "pay_range": f"${pay_low:.0f} - ${pay_high:.0f}/hr",
            "shift": random.choice(SHIFTS),
            "duration": random.choice(DURATIONS),
            "notes": random.choice([
                "Client needs traveling workforce setup.",
                "Per diem approved for this local region.",
                "Client slow on candidate feedback.",
                "Needs OSHA 10 completed.",
                "Strong urgent need for Mill setups.",
            ]),
            # NEW CANDIDATE SUBMISSION TRACKING FIELDS
            "candidate_submitted_names": "; ".join(names),
            "candidate_submission_dates": "; ".join(dates),
            "approval_status": approval,
            "interview_status": interview,
            "client_feedback": random.choice(feedback_pool) if submitted_cnt > 0 else "",
            "last_order_update": fmt(TODAY - timedelta(days=random.randint(1, 5))),
            "next_order_action": random.choice(["Gather recruiter feedback", "Follow up on client review", "Schedule on-site interview", "Draft confirmation packet", "Source more candidates"]),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Generate recruiter activity (35)
# ---------------------------------------------------------------------------

def generate_recruiter_activity(workers_df, positions_df, clients_df, n=35) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        recruiter = random.choice(RECRUITERS)
        activity_type = random.choice(ACTIVITY_TYPES)
        worker_name = random.choice(workers_df["worker_name"].tolist()) if random.random() > 0.3 else ""
        client_name = random.choice(clients_df["client_name"].tolist()) if random.random() > 0.4 else ""
        pos_id = random.choice(positions_df["position_id"].tolist()) if random.random() > 0.5 else ""

        days_ago = random.randint(-3, 14)
        activity_date = TODAY - timedelta(days=days_ago)
        due_offset = random.randint(-5, 10)
        due_date = activity_date + timedelta(days=due_offset)

        if due_date < TODAY:
            status = random.choices(["Complete", "Overdue"], weights=[6, 4])[0]
        else:
            status = random.choices(["Pending", "In Progress", "Complete"], weights=[4, 3, 3])[0]

        rows.append({
            "activity_id": f"ACT{i:03d}",
            "recruiter_name": recruiter,
            "date": fmt(activity_date),
            "activity_type": activity_type,
            "related_worker": worker_name,
            "related_client": client_name,
            "related_position": pos_id,
            "status": status,
            "next_action": random.choice([
                "Follow up in 3 days", "Wait for client response",
                "Schedule interview", "Send offer letter",
                "Confirm start date", "Submit resume", "Call worker back",
                "Update position stage", "Check references", "",
            ]),
            "due_date": fmt(due_date),
            "notes": random.choice([
                "Left voicemail.", "Email sent regarding per diem.", "Good conversation.",
                "Client reviewing resumes.", "Worker confirmed availability.",
                "Waiting on background check.", "Lodging confirmed for start date.",
            ]),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Generate clients table
# ---------------------------------------------------------------------------

def generate_clients(assignments_df, positions_df) -> pd.DataFrame:
    rows = []
    for c in CLIENTS:
        active = len(assignments_df[assignments_df["client_name"] == c["client_name"]])
        opens = len(positions_df[positions_df["client_name"] == c["client_name"]])
        rows.append({
            "client_id": c["client_id"],
            "client_name": c["client_name"],
            "industry": c["industry"],
            "location": c["location"],
            "state": c["state"],
            "active_assignments": active,
            "open_positions": opens,
            "last_contact": fmt(random_date(1, 20)),
            "account_status": random.choice(["Active", "Active", "Active", "Warm", "New"]),
            "notes": random.choice([
                "Key account focusing on traveling CNC talent.",
                "Increasing headcount for aerospace surge.",
                "Strong direct-hire relationship.",
                "Requires lodging assistance for travelers.",
                "Outstanding invoice review pending.",
            ]),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_all(output_dir: str = "data"):
    os.makedirs(output_dir, exist_ok=True)

    print("Generating workers...")
    workers = generate_workers(70)

    print("Generating assignments...")
    assignments = generate_assignments(workers, 60)

    # Back-fill current_assignment_id on workers
    for _, row in assignments.iterrows():
        mask = workers["worker_id"] == row["worker_id"]
        workers.loc[mask, "current_assignment_id"] = row["assignment_id"]

    print("Generating open positions...")
    positions = generate_open_positions(20)

    print("Generating clients...")
    clients_full = generate_clients(assignments, positions)

    print("Generating recruiter activity...")
    activity = generate_recruiter_activity(workers, positions, clients_full, 35)

    # Save
    workers.to_csv(os.path.join(output_dir, "workers.csv"), index=False)
    assignments.to_csv(os.path.join(output_dir, "assignments.csv"), index=False)
    positions.to_csv(os.path.join(output_dir, "open_positions.csv"), index=False)
    clients_full.to_csv(os.path.join(output_dir, "clients.csv"), index=False)
    activity.to_csv(os.path.join(output_dir, "recruiter_activity.csv"), index=False)

    print(f"\nDone! Demo data written to '{output_dir}/'")
    print(f"   workers.csv            -> {len(workers)} rows")
    print(f"   assignments.csv        -> {len(assignments)} rows")
    print(f"   open_positions.csv     -> {len(positions)} rows")
    print(f"   clients.csv            -> {len(clients_full)} rows")
    print(f"   recruiter_activity.csv -> {len(activity)} rows")


if __name__ == "__main__":
    generate_all()
