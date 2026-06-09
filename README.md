# Trades Resource Assignment & Recruiter Command Center

A polished Streamlit operations dashboard for a skilled-trades recruiting and staffing company. Provides real-time visibility into active worker assignments, open positions, recruiter workload, and upcoming redeployment needs.

> ⚠️ **All data is fake/demo data.** No real employee, client, or business data is used.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app (demo data is generated automatically on first run)
streamlit run app.py
```

The app opens at **http://localhost:8501** in your browser.

---

## Pages

| Page | Purpose |
|------|---------|
| 🏠 **Today Dashboard** | Command-center KPIs, urgent alerts, assignments ending soon, stuck positions, recruiter workload |
| 📅 **Assignment Timeline** | Gantt-style chart of all 60 active assignments, color-coded by urgency, with today line and filters |
| 📋 **Open Positions** | All open roles grouped by stage, stuck-position flags, priority breakdown, filters |
| 👥 **Recruiter Workboard** | Per-recruiter workload scores, overdue tasks, check-in needs, open positions |
| 🔄 **Redeployment** | Workers ending soon, redeployment status tracking, simple trade-category matching |
| 🗄 **Data / Admin** | View and download all underlying tables, optional CSV upload, data regeneration |

---

## Business Rules (Deterministic)

### Assignment Urgency
| Color | Condition |
|-------|-----------|
| 🔴 Critical (dark red) | End date passed AND redeployment not resolved |
| 🔴 Red | ≤ 7 days remaining |
| 🟠 Orange | ≤ 14 days remaining |
| 🟡 Yellow | ≤ 30 days remaining |
| 🟢 Green | > 30 days remaining |

### Stuck Position Flags
A position is flagged as stuck if any of:
- Intake is incomplete
- Open more than 7 days with zero candidate submissions
- High priority and zero submissions
- Target start date within 7 days and not filled/confirmed

### Workload Score (per recruiter)
```
score = (open_positions × 2) + (high_priority × 3) + (overdue_actions × 2) + (ending_soon × 2)
```
- Light: < 10
- Balanced: 10–20
- Heavy: 20–32
- Overloaded: 32+

---

## Project Structure

```
recruter-dashboard/
├── app.py                        # Main Streamlit application
├── requirements.txt
├── README.md
├── data/                         # Auto-generated demo CSVs
│   ├── assignments.csv
│   ├── workers.csv
│   ├── open_positions.csv
│   ├── recruiter_activity.csv
│   └── clients.csv
└── src/
    ├── data_loader.py            # CSV loading with auto-generation fallback
    ├── rules.py                  # All business rules and scoring logic
    ├── charts.py                 # Plotly chart builders
    ├── components.py             # Streamlit UI components (KPI cards, badges, etc.)
    └── demo_data_generator.py    # Generates realistic fake demo data
```

---

## Demo Data

Run the generator independently:
```bash
python src/demo_data_generator.py
```

Generated data includes:
- **60 active assignments** across 15 clients and 4 recruiters
- **70 workers** with skills, certifications, and location preferences
- **20 open positions** in various stages
- **35 recruiter activity records** with realistic statuses and due dates
- **15 client records** with active assignment and position counts

Trade categories: CNC · Welding · Maintenance · Electrical · Quality · Tooling · Field Service

---

## Suggested Next Improvements

1. **Persistent edit mode** — allow recruiters to update redeployment status directly in the UI
2. **Real database backend** — replace CSV files with SQLite or PostgreSQL
3. **Email/Slack alerts** — trigger notifications for overdue actions
4. **User authentication** — per-recruiter login with filtered views
5. **Activity logging** — track when actions were taken in the app
6. **Calendar integration** — sync assignment end dates with Google Calendar
7. **Mobile-responsive view** — optimize for phone/tablet use in the field
8. **Custom date range filters** — filter timeline by arbitrary date ranges
9. **Bulk action tools** — mark multiple assignments or positions at once
10. **Simulated AI summary** — plain-English "here's what needs attention" using deterministic templates
