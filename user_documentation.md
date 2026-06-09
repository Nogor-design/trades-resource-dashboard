# ⚙️ Trades Resource Command Center — Operations Guide

> **PROTOTYPE — Demo Data Only.**
> This is a concept prototype using generated demo data. It is designed to show what the workflow could look like. A production version would connect to real spreadsheets, databases, or your existing tools.

---

## What This Prototype Solves

This system is built around four confirmed pain points:

1. **Active assignments** are tracked in spreadsheets
2. **Open orders** are tracked on paper and memory
3. **Recruiter workflow** is difficult to monitor consistently
4. **Forecasting renewals, extensions, time off, and redeployment** takes too much owner attention

The goal is one operational command center showing:

- Who is currently assigned and when assignments end
- Which assignments need renewal or extension follow-up
- Who has upcoming time off, and whether the client has been notified
- Which open orders need candidates or client approval
- Which recruiter process steps are incomplete
- What the owner should focus on today vs. what can be delegated

> **"Forecasting so the owner can focus on sales."**
> This helps move the business from spreadsheet + paper + memory to one command center.

---

## First-Meeting Demo Flow

Focus on these four screens for the first client meeting:

| # | Screen | What It Replaces | Helps Answer |
|---|--------|-----------------|--------------|
| 1 | 🏠 Owner Today View | Manual daily briefing from memory | "What needs attention today?" |
| 2 | 📅 Assignment Forecast | Assignment spreadsheet | "What's ending soon and what's the plan?" |
| 3 | 📋 Open Orders Board | Paper order tracking | "Which jobs need candidates or approval?" |
| 4 | 👥 Recruiter Process Tracker | Candidate update spreadsheet | "Is the process being followed consistently?" |

**Candidate Matching, Redeployment Planning, and Submittal Packets** are available as future expansion areas. Show them briefly only if the meeting is going well.

---

## Tab-by-Tab Guide

### 1. 🏠 Owner Today View

**What it does:** Shows what needs attention today — replacing memory-based tracking with structured visibility.

- **Prototype disclaimer** — always visible at the top as a reminder this uses demo data
- **What This Solves** — expandable intro explaining the four pain points addressed
- **A. Urgent Actions Today** — assignments ending within 7 days and overdue recruiter tasks
- **B. Assignments Ending Soon** — workers ending in the next 30 days
- **C. Stuck Open Positions** — positions stalled due to missing intake or no candidates submitted
- **D. Recruiter Workload Summary** — visual charts of open positions, overdue tasks, and ending assignments by recruiter
- **E. Owner Sales Focus** — table showing what is stable vs. what needs attention; designed to help the owner decide what can be delegated and where to focus on sales
- **F. Renewal & Extension Forecast** — assignments ending in the next 45 days with renewal conversation dates, extension status, and alert level
- **G. Upcoming Time Off** — workers with scheduled time off, client notification status, and coverage needs
- **H. Bench Depth Signals** — available worker pool analysis for rapid deployment

**Suggested talking point:**
> "This is the screen that replaces memory-based tracking. It shows what needs attention today, what is coming up, and what may affect forecasting."

---

### 2. 📅 Active Assignment Forecast

**What it does:** Gantt-style timeline showing all active assignments with renewals, extensions, and time-off markers visible.

- Each bar represents one worker's assignment, colored by urgency
- Today line shows exactly where you are in the timeline
- Event markers: 🔵 Time Off · 🟡 Renewal Due · 🟠 Ending 14d · ❌ Ending 7d · 🟣 Extension Pending · ⭐ Redeployed
- Highlight filter lets you isolate a specific event type (e.g., view only workers with time off)
- Forecast table below the chart shows extension status, time off, and next action per worker

**Suggested talking point:**
> "This helps you see what is coming before it turns into a fire."

---

### 3. 📋 Open Orders Board

**What it does:** Replaces paper tracking for jobs that need to be filled.

- Master table shows every open order with recruiter owner, candidates submitted, submission dates, approval status, interview status, and client feedback
- **Action Needed** column automatically flags: Sourcing needed · Follow-up needed · Schedule interview · Approved · Intake incomplete
- **Stuck flag** highlights positions that have been open too long or have no candidates submitted
- **Approval Status guide:** Not Submitted → Submitted → Waiting on Client → Approved → Interview Scheduled → Offer Pending → Filled
- Alert rules: Candidate submitted 3+ days with no client response = follow-up needed; No submissions after 7 days = sourcing needed

**Suggested talking point:**
> "This gives you one place to see every open order, who has been submitted, whether they were approved, and what needs to happen next."

---

### 4. 👥 Recruiter Process Tracker

**What it does:** Creates process visibility without micromanagement.

- **Candidate Readiness & Process Tracker** — shows profile completion %, missing fields, proficiency test status, and readiness status for each candidate
- **Recruiter Action Queue** — prioritized task list derived from candidate readiness and open order pipeline
- **Recruiter Workload Summary** — visual breakdown of how assignments, open orders, and tasks are distributed
- Drill down into any individual recruiter to see their open positions, assignments ending soon, overdue actions, and workers needing check-in

**Suggested talking point:**
> "This is not meant to police the recruiter. It is meant to make the process visible and consistent so nothing gets missed."

---

### 5. 🔍 Candidate Matching *(Future Expansion)*

Score available workers against a structured job order using transparent rule-based logic. Recruiter review always required.

---

### 6. 🔄 Redeployment Planning *(Future Expansion)*

Plan next placements for workers whose assignments are ending soon, before they roll off.

---

### 7. 📤 Submittal Packets *(Future Expansion)*

Generate client-ready candidate summary packets. Rule-based draft with optional AI assist — recruiter review required.

---

### 8. 🗄️ Data / Admin

View and download the underlying demo data tables. Includes: Assignments, Workers, Open Positions, Recruiter Activity, Clients, and Alerts. Use "Regenerate All Demo Data" to create a fresh dataset.

---

## How to Launch

Open a terminal inside the project directory and run:

```bash
streamlit run app.py
```

This starts the local Streamlit server on port 8501. Your browser will open automatically.

---

## Success Metrics

When this system is in production use, success would be measured by:

- Fewer missed renewal conversations
- Fewer missed extension decisions
- Fewer assignments ending without a redeployment plan
- Better visibility into upcoming time off
- Less paper tracking for open orders
- Fewer incomplete candidate records
- Faster candidate submissions
- Faster client follow-up after submission
- Better recruiter update consistency
- Less manual reporting by the owner
- More owner time spent on sales
- Better forecasting of active assignments and available workers

---

## Non-Goals

This system is **not** intended to:

- Replace recruiter judgment or client relationships
- Fully automate the recruiting process
- Monitor employees in a punitive way
- Force the company into a complicated software platform before the process is clear

The goal is **visibility, consistency, forecasting, and better follow-through.**

---

## Phased Roadmap

### Phase 1 — Visibility *(this prototype)*
- Active assignment tracking
- Open order tracking
- Upcoming action dashboard
- Assignment forecast timeline
- Recruiter process tracker
- Basic CSV export

### Phase 2 — Workflow Consistency
- Structured client intake
- Required field enforcement
- Candidate profile completion
- Proficiency testing workflow
- Candidate submission workflow
- Follow-up reminders
- Open order update rules

### Phase 3 — Forecasting
- Renewal forecast
- Extension forecast
- Time-off forecast
- Redeployment forecast
- Available worker forecast
- Open order demand forecast

### Phase 4 — Decision Support
- Candidate matching
- Redeployment suggestions
- Submittal packet generation
- Sales focus recommendations
- Client opportunity tracking
- AI summaries where useful

---

## What We Would Need From Trades Resource

To convert this prototype into a working internal tool, we would need:

1. Current active assignment spreadsheet
2. Current open orders list
3. Candidate / recruiter process spreadsheet
4. Technical job intake document
5. Current proficiency testing process
6. Required fields for candidates and job orders
7. Current reporting needs
8. Desired alert timing for renewals, extensions, time off, and follow-ups
9. Existing tools currently in use (spreadsheets, email, ATS, CRM, calendar, accounting system)
10. Decision on where the system should live long-term

---

## Prototype Scope

This is a concept prototype using generated demo data. A production version would require:

- Connecting to real spreadsheets, databases, an ATS, or shared files
- Defining required fields for the company's workflow
- Importing current active assignments
- Importing current open orders
- Importing candidate and recruiter process data
- Setting user permissions
- Confirming alert timing
- Adding backup and export procedures
- Deciding where the system lives long-term

Notes entered in this prototype are stored only in the current browser session and are not persisted to any database. A production version would save notes to a database or approved shared data source.

---

## Frequently Asked Questions

#### How do I unblock a stuck position?
1. Go to **Owner Today View** (Section C) or the **Open Orders Board**
2. Expand the *Stuck & Blocked Positions* section
3. Click **Unblock** next to the position
4. Fill in the intake status, update the stage, write resolution notes, and click **Save & Unblock**

#### How do I filter the assignment timeline?
Open the left sidebar and use the **Timeline Filters** section to filter by recruiter, client, trade category, urgency, or ending window. The Gantt chart and forecast table update instantly.

#### How do I filter open orders?
Use the **Position Filters** section in the left sidebar to filter by priority, stage, recruiter, or stuck status.

---

*Trades Resource Command Center — Prototype v3.0 — Demo Data Only*
