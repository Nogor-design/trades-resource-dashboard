"""
app.py
Trades Resource Assignment & Recruiter Command Center
Streamlit 1.57+ compatible.

Run with: streamlit run app.py
"""

import hmac
import os, sys, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.data_loader import load_all
from src.customer_imports import build_customer_dashboard_data, load_customer_import_preview
from src import rules, charts, components

# New matching-engine modules
from src.matching_engine  import score_all_workers
from src.readiness        import add_readiness_status
from src.actions_engine   import generate_actions
from src.candidate_state  import (
    apply_worker_overrides, update_worker_override,
    add_worker_note, get_worker_notes, NOTE_TYPES,
    apply_position_overrides, update_position_override,
)
from src.explanations     import build_match_explanation
from src.summaries        import (
    generate_client_summary, generate_recruiter_digest,
    generate_requirement_brief,
)
from src.bench            import build_bench_insights
from src.extraction       import extract_job_requirements, requirements_from_job_order, DEMO_JOB_TEXT
from src.ollama_client    import DEFAULT_OLLAMA_MODEL, list_ollama_models

# ==============================================================================
# 1. Page config  (MUST be the very first Streamlit call)
# ==============================================================================

st.set_page_config(
    page_title="Trades Resource Command Center",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 2. Global CSS  (hide Streamlit chrome, set colors, fix sidebar text)
# ==============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Targeted reset to avoid breaking ligature icon fonts (like _arrow_right or arrow_down) or code monospace fonts */
html, body, [data-testid="stAppViewContainer"], .stApp, 
.stApp input, .stApp button, .stApp select, .stApp textarea,
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Hide Streamlit chrome decoration and toolbar, keep header for toggle support */
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
#MainMenu, footer { display: none !important; }

/* Style the header transparently and let click events pass through, keeping toggle clickable */
header[data-testid="stHeader"] {
    background-color: transparent !important;
    background: transparent !important;
    border-bottom: none !important;
    pointer-events: none;
    z-index: 99 !important;
}
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] a,
header[data-testid="stHeader"] div {
    pointer-events: auto !important;
}

/* ═══════════════════════════════════════════════════════
   APP BACKGROUND
   ═══════════════════════════════════════════════════════ */
.stApp,
.stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {
    background-color: #f8fafc !important;
    color: #0f172a !important;
}

/* ═══════════════════════════════════════════════════════
   CUSTOM PAGE BANNER & LEGEND OVERRIDES
   ═══════════════════════════════════════════════════════ */
.custom-page-banner h1,
.custom-page-banner p,
.custom-page-banner span,
.custom-page-banner div {
    color: #ffffff !important;
}
.custom-legend-card,
.custom-legend-card div,
.custom-legend-card span {
    color: #475569 !important;
}
.custom-legend-card strong {
    color: #0f172a !important;
}

/* ═══════════════════════════════════════════════════════
   MAIN CONTENT CONTAINER
   ═══════════════════════════════════════════════════════ */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1500px !important;
}

/* ═══════════════════════════════════════════════════════
   SIDEBAR — comprehensive selector coverage
   ═══════════════════════════════════════════════════════ */

/* Universal sidebar text styling — targeted elements only (no wildcard * to avoid aria/svg rendering bugs) */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] li {
    color: #1e293b !important;
}

/* Ensure inner Streamlit user widget container overflows cleanly into the parent container without rendering its own scrollbar */
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
[data-testid="stSidebar"] [class*="SidebarUserContent"] {
    height: auto !important;
    max-height: none !important;
    overflow-x: hidden !important;
    padding-bottom: 2rem !important;
}

/* ─── DESKTOP STATE (Screen >= 1200px): native collapsible sidebar ─── */
@media (min-width: 1200px) {
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
        background-color: #f1f5f9 !important;
        border-right: 1px solid #cbd5e1 !important;
        z-index: 100 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    
    [data-testid="stSidebar"] > div {
        background-color: #f1f5f9 !important;
        height: auto !important;
        overflow-x: hidden !important;
    }
    
    /* Keep Streamlit's native hide/show controls visible on desktop. */
    [data-testid="stSidebarCollapseButton"],
    button[title="Expand sidebar"],
    button[title="Close sidebar"],
    button[class*="CollapseButton"],
    [data-testid="stSidebar"] button[class*="CollapseButton"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12) !important;
        border-radius: 999px !important;
        pointer-events: auto !important;
    }
}

/* ─── RESIZED/NARROW STATE (Screen < 1200px): Collapsible sidebar with premium toggle ─── */
@media (max-width: 1200px) {
    [data-testid="stSidebar"] {
        background-color: #f1f5f9 !important;
        border-right: 1px solid #cbd5e1 !important;
        height: 100vh !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    
    [data-testid="stSidebar"] > div {
        background-color: #f1f5f9 !important;
        height: auto !important;
        overflow-x: hidden !important;
    }
    
    /* Style Streamlit's native sidebar control without forcing custom placement. */
    [data-testid="stSidebarCollapseButton"],
    button[title="Expand sidebar"],
    button[class*="CollapseButton"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12) !important;
        border-radius: 999px !important;
        z-index: 9999 !important;
        pointer-events: auto !important;
    }
    
    [data-testid="stSidebarCollapseButton"] svg,
    button[title="Expand sidebar"] svg,
    button[class*="CollapseButton"] svg {
        fill: #1f5f8b !important;
        color: #1f5f8b !important;
    }
    
    /* Standard close/collapse button inside open sidebar */
    [data-testid="stSidebar"] button[class*="CollapseButton"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        border-radius: 4px !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }
    
    [data-testid="stSidebar"] button[class*="CollapseButton"] svg {
        fill: #1f5f8b !important;
        color: #1f5f8b !important;
    }
}

/* Sidebar section headers (bold markdown) */
[data-testid="stSidebar"] strong {
    color: #1f5f8b !important;
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}

/* Sidebar input fields */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="input"],
[data-testid="stSidebar"] [data-baseweb="select"] {
    background-color: var(--input-bg, #ffffff) !important;
    border-color: var(--input-border, #cbd5e1) !important;
    color: var(--input-text, #0f172a) !important;
}
[data-testid="stSidebar"] [data-baseweb="option"] {
    color: #0f172a !important;
    background-color: #ffffff !important;
}
[data-testid="stSidebar"] [data-baseweb="option"]:hover {
    background-color: #f1f5f9 !important;
}

/* Multiselect tags */
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: #1f5f8b !important;
    border-color: #1f5f8b !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] * {
    color: #ffffff !important;
}

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: #e2e8f0 !important;
    margin: 10px 0 !important;
}

/* Sidebar caption / small text */
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
    color: #64748b !important;
    font-size: 0.75rem !important;
}

/* Toggle in sidebar */
[data-testid="stSidebar"] [data-testid="stToggle"] * {
    color: #1e293b !important;
}

/* ═══════════════════════════════════════════════════════
   MAIN CONTENT — headings
   ═══════════════════════════════════════════════════════ */
h1, h2, h3, h4, h5, h6 {
    color: #0f172a !important;
    font-weight: 700;
}

/* ═══════════════════════════════════════════════════════
   TAB BAR
   ═══════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: #e2e8f0;
    border-radius: 10px;
    padding: 4px 8px;
    gap: 4px;
    border-bottom: none !important;
    flex-wrap: wrap;
    border: 1px solid #cbd5e1;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #475569 !important;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 8px 14px;
    border: none;
    background: transparent;
    white-space: nowrap;
    transition: all 0.2s;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #0f172a !important;
    background: #f1f5f9 !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #1b5f8b 0%, #0e7fb5 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 10px rgba(27, 95, 139, 0.25) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent;
    padding-top: 1.2rem;
}

/* ═══════════════════════════════════════════════════════
   METRICS
   ═══════════════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: #ffffff;
    border-radius: 10px;
    padding: 14px 16px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
[data-testid="metric-container"] label {
    color: #475569 !important;
    font-size: 0.75rem !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-weight: 700;
}

/* ═══════════════════════════════════════════════════════
   DATA EDITOR & DATAFRAMES
   ═══════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}
[data-testid="stDataEditor"] {
    border-radius: 8px;
    border: 1px solid #e2e8f0;
}

/* ═══════════════════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════════════════ */
.stButton > button {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.85rem;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #f8fafc;
    border-color: #1f5f8b;
    color: #1f5f8b;
}
.stDownloadButton > button {
    background: linear-gradient(90deg, #1b5f8b 0%, #0e7fb5 100%) !important;
    color: white !important;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    box-shadow: 0 4px 10px rgba(27, 95, 139, 0.2) !important;
}
.stDownloadButton > button:hover {
    background: linear-gradient(90deg, #16527a 0%, #0c6e9e 100%) !important;
    box-shadow: 0 4px 14px rgba(27, 95, 139, 0.35) !important;
}
.stDownloadButton > button * { color: white !important; }

/* ═══════════════════════════════════════════════════════
   EXPANDER
   ═══════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
[data-testid="stExpander"] summary {
    color: #0f172a !important;
    font-weight: 600;
}
[data-testid="stExpander"] summary p {
    color: #0f172a !important;
    font-weight: 600;
    margin: 0 !important;
}
[data-testid="stExpander"] summary:hover {
    color: #1f5f8b !important;
}
[data-testid="stExpander"] summary:hover p {
    color: #1f5f8b !important;
}

/* ═══════════════════════════════════════════════════════
   ALERTS / INFO / SUCCESS / WARNING / ERROR
   ═══════════════════════════════════════════════════════ */
[data-testid="stInfo"] { background: #eff6ff !important; border-left-color: #3b82f6 !important; }
[data-testid="stSuccess"] { background: #f0fdf4 !important; border-left-color: #22c55e !important; }
[data-testid="stWarning"] { background: #fffbeb !important; border-left-color: #f59e0b !important; }
[data-testid="stError"] { background: #fef2f2 !important; border-left-color: #ef4444 !important; }
[data-testid="stInfo"] p, [data-testid="stInfo"] span,
[data-testid="stSuccess"] p, [data-testid="stSuccess"] span,
[data-testid="stWarning"] p, [data-testid="stWarning"] span,
[data-testid="stError"] p, [data-testid="stError"] span {
    color: #0f172a !important;
}

/* ═══════════════════════════════════════════════════════
   FORMS & INPUTS (main area)
   ═══════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background-color: #ffffff !important;
    border-color: #cbd5e1 !important;
    color: #0f172a !important;
}
[data-baseweb="select"] {
    background-color: #ffffff !important;
    border-color: #cbd5e1 !important;
}
[data-baseweb="menu"] {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
}
[data-baseweb="option"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
}
[data-baseweb="option"]:hover {
    background-color: #f1f5f9 !important;
}

/* Multiselect tags in main area */
[data-baseweb="tag"] {
    background-color: #1f5f8b !important;
}
[data-baseweb="tag"] span { color: #fff !important; }

/* ═══════════════════════════════════════════════════════
   CHECKBOX & TOGGLE
   ═══════════════════════════════════════════════════════ */
[data-testid="stCheckbox"] label,
[data-testid="stCheckbox"] p,
[data-testid="stCheckbox"] span { color: #1e293b !important; }
[data-testid="stToggle"] label,
[data-testid="stToggle"] p,
[data-testid="stToggle"] span { color: #1e293b !important; }

/* ═══════════════════════════════════════════════════════
   CAPTION / SMALL TEXT
   ═══════════════════════════════════════════════════════ */
.stCaption, [data-testid="stCaptionContainer"] * {
    color: #64748b !important;
    font-size: 0.78rem !important;
}

/* ═══════════════════════════════════════════════════════
   SCROLLBAR
   ═══════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

hr { border-color: #e2e8f0 !important; margin: 18px 0; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 3. Demo login gate
# ==============================================================================

def get_demo_credentials():
    username = os.getenv("DEMO_USERNAME") or os.getenv("TRADES_DEMO_USERNAME")
    password = os.getenv("DEMO_PASSWORD") or os.getenv("TRADES_DEMO_PASSWORD")

    try:
        auth_secrets = st.secrets.get("auth", {})
        username = username or auth_secrets.get("username") or st.secrets.get("DEMO_USERNAME")
        password = password or auth_secrets.get("password") or st.secrets.get("DEMO_PASSWORD")
    except Exception:
        pass

    return str(username or ""), str(password or "")


def require_demo_login():
    if st.session_state.get("demo_authenticated"):
        return

    configured_username, configured_password = get_demo_credentials()

    st.markdown("""
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    .block-container {
        max-width: 520px !important;
        padding-top: 12vh !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("Trades Resource Command Center")
    st.caption("Private demo access")

    if not configured_username or not configured_password:
        st.error("Demo login is not configured yet.")
        st.info("Add DEMO_USERNAME and DEMO_PASSWORD in Streamlit Cloud secrets, then restart the app.")
        st.stop()

    with st.form("demo_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        username_ok = hmac.compare_digest(username, configured_username)
        password_ok = hmac.compare_digest(password, configured_password)
        if username_ok and password_ok:
            st.session_state.demo_authenticated = True
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.stop()


require_demo_login()


# ==============================================================================
# 4. Session state initialization (for matching engine + notes)
# ==============================================================================

if "worker_overrides"  not in st.session_state: st.session_state.worker_overrides  = {}
if "position_overrides" not in st.session_state: st.session_state.position_overrides = {}
if "worker_notes"      not in st.session_state: st.session_state.worker_notes      = []
if "action_statuses"   not in st.session_state: st.session_state.action_statuses   = {}
if "raw_job_text"      not in st.session_state: st.session_state.raw_job_text      = DEMO_JOB_TEXT
if "jo_raw_text"       not in st.session_state: st.session_state.jo_raw_text       = DEMO_JOB_TEXT
if "requirements"      not in st.session_state: st.session_state.requirements      = extract_job_requirements(DEMO_JOB_TEXT)
if "use_ai_assist"     not in st.session_state: st.session_state.use_ai_assist     = False
if "llm_model"         not in st.session_state: st.session_state.llm_model         = DEFAULT_OLLAMA_MODEL
if "saved_quick_notes" not in st.session_state: st.session_state.saved_quick_notes = set()
if "added_workers"      not in st.session_state: st.session_state.added_workers      = []
if "demo_sent_emails"   not in st.session_state: st.session_state.demo_sent_emails   = []
if "demo_sent_sms"      not in st.session_state: st.session_state.demo_sent_sms      = []
if "app_theme"          not in st.session_state: st.session_state.app_theme          = "Light Corporate"
if "presentation_mode"  not in st.session_state: st.session_state.presentation_mode  = "Client Demo Mode"
if "data_source"        not in st.session_state: st.session_state.data_source        = "Customer Imports"


# ==============================================================================
# 3b. Theme system — 4 switchable global themes via CSS custom properties
# ==============================================================================

THEMES = {
    # ── 1. Light Corporate (default) ──────────────────────────────────────────
    "Light Corporate": {
        "label": "☀️ Light Corporate",
        "css": """
        :root {
            --app-bg:           #f8fafc;
            --app-text:         #0f172a;
            --sidebar-bg:       #f1f5f9;
            --sidebar-border:   #cbd5e1;
            --sidebar-text:     #1e293b;
            --sidebar-strong:   #1f5f8b;
            --card-bg:          #ffffff;
            --card-border:      #e2e8f0;
            --tab-list-bg:      #e2e8f0;
            --tab-list-border:  #cbd5e1;
            --tab-text:         #475569;
            --tab-text-hover:   #0f172a;
            --tab-hover-bg:     #f1f5f9;
            --tab-active-grad:  linear-gradient(90deg, #1b5f8b 0%, #0e7fb5 100%);
            --tab-active-shadow:0 4px 10px rgba(27,95,139,0.25);
            --accent-grad:      linear-gradient(90deg, #1b5f8b 0%, #0e7fb5 100%);
            --accent-shadow:    rgba(27,95,139,0.2);
            --btn-bg:           #ffffff;
            --btn-text:         #0f172a;
            --btn-border:       #cbd5e1;
            --btn-hover-border: #1f5f8b;
            --btn-hover-text:   #1f5f8b;
            --btn-hover-bg:     #f8fafc;
            --input-bg:         #ffffff;
            --input-border:     #cbd5e1;
            --input-text:       #0f172a;
            --menu-bg:          #ffffff;
            --option-hover-bg:  #f1f5f9;
            --tag-bg:           #1f5f8b;
            --expander-bg:      #ffffff;
            --expander-border:  #e2e8f0;
            --expander-text:    #0f172a;
            --expander-hover:   #1f5f8b;
            --metric-bg:        #ffffff;
            --metric-border:    #e2e8f0;
            --metric-label:     #475569;
            --metric-value:     #0f172a;
            --heading-color:    #0f172a;
            --caption-color:    #64748b;
            --divider-color:    #e2e8f0;
            --scrollbar-track:  #f1f5f9;
            --scrollbar-thumb:  #cbd5e1;
            --scrollbar-hover:  #94a3b8;
            --info-bg:          #eff6ff;
            --success-bg:       #f0fdf4;
            --warning-bg:       #fffbeb;
            --error-bg:         #fef2f2;
            --alert-text:       #0f172a;
        }
        """,
    },

    # ── 2. Dark Mode ──────────────────────────────────────────────────────────
    "Dark Mode": {
        "label": "🌙 Dark Mode",
        "css": """
        :root {
            --app-bg:           #0d1117;
            --app-text:         #e2e8f0;
            --sidebar-bg:       #161b22;
            --sidebar-border:   #30363d;
            --sidebar-text:     #c9d1d9;
            --sidebar-strong:   #79c0ff;
            --card-bg:          #1c2128;
            --card-border:      #30363d;
            --tab-list-bg:      #1c2128;
            --tab-list-border:  #30363d;
            --tab-text:         #8b949e;
            --tab-text-hover:   #e2e8f0;
            --tab-hover-bg:     #21262d;
            --tab-active-grad:  linear-gradient(90deg, #1f5f8b 0%, #0ea5e9 100%);
            --tab-active-shadow:0 4px 12px rgba(31, 95, 139, 0.4);
            --accent-grad:      linear-gradient(90deg, #1f5f8b 0%, #0ea5e9 100%);
            --accent-shadow:    rgba(31, 95, 139, 0.3);
            --btn-bg:           #21262d;
            --btn-text:         #c9d1d9;
            --btn-border:       #30363d;
            --btn-hover-border: #79c0ff;
            --btn-hover-text:   #79c0ff;
            --btn-hover-bg:     #1c2128;
            --input-bg:         #1c2128;
            --input-border:     #30363d;
            --input-text:       #e2e8f0;
            --menu-bg:          #1c2128;
            --option-hover-bg:  #21262d;
            --tag-bg:           #1f5f8b;
            --expander-bg:      #1c2128;
            --expander-border:  #30363d;
            --expander-text:    #e2e8f0;
            --expander-hover:   #79c0ff;
            --metric-bg:        #1c2128;
            --metric-border:    #30363d;
            --metric-label:     #8b949e;
            --metric-value:     #e2e8f0;
            --heading-color:    #e2e8f0;
            --caption-color:    #6e7681;
            --divider-color:    #30363d;
            --scrollbar-track:  #161b22;
            --scrollbar-thumb:  #30363d;
            --scrollbar-hover:  #484f58;
            --info-bg:          #1c2845;
            --success-bg:       #0f2a1a;
            --warning-bg:       #2a1f0a;
            --error-bg:         #2a0f0f;
            --alert-text:       #e2e8f0;
        }
        """,
    },

    # ── 3. Steel & Slate (trades / industrial feel) ──────────────────────────
    "Steel & Slate": {
        "label": "🔩 Steel & Slate",
        "css": """
        :root {
            --app-bg:           #1a2332;
            --app-text:         #d4e0f0;
            --sidebar-bg:       #141d2b;
            --sidebar-border:   #2d3f55;
            --sidebar-text:     #b0c4de;
            --sidebar-strong:   #4db8e8;
            --card-bg:          #1e2d3d;
            --card-border:      #2d3f55;
            --tab-list-bg:      #141d2b;
            --tab-list-border:  #2d3f55;
            --tab-text:         #7a9bbf;
            --tab-text-hover:   #d4e0f0;
            --tab-hover-bg:     #1e2d3d;
            --tab-active-grad:  linear-gradient(90deg, #0e7fb5 0%, #0a5c85 100%);
            --tab-active-shadow:0 4px 12px rgba(14,127,181,0.4);
            --accent-grad:      linear-gradient(90deg, #0e7fb5 0%, #0a5c85 100%);
            --accent-shadow:    rgba(14,127,181,0.3);
            --btn-bg:           #1e2d3d;
            --btn-text:         #b0c4de;
            --btn-border:       #2d3f55;
            --btn-hover-border: #4db8e8;
            --btn-hover-text:   #4db8e8;
            --btn-hover-bg:     #253344;
            --input-bg:         #1e2d3d;
            --input-border:     #2d3f55;
            --input-text:       #d4e0f0;
            --menu-bg:          #1e2d3d;
            --option-hover-bg:  #253344;
            --tag-bg:           #0e7fb5;
            --expander-bg:      #1e2d3d;
            --expander-border:  #2d3f55;
            --expander-text:    #d4e0f0;
            --expander-hover:   #4db8e8;
            --metric-bg:        #1e2d3d;
            --metric-border:    #2d3f55;
            --metric-label:     #7a9bbf;
            --metric-value:     #d4e0f0;
            --heading-color:    #d4e0f0;
            --caption-color:    #4a7095;
            --divider-color:    #2d3f55;
            --scrollbar-track:  #141d2b;
            --scrollbar-thumb:  #2d3f55;
            --scrollbar-hover:  #3d5470;
            --info-bg:          #0d2035;
            --success-bg:       #0d2018;
            --warning-bg:       #241a08;
            --error-bg:         #241010;
            --alert-text:       #d4e0f0;
        }
        """,
    },

    # ── 4. Executive Gold ─────────────────────────────────────────────────────
    "Executive Gold": {
        "label": "✨ Executive Gold",
        "css": """
        :root {
            --app-bg:           #0c0c0c;
            --app-text:         #f0e6c8;
            --sidebar-bg:       #111111;
            --sidebar-border:   #2c2410;
            --sidebar-text:     #d4b96a;
            --sidebar-strong:   #f0c040;
            --card-bg:          #161410;
            --card-border:      #2c2410;
            --tab-list-bg:      #111111;
            --tab-list-border:  #2c2410;
            --tab-text:         #8a7a50;
            --tab-text-hover:   #f0e6c8;
            --tab-hover-bg:     #1c1a14;
            --tab-active-grad:  linear-gradient(90deg, #c8962a 0%, #a07820 100%);
            --tab-active-shadow:0 4px 14px rgba(200,150,42,0.4);
            --accent-grad:      linear-gradient(90deg, #c8962a 0%, #a07820 100%);
            --accent-shadow:    rgba(200,150,42,0.3);
            --btn-bg:           #161410;
            --btn-text:         #d4b96a;
            --btn-border:       #2c2410;
            --btn-hover-border: #f0c040;
            --btn-hover-text:   #f0c040;
            --btn-hover-bg:     #1c1a14;
            --input-bg:         #161410;
            --input-border:     #2c2410;
            --input-text:       #f0e6c8;
            --menu-bg:          #161410;
            --option-hover-bg:  #1c1a14;
            --tag-bg:           #c8962a;
            --expander-bg:      #161410;
            --expander-border:  #2c2410;
            --expander-text:    #f0e6c8;
            --expander-hover:   #f0c040;
            --metric-bg:        #161410;
            --metric-border:    #2c2410;
            --metric-label:     #8a7a50;
            --metric-value:     #f0e6c8;
            --heading-color:    #f0e6c8;
            --caption-color:    #6a5a30;
            --divider-color:    #2c2410;
            --scrollbar-track:  #111111;
            --scrollbar-thumb:  #2c2410;
            --scrollbar-hover:  #3c3418;
            --info-bg:          #161410;
            --success-bg:       #101608;
            --warning-bg:       #1c1408;
            --error-bg:         #1c0c0c;
            --alert-text:       #f0e6c8;
        }
        """,
    },
}

# Inject the active theme's CSS variables
_active_theme_css = THEMES[st.session_state.app_theme]["css"]
st.markdown(f"<style>{_active_theme_css}</style>", unsafe_allow_html=True)

# Apply all CSS vars to Streamlit elements via a universal variable-consumption block
st.markdown("""
<style>
/* ── Theme variable consumption ── */
.stApp,
.stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {
    background-color: var(--app-bg) !important;
    color: var(--app-text) !important;
}

[data-testid="stSidebar"],
section[data-testid="stSidebar"],
[data-testid="stSidebar"] > div {
    background-color: var(--sidebar-bg) !important;
    border-right-color: var(--sidebar-border) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] li {
    color: var(--sidebar-text) !important;
}
[data-testid="stSidebar"] strong {
    color: var(--sidebar-strong) !important;
}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="input"],
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div {
    background-color: var(--input-bg) !important;
    border-color: var(--input-border) !important;
    color: var(--input-text) !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] *,
div[data-baseweb="select"] * {
    color: var(--input-text) !important;
}
[data-testid="stSidebar"] [data-baseweb="option"],
[data-baseweb="option"] {
    background-color: var(--menu-bg) !important;
    color: var(--input-text) !important;
}
[data-testid="stSidebar"] [data-baseweb="option"]:hover,
[data-baseweb="option"]:hover {
    background-color: var(--option-hover-bg) !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: var(--tag-bg) !important;
}
[data-testid="stSidebar"] hr {
    border-color: var(--divider-color) !important;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--heading-color) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--tab-list-bg) !important;
    border-color: var(--tab-list-border) !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--tab-text) !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--tab-text-hover) !important;
    background: var(--tab-hover-bg) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--tab-active-grad) !important;
    box-shadow: var(--tab-active-shadow) !important;
    color: #ffffff !important;
}

[data-testid="metric-container"] {
    background: var(--metric-bg) !important;
    border-color: var(--metric-border) !important;
}
[data-testid="metric-container"] label {
    color: var(--metric-label) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--metric-value) !important;
}

[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
    border-color: var(--card-border) !important;
}

.stButton > button {
    background: var(--btn-bg) !important;
    color: var(--btn-text) !important;
    border-color: var(--btn-border) !important;
}
.stButton > button:hover {
    background: var(--btn-hover-bg) !important;
    border-color: var(--btn-hover-border) !important;
    color: var(--btn-hover-text) !important;
}
.stDownloadButton > button {
    background: var(--accent-grad) !important;
    box-shadow: 0 4px 10px var(--accent-shadow) !important;
}

[data-testid="stExpander"] {
    background: var(--expander-bg) !important;
    border-color: var(--expander-border) !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: var(--expander-text) !important;
}
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:hover p {
    color: var(--expander-hover) !important;
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background-color: var(--input-bg) !important;
    border-color: var(--input-border) !important;
    color: var(--input-text) !important;
}
[data-baseweb="select"] {
    background-color: var(--input-bg) !important;
    border-color: var(--input-border) !important;
}
[data-baseweb="menu"] {
    background-color: var(--menu-bg) !important;
    border-color: var(--input-border) !important;
}
[data-baseweb="option"] {
    background-color: var(--menu-bg) !important;
    color: var(--input-text) !important;
}
[data-baseweb="option"]:hover {
    background-color: var(--option-hover-bg) !important;
}
[data-baseweb="tag"] {
    background-color: var(--tag-bg) !important;
}

[data-testid="stCheckbox"] label,
[data-testid="stCheckbox"] p,
[data-testid="stCheckbox"] span,
[data-testid="stToggle"] label,
[data-testid="stToggle"] p,
[data-testid="stToggle"] span {
    color: var(--sidebar-text) !important;
}

.stCaption, [data-testid="stCaptionContainer"] * {
    color: var(--caption-color) !important;
}

::-webkit-scrollbar-track { background: var(--scrollbar-track) !important; }
::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb) !important; }
::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-hover) !important; }

hr { border-color: var(--divider-color) !important; }

[data-testid="stInfo"]    { background: var(--info-bg) !important; }
[data-testid="stSuccess"] { background: var(--success-bg) !important; }
[data-testid="stWarning"] { background: var(--warning-bg) !important; }
[data-testid="stError"]   { background: var(--error-bg) !important; }
[data-testid="stInfo"] p,    [data-testid="stInfo"] span,
[data-testid="stSuccess"] p, [data-testid="stSuccess"] span,
[data-testid="stWarning"] p, [data-testid="stWarning"] span,
[data-testid="stError"] p,   [data-testid="stError"] span {
    color: var(--alert-text) !important;
}

/* Sidebar media-query bg must also pick up theme */
@media (min-width: 1200px) {
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        border-right-color: var(--sidebar-border) !important;
    }
    [data-testid="stSidebar"] > div {
        background-color: var(--sidebar-bg) !important;
    }
}
@media (max-width: 1200px) {
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        border-right-color: var(--sidebar-border) !important;
    }
    [data-testid="stSidebar"] > div {
        background-color: var(--sidebar-bg) !important;
    }
}
</style>
""", unsafe_allow_html=True)



# ==============================================================================
# 4. Load data FIRST so sidebar options are available
# ==============================================================================

@st.cache_data(ttl=300)
def get_data():
    data = load_all()
    asgn = rules.apply_assignment_urgency(data["assignments"])
    asgn = rules.apply_worker_flags(asgn)
    asgn = rules.apply_recommended_actions(asgn)
    pos  = rules.apply_position_flags(data["open_positions"])
    act  = rules.apply_activity_flags(data["recruiter_activity"])
    asgn = rules.match_workers_to_positions(asgn, pos)
    wl   = rules.compute_recruiter_workload(asgn, pos, act)
    alrt = rules.build_alerts(asgn, pos, act, data["workers"])
    return dict(assignments=asgn, workers=data["workers"], open_positions=pos,
                recruiter_activity=act, clients=data["clients"],
                workload=wl, alerts=alrt, job_orders=data.get("job_orders", pd.DataFrame()))


@st.cache_data(ttl=300)
def get_customer_preview():
    return load_customer_import_preview()

with st.spinner("Loading data..."):
    D = get_data()
    CUSTOMER_PREVIEW = get_customer_preview()
    CUSTOMER_DASHBOARD_DATA = build_customer_dashboard_data(CUSTOMER_PREVIEW)

if st.session_state.data_source == "Customer Imports" and CUSTOMER_DASHBOARD_DATA is not None:
    D = CUSTOMER_DASHBOARD_DATA
    ACTIVE_DATA_SOURCE = "Customer Imports"
else:
    ACTIVE_DATA_SOURCE = "Demo Data"

asgn       = D["assignments"]
workers    = D["workers"]
pos        = D["open_positions"]
act        = D["recruiter_activity"]
clients    = D["clients"]
asgn       = rules.apply_assignment_urgency(asgn)
asgn       = rules.apply_worker_flags(asgn)
asgn       = rules.apply_recommended_actions(asgn)
pos        = rules.apply_position_flags(pos)
act        = rules.apply_activity_flags(act)
workload   = rules.compute_recruiter_workload(asgn, pos, act)
alerts     = rules.build_alerts(asgn, pos, act, workers)
job_orders = D.get("job_orders", pd.DataFrame())
TODAY      = pd.Timestamp.now().normalize()

# Apply session-state overrides to workers so matching engine gets live values
workers_live = apply_worker_overrides(workers, st.session_state.worker_overrides)

# Prepend newly parsed mock workers from Advanced Demo Mode
if "added_workers" in st.session_state and st.session_state.added_workers:
    new_df = pd.DataFrame(st.session_state.added_workers)
    # Ensure all columns exist and match
    for col in workers_live.columns:
        if col not in new_df.columns:
            new_df[col] = None
    new_df = new_df[workers_live.columns]
    workers_live = pd.concat([new_df, workers_live], ignore_index=True)

# Apply session-state overrides to positions so everything gets live values
pos_live = apply_position_overrides(pos, st.session_state.position_overrides)
pos = rules.apply_position_flags(pos_live)

# Recalculate workload, alerts, and assignments matching based on live position overrides
asgn = rules.match_workers_to_positions(asgn, pos)
workload = rules.compute_recruiter_workload(asgn, pos, act)
alerts = rules.build_alerts(asgn, pos, act, workers_live)

# Pre-compute option lists from real data
OPT_RECRUITERS = sorted(asgn["recruiter_owner"].dropna().unique().tolist())
OPT_CLIENTS    = sorted(asgn["client_name"].dropna().unique().tolist())
OPT_TRADES     = sorted(asgn["trade_category"].dropna().unique().tolist())
OPT_URGENCIES  = ["Critical", "Red", "Orange", "Yellow", "Green"]
OPT_STAGES     = sorted(pos["stage"].dropna().unique().tolist())
OPT_PRIORITIES = ["High", "Medium", "Low"]
OPT_REC_WB     = ["All Recruiters"] + sorted(workload["recruiter"].tolist())

# Job order scenario labels
if not job_orders.empty:
    JO_OPTIONS = {
        f"{row.job_order_id} — {row.role} ({row.client_state})": row.job_order_id
        for row in job_orders.itertuples(index=False)
    }
else:
    JO_OPTIONS = {}


# ==============================================================================
# 4. Sidebar — branding + filters (options now populated from real data)
# ==============================================================================

with st.sidebar:
    if st.button("Sign out", use_container_width=True):
        st.session_state.demo_authenticated = False
        st.rerun()

    st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

    # ── Theme Selector (always at the very top) ──────────────────────
    theme_labels = [THEMES[k]["label"] for k in THEMES]
    theme_keys   = list(THEMES.keys())
    current_idx  = theme_keys.index(st.session_state.app_theme)
    chosen_label = st.selectbox(
        "🎨 App Theme",
        options=theme_labels,
        index=current_idx,
        key="theme_selector",
    )
    chosen_key = theme_keys[theme_labels.index(chosen_label)]
    if chosen_key != st.session_state.app_theme:
        st.session_state.app_theme = chosen_key
        st.rerun()

    customer_ready = CUSTOMER_DASHBOARD_DATA is not None
    data_options = ["Customer Imports", "Demo Data"] if customer_ready else ["Demo Data"]
    if st.session_state.data_source not in data_options:
        st.session_state.data_source = data_options[0]
    data_source = st.radio(
        "Data Source",
        data_options,
        index=data_options.index(st.session_state.data_source),
        key="data_source",
        help="Customer Imports uses the local customer spreadsheets/PDF in the data folder. Demo Data uses the generated CSV dataset.",
    )
    if data_source == "Customer Imports":
        st.caption("Main dashboard is populated from the imported customer files.")
    else:
        st.caption("Main dashboard is populated from generated demo CSVs.")

    mode = st.radio(
        "Demo Navigation",
        ["Client Demo Mode", "Full Prototype Mode"],
        index=0 if st.session_state.presentation_mode == "Client Demo Mode" else 1,
        key="presentation_mode",
        help="Client Demo Mode shows only the start page and the four first-meeting screens. Full Prototype Mode restores every prototype page.",
    )
    demo_mode = mode == "Client Demo Mode"
    st.caption(
        "Showing the guided first-meeting flow."
        if demo_mode else
        "Showing all prototype, admin, and future-expansion areas."
    )

    st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)
    source_badge = "CUSTOMER IMPORTS" if ACTIVE_DATA_SOURCE == "Customer Imports" else "DEMO DATA"

    st.markdown(f"""
    <div style="text-align:center;padding:12px 0 8px 0;">
        <div style="font-size:2.2rem;">⚙️</div>
        <div style="font-size:1.15rem;font-weight:800;background:var(--accent-grad, linear-gradient(90deg, #1b5f8b 0%, #0e7fb5 100%));-webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.3;">
            Trades Resource
        </div>
        <div style="font-size:0.7rem;color:var(--caption-color,#475569);font-weight:700;margin-top:2px;letter-spacing:0.5px;text-transform:uppercase;">Command Center</div>
        <div style="margin-top:4px;font-size:0.68rem;color:#64748b;font-style:italic;line-height:1.2;">
            "Forecasting so the owner can focus on sales."
        </div>
        <div style="margin-top:6px;font-size:0.72rem;color:#334155;line-height:1.4;">
            Replacing spreadsheet, paper, and memory-based tracking with one operations command center.
        </div>
        <div style="margin-top:8px;display:inline-block;background:#FEF3C7;
             border:1px solid #FDE68A;border-radius:4px;padding:2px 10px;
             font-size:0.68rem;color:#92400E;font-weight:700;letter-spacing:1px;">
            PROTOTYPE - {source_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"Today: {datetime.now().strftime('%B %d, %Y')}")
    st.divider()

    # ── Timeline (Page 2) ──────────────────────────────────────────────────────
    st.markdown("**📅 TIMELINE FILTERS**")
    tl_recruiters = st.multiselect("Recruiter",     OPT_RECRUITERS, key="tl_rec")
    tl_clients    = st.multiselect("Client",         OPT_CLIENTS,   key="tl_client")
    tl_trades     = st.multiselect("Trade Category", OPT_TRADES,    key="tl_trade")
    tl_urgencies  = st.multiselect("Urgency",        OPT_URGENCIES, key="tl_urgency")
    tl_end_within = st.selectbox("Ending Within",
                        ["All", "7 Days", "14 Days", "30 Days", "60 Days"],
                        key="tl_end_within")
    st.divider()

    # ── Open Positions (Page 3) ────────────────────────────────────────────────
    st.markdown("**📋 POSITION FILTERS**")
    pos_priorities = st.multiselect("Priority",  OPT_PRIORITIES, key="pos_priority")
    pos_stages_sel = st.multiselect("Stage",     OPT_STAGES,     key="pos_stage")
    pos_rec_sel    = st.multiselect("Recruiter", OPT_RECRUITERS, key="pos_rec")
    pos_stuck_only = st.checkbox("Stuck Positions Only", key="pos_stuck")
    st.divider()

    # ── Recruiter Workboard (Page 4) ───────────────────────────────────────────
    st.markdown("**👥 RECRUITER VIEW**")
    wb_recruiter = st.selectbox("Drill into recruiter", OPT_REC_WB, key="wb_rec")
    st.divider()

    # ── Redeployment (Page 5) ──────────────────────────────────────────────────
    st.markdown("**🔄 REDEPLOYMENT**")
    rd_horizon     = st.selectbox("Ending Within",
                        ["30 Days", "60 Days", "90 Days", "All"], key="rd_horizon")
    rd_not_started = st.checkbox("Not Started Only", key="rd_ns")
    st.divider()

    # ── AI Assist (Candidate Matching / Submittal) ────────────────────────────
    st.markdown("**🤖 AI ASSIST**")
    available_models = list_ollama_models()
    model_opts  = available_models or [DEFAULT_OLLAMA_MODEL]
    st.selectbox("Local LLM Model", model_opts,
                 key="llm_model",
                 help="Used in Candidate Matching and Submittal tabs. Requires Ollama running locally.")
    st.toggle("Enable AI Assist", key="use_ai_assist",
              help="Generates LLM-assisted requirement briefs, recruiter digest, and submittal drafts.")
    ai_status = (
        f"Ollama: {st.session_state.llm_model}" if st.session_state.use_ai_assist
        else "Deterministic mode (no LLM)"
    )
    st.caption(ai_status)


# ==============================================================================
# 5. Utilities
# ==============================================================================

_ck = {"n": 0}
def ckey(name: str) -> str:
    _ck["n"] += 1
    return f"{name}_{_ck['n']}"

def fmt_dates(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns and pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return df


# ---------------------------------------------------------------------------
# Dialog for unblocking open positions
# ---------------------------------------------------------------------------
@st.dialog("Unblock Open Position")
def show_unblock_dialog(row_dict):
    st.markdown(f"### Update Details for **{row_dict['role']}**")
    st.caption(f"Client: {row_dict['client_name']} · ID: {row_dict['position_id']}")
    st.divider()
    
    with st.form("unblock_form"):
        st.markdown("**Stuck Reason:**")
        st.warning(row_dict['stuck_reason'])
        
        # Checkbox to toggle intake complete (a primary stuck trigger)
        intake_val = bool(row_dict.get('intake_complete', True))
        new_intake = st.checkbox("Intake Form Completed", value=intake_val, 
                                 help="If unchecked, position is marked as Stuck (Intake Incomplete).")
        
        # Selectbox to update stage
        stages_list = [
            "New Intake", "Intake Incomplete", "Sourcing", "Candidates Identified",
            "Submitted to Client", "Interviewing", "Offer / Confirmation", "On Hold", "Filled"
        ]
        curr_stage = row_dict.get('stage', 'Sourcing')
        stage_idx = stages_list.index(curr_stage) if curr_stage in stages_list else 2
        new_stage = st.selectbox("Stage", stages_list, index=stage_idx)
        
        # Selectbox to update priority
        priorities_list = ["High", "Medium", "Low"]
        curr_pri = row_dict.get('priority', 'Medium')
        pri_idx = priorities_list.index(curr_pri) if curr_pri in priorities_list else 1
        new_priority = st.selectbox("Priority", priorities_list, index=pri_idx)
        
        # Text area to write resolution notes
        curr_notes = row_dict.get('notes', '')
        new_notes = st.text_area("Resolution / Action Taken Notes", value=str(curr_notes) if pd.notna(curr_notes) else "")
        
        st.markdown("<br>", unsafe_allow_html=True)
        save = st.form_submit_button("Save & Unblock")
        if save:
            st.session_state.position_overrides = update_position_override(
                st.session_state.position_overrides,
                row_dict['position_id'],
                {"intake_complete": new_intake, "stage": new_stage, "priority": new_priority, "notes": new_notes}
            )
            st.success("Position successfully unblocked and updated!")
            st.rerun()


# ==============================================================================
# 6. Tabs
# ==============================================================================

if demo_mode:
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] [data-baseweb="tab"]:nth-of-type(n+6) {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🎯 Demo Start",
    "🏠 Owner Today View",
    "📅 Assignment Forecast",
    "📋 Open Orders Board",
    "👥 Recruiter Process Tracker",
    "🔍 Candidate Matching ›",
    "🔄 Redeployment ›",
    "📤 Submittal Packets ›",
    "🗄️ Data / Admin",
    "🚀 Demo Simulators",
])


# ██████████████████████████████████████████████████████████████████████████████
# PAGE 1 — TODAY DASHBOARD
# ██████████████████████████████████████████████████████████████████████████████

with tab0:
    components.page_banner(
        "Trades Resource Demo Start",
        "A guided first-meeting flow built around forecasting, follow-through, and freeing the owner to focus on sales.",
        "🎯",
        decision_label="Start here: spreadsheet + paper + memory to one operational command center"
    )

    st.markdown("""
    <div style="background:var(--card-bg,#ffffff);border:1px solid var(--card-border,#e2e8f0);
         border-radius:8px;padding:18px 20px;margin-bottom:18px;">
        <div style="font-size:0.78rem;font-weight:800;color:var(--caption-color,#64748b);
             text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px;">Positioning</div>
        <div style="font-size:1.3rem;font-weight:800;color:var(--heading-color,#0f172a);line-height:1.25;">
            Forecasting so the owner can focus on sales.
        </div>
        <div style="font-size:0.94rem;color:var(--app-text,#334155);line-height:1.55;margin-top:8px;">
            This prototype shows how active assignments, open orders, recruiter updates, renewals,
            extensions, time off, and client follow-ups can move from spreadsheet + paper + memory
            into one daily command center.
        </div>
    </div>
    """, unsafe_allow_html=True)

    components.render_kpi_row([
        {"label": "Demo Screens", "value": 4, "color": "#1E88E5", "sub": "Keep the first meeting focused"},
        {"label": "Core Pain Points", "value": 4, "color": "#8E24AA", "sub": "Assignments, orders, workflow, forecasting"},
        {"label": "Suggested Ask", "value": "1", "color": "#43A047", "sub": "Which area creates value first?"},
    ])

    components.section_header("First-Meeting Flow", "Use these screens in order; leave the rest for future expansion.", "🧭")
    flow_cards = [
        {"Step": "1", "Screen": "Owner Today View", "Shows": "What needs attention today, what can be delegated, and where the owner can safely focus on sales.", "Talking Point": "This replaces memory-based tracking with a daily action queue."},
        {"Step": "2", "Screen": "Assignment Forecast", "Shows": "A Gantt-style view of assignments, renewals, extensions, ending dates, and time off.", "Talking Point": "This helps you see what is coming before it turns into a fire."},
        {"Step": "3", "Screen": "Open Orders Board", "Shows": "Every open order, submitted candidates, approval status, client feedback, and next action.", "Talking Point": "This replaces paper order tracking with one board."},
        {"Step": "4", "Screen": "Recruiter Process Tracker", "Shows": "Required-field completion, proficiency status, candidate readiness, and recruiter workload.", "Talking Point": "This creates process visibility without micromanagement."},
    ]
    st.markdown(
        components.render_styled_table(pd.DataFrame(flow_cards), badge_cols=["Step"], column_names={}),
        unsafe_allow_html=True,
    )

    components.section_header("Three Demo Stories", "Anchor the walkthrough in realistic moments instead of a feature tour.", "🎬")
    story1, story2, story3 = st.columns(3)
    with story1:
        st.markdown("""
        <div style="background:var(--card-bg,#ffffff);border:1px solid var(--card-border,#e2e8f0);border-radius:8px;padding:16px;min-height:190px;">
            <div style="font-weight:800;color:#1E88E5;margin-bottom:6px;">Assignment Ending Soon</div>
            <div style="font-size:0.88rem;color:var(--app-text,#334155);line-height:1.5;">
                Jason is ending in 7 days. The system flags the risk, shows extension status,
                shows whether the client was contacted, and points to the next action.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with story2:
        st.markdown("""
        <div style="background:var(--card-bg,#ffffff);border:1px solid var(--card-border,#e2e8f0);border-radius:8px;padding:16px;min-height:190px;">
            <div style="font-weight:800;color:#FB8C00;margin-bottom:6px;">Open Order Stuck</div>
            <div style="font-size:0.88rem;color:var(--app-text,#334155);line-height:1.5;">
                A CNC role has been open for 9 days with no submitted candidates.
                The board flags it as stuck and makes the required follow-up obvious.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with story3:
        st.markdown("""
        <div style="background:var(--card-bg,#ffffff);border:1px solid var(--card-border,#e2e8f0);border-radius:8px;padding:16px;min-height:190px;">
            <div style="font-weight:800;color:#8E24AA;margin-bottom:6px;">Incomplete Recruiter Process</div>
            <div style="font-size:0.88rem;color:var(--app-text,#334155);line-height:1.5;">
                A candidate is nearly ready, but pay rate and availability are missing.
                The tracker catches it before an incomplete profile goes to a client.
            </div>
        </div>
        """, unsafe_allow_html=True)

    components.section_header("Close With This Question", "Move the conversation toward the first paid production slice.", "✅")
    st.info(
        "Of these four areas, which would create the most value first if we turned the prototype into a real working system?",
        icon="💬",
    )

    with st.expander("What We Would Need From Trades Resource", expanded=False):
        st.markdown("""
- Current active assignment spreadsheet
- Current open orders list
- Candidate / recruiter process spreadsheet
- Technical job intake document
- Current proficiency testing process
- Required fields for candidates and job orders
- Desired alert timing for renewals, extensions, time off, and follow-ups
- Existing tools currently used, such as spreadsheets, email, ATS, CRM, calendar, or accounting system
        """)


with tab1:
    components.page_banner(
        "Owner Today View",
        "What needs attention today? Active assignments · Open orders · Renewals · Extensions · Time off · Candidate approvals · Recruiter updates",
        "🏠",
        decision_label="Helps answer: \"What needs attention today — and what can I safely focus on sales?\""
    )

    # ── Prototype disclaimer ──────────────────────────────────────────────────
    source_note_title = "Customer Import Preview" if ACTIVE_DATA_SOURCE == "Customer Imports" else "Demo Data Only"
    source_note_body = (
        "This local view is populated from the customer files in the data folder. Review mappings before using this as production truth."
        if ACTIVE_DATA_SOURCE == "Customer Imports"
        else "This concept prototype uses generated demo data to show what the workflow could look like. A production version would connect to your real spreadsheets, database, or existing tools."
    )
    st.markdown(f"""
    <div style="background:#FEF9EC;border:1px solid #FDE68A;border-left:5px solid #F59E0B;
         border-radius:8px;padding:12px 18px;margin-bottom:12px;">
        <span style="font-weight:700;color:#92400E;font-size:0.88rem;">PROTOTYPE - {source_note_title}</span>
        <span style="color:#78350F;font-size:0.84rem;margin-left:8px;">
        {source_note_body}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── What This Solves intro ─────────────────────────────────────────────────
    with st.expander("📌 What This Prototype Solves — Click to read", expanded=False):
        st.markdown("""
**This prototype is built around four confirmed pain points:**

1. **Active assignments** are currently tracked in spreadsheets
2. **Open orders** are currently tracked on paper and memory
3. **Recruiter workflow** is difficult to monitor consistently
4. **Forecasting renewals, extensions, time off, and redeployment** takes too much owner attention

**The goal is one command center showing:**
- Who is currently assigned and when assignments end
- Which assignments need renewal or extension follow-up
- Who has upcoming time off, and whether the client has been notified
- Which open orders need candidates or client approval
- Which recruiter process steps are incomplete
- What the owner should focus on today vs. what can be delegated

**What this system is not trying to do:**
- Replace recruiter judgment or client relationships
- Fully automate recruiting
- Monitor employees in a punitive way
- Lock the company into a complicated software platform before the process is clear

> The goal is visibility, consistency, forecasting, and better follow-through — so the owner can spend more time on sales.
        """)

    active_count      = int(len(asgn[asgn["status"] == "Active"]))
    open_count        = int(len(pos[~pos["stage"].isin(["Filled", "On Hold"])]))
    ending_7          = int(len(asgn[asgn["days_remaining"].between(0, 7)]))
    ending_14         = int(len(asgn[asgn["days_remaining"].between(0, 14)]))
    ending_30         = int(len(asgn[asgn["days_remaining"].between(0, 30)]))
    critical_count    = int(len(asgn[asgn["urgency"] == "Critical"]))
    overdue_actions   = int(act["is_overdue"].sum()) if "is_overdue" in act.columns else 0
    high_priority_pos = int(len(pos[pos["priority"] == "High"]))
    stuck_positions   = int(pos["is_stuck"].sum()) if "is_stuck" in pos.columns else 0
    checkin_needed    = int(asgn["checkin_needed"].sum()) if "checkin_needed" in asgn.columns else 0

    # Expanded Forecasting KPI calculations
    ext_pending       = int((asgn["extension_status"] == "Extension pending").sum())
    time_off_upcoming = int((asgn["time_off_start"].astype(str).str.strip() != "").sum())
    approvals_pending = int((pos["approval_status"] == "Pending Client Review").sum())
    missing_updates   = int((workers_live["candidate_fields_complete"] == False).sum())
    urgent      = asgn[asgn["urgency"].isin(["Critical", "Red"])].sort_values("days_remaining")
    overdue_act = act[act["is_overdue"]] if "is_overdue" in act.columns else pd.DataFrame()
    total_urgent = len(urgent) + len(overdue_act)

    if demo_mode:
        components.render_kpi_row([
            {"label": "Needs Attention",     "value": total_urgent, "color": "#E53935", "sub": "Start here"},
            {"label": "Renewals Due",        "value": ending_7,        "color": "#FB8C00", "sub": "Protect revenue"},
            {"label": "Extensions Pending",  "value": ext_pending,     "color": "#1E88E5", "sub": "Client decisions"},
            {"label": "Time Off Upcoming",   "value": time_off_upcoming,"color": "#8E24AA", "sub": "Forecast coverage"},
            {"label": "Open Orders Action",  "value": stuck_positions,  "color": "#FDD835", "sub": "Unblock recruiting"},
        ])
    else:
        components.render_kpi_row([
            {"label": "Active Assignments",   "value": active_count,    "color": "#1E88E5"},
            {"label": "Open Positions",       "value": open_count,      "color": "#8E24AA"},
            {"label": "Renewals Due This Wk", "value": ending_7,        "color": "#E53935"},
            {"label": "Extensions Pending",   "value": ext_pending,     "color": "#FB8C00"},
            {"label": "Time Off Upcoming",    "value": time_off_upcoming,"color": "#1E88E5"},
        ])
        components.render_kpi_row([
            {"label": "Ending in 14 Days",    "value": ending_14,       "color": "#FB8C00"},
            {"label": "Approvals Pending",    "value": approvals_pending,"color": "#FDD835"},
            {"label": "Missing Updates",      "value": missing_updates,  "color": "#E53935"},
            {"label": "Stuck Positions",      "value": stuck_positions,  "color": "#FB8C00"},
            {"label": "Need Check-In",        "value": checkin_needed,   "color": "#FDD835"},
        ])

    # A — Urgent Actions
    components.section_header("A. Urgent Actions Today",
                               "Assignments and tasks needing attention right now.", "🚨")
    with st.expander(f"⚠️ View Urgent Actions Checklist ({total_urgent} items)", expanded=(total_urgent > 0)):
        if urgent.empty and overdue_act.empty:
            st.success("No urgent actions right now — you're in great shape!")
        else:
            for _, row in urgent.iterrows():
                components.alert_row("Assignment",
                    subject=f"{row['worker_name']} → {row['role']} @ {row['client_name']}",
                    detail=f"Ends {str(row['end_date'])[:10]} · {row['days_remaining']} days remaining",
                    action=row["recommended_action"],
                    severity=row["urgency"],
                    recruiter=row["recruiter_owner"])
            for _, row in overdue_act.iterrows():
                components.alert_row("Overdue Task",
                    subject=f"{row['recruiter_name']} — {row['activity_type']}",
                    detail=f"Due: {str(row.get('due_date',''))[:10]}",
                    action=str(row.get("next_action", "Follow up immediately")),
                    severity="Red",
                    recruiter=row["recruiter_name"])

    # B — Ending Soon
    components.section_header("B. Owner Sales Focus",
                               "What can be delegated vs. what needs your attention right now.", "🎯")
    with st.expander("View Owner Sales Focus Summary", expanded=True):
        stable_count    = int(len(asgn[(asgn["status"] == "Active") & (asgn["days_remaining"] > 30)]))
        renewals_week   = int(len(asgn[asgn["days_remaining"].between(0, 7)]))
        ext_pending_sf  = int((asgn["extension_status"] == "Extension pending").sum())
        avail_soon      = int(len(asgn[asgn["days_remaining"].between(0, 30)]))
        urgent_orders   = int(len(pos[pos["priority"] == "High"]))
        missing_updates_sf = int((workers_live.get("candidate_fields_complete", pd.Series(dtype=bool)) == False).sum()) if "candidate_fields_complete" in workers_live.columns else 0

        sf_data = [
            {"Category": "Stable Assignments", "Count": stable_count, "Meaning": "No owner attention needed - safe to focus on sales"},
            {"Category": "Renewals Due This Week", "Count": renewals_week, "Meaning": "Protect existing revenue - follow up on ending assignments"},
            {"Category": "Extensions Pending", "Count": ext_pending_sf, "Meaning": "Client decision needed - follow up to confirm extension"},
            {"Category": "Workers Available Soon", "Count": avail_soon, "Meaning": "Redeployment opportunity - begin next placement planning"},
            {"Category": "Urgent Open Orders", "Count": urgent_orders, "Meaning": "Recruiting and sales priority - needs candidate sourcing"},
            {"Category": "Missing Recruiter Updates", "Count": missing_updates_sf, "Meaning": "Process issue to clean up - incomplete candidate records"},
        ]
        st.markdown(
            components.render_styled_table(pd.DataFrame(sf_data), badge_cols=[], column_names={}),
            unsafe_allow_html=True
        )
        st.caption("This view helps the owner know what can be delegated, what needs attention, and where she can safely focus on sales.")

    ending_soon = asgn[asgn["days_remaining"].between(0, 30)].sort_values("days_remaining")
    
    if not demo_mode:
        components.section_header("C. Assignments Ending Soon",
                                   "Workers whose assignments end in the next 30 days.", "📅")
        with st.expander(f"⏳ View Ending Assignments ({len(ending_soon)} workers)", expanded=False):
            if ending_soon.empty:
                st.info("No assignments ending in the next 30 days.")
            else:
                show = fmt_dates(ending_soon[[
                    "worker_name", "client_name", "role", "recruiter_owner",
                    "end_date", "days_remaining", "urgency",
                    "redeployment_status", "recommended_action"
                ]], ["end_date"])
                st.dataframe(show, width="stretch", height=280)

    # C — Stuck Positions
    stuck = (pos[pos["is_stuck"]].sort_values("priority",
             key=lambda x: x.map({"High": 0, "Medium": 1, "Low": 2}))
             if "is_stuck" in pos.columns else pd.DataFrame())

    if not demo_mode:
        components.section_header("D. Stuck Open Positions",
                                   "Positions that are stalled and need immediate attention.", "🚧")
        with st.expander(f"🛑 View Stuck & Blocked Positions ({len(stuck)} positions)", expanded=(len(stuck) > 0)):
            if stuck.empty:
                st.success("No stuck positions right now.")
            else:
                for _, row in stuck.iterrows():
                    col_alert, col_btn = st.columns([5, 1])
                    with col_alert:
                        components.alert_row("Open Position",
                            subject=f"{row['role']} @ {row['client_name']}",
                            detail=f"Stage: {row['stage']} · Open {row['days_open']}d · {row['stuck_reason']}",
                            action="Review and unblock",
                            severity="Orange" if row["priority"] == "High" else "Yellow",
                            recruiter=row["recruiter_owner"])
                    with col_btn:
                        st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)
                        if st.button("Unblock", key=f"unblock_dash_{row['position_id']}"):
                            show_unblock_dialog(row.to_dict())

    # D — Recruiter Summary
    if not demo_mode:
        components.section_header("E. Recruiter Workload Summary", "", "👥")
        with st.expander("📊 View Recruiter Workloads & Operations Charts", expanded=False):
            st.dataframe(
                workload[["recruiter", "open_positions", "active_assignments",
                          "ending_soon", "overdue_actions", "workload_score", "workload_label"]],
                width="stretch", height=200,
            )

            col_a, col_b = st.columns(2)
            with col_a:
                st.plotly_chart(charts.build_endings_by_week(asgn),
                                width="stretch", key=ckey("endings_week"))
            with col_b:
                st.plotly_chart(charts.build_overdue_by_recruiter(act),
                                width="stretch", key=ckey("overdue_rec_dash"))

    # E — Owner Sales Focus
    if not demo_mode:
        components.section_header("Owner Sales Focus Detail",
                                   "What can be delegated vs. what needs your attention right now.", "🎯")
        with st.expander("📊 View Owner Sales Focus Summary", expanded=False):
            st.caption("This repeats the higher-priority sales-focus summary for people who scroll the full Today dashboard.")
            # Compute sales focus metrics
            stable_count    = int(len(asgn[(asgn["status"] == "Active") & (asgn["days_remaining"] > 30)]))
            renewals_week   = int(len(asgn[asgn["days_remaining"].between(0, 7)]))
            ext_pending_sf  = int((asgn["extension_status"] == "Extension pending").sum())
            avail_soon      = int(len(asgn[asgn["days_remaining"].between(0, 30)]))
            urgent_orders   = int(len(pos[pos["priority"] == "High"]))
            missing_updates_sf = int((workers_live.get("candidate_fields_complete", pd.Series(dtype=bool)) == False).sum()) if "candidate_fields_complete" in workers_live.columns else 0

            sf_data = [
                {"Category": "Stable Assignments",     "Count": stable_count,    "Meaning": "No owner attention needed — safe to focus on sales"},
                {"Category": "Renewals Due This Week",  "Count": renewals_week,   "Meaning": "Protect existing revenue — follow up on ending assignments"},
                {"Category": "Extensions Pending",      "Count": ext_pending_sf,  "Meaning": "Client decision needed — follow up to confirm extension"},
                {"Category": "Workers Available Soon",  "Count": avail_soon,      "Meaning": "Redeployment opportunity — begin next placement planning"},
                {"Category": "Urgent Open Orders",      "Count": urgent_orders,   "Meaning": "Recruiting and sales priority — needs candidate sourcing"},
                {"Category": "Missing Recruiter Updates","Count": missing_updates_sf, "Meaning": "Process issue to clean up — incomplete candidate records"},
            ]
            sf_df = pd.DataFrame(sf_data)
            sf_html = components.render_styled_table(sf_df, badge_cols=[], column_names={})
            st.markdown(sf_html, unsafe_allow_html=True)
            st.caption("This view helps the owner know what can be delegated, what needs attention, and where she can safely focus on sales.")

    # F — Renewal & Extension Forecast
    renewal_section_title = "C. Renewal & Extension Forecast" if demo_mode else "F. Renewal & Extension Forecast"
    components.section_header(renewal_section_title,
                               "Assignments ending soon that need a renewal conversation or extension decision.", "🔄")
    with st.expander(f"📆 View Renewal & Extension Forecast ({len(asgn[asgn['days_remaining'].between(-30, 30)])} assignments in window)", expanded=False):
        renewal_window = asgn[asgn["days_remaining"].between(-30, 45)].copy()
        if renewal_window.empty:
            st.info("No assignments in the 45-day renewal window.")
        else:
            def renewal_alert(row):
                days = row.get("days_remaining", 999)
                ext_status = str(row.get("extension_status", "")).strip()
                if pd.isna(days): days = 999
                if days <= 7 and ext_status not in ["Extended", "Extension confirmed"]:
                    return "🔴 Critical forecast risk"
                if days <= 14 and ext_status in ["", "Unknown", "Extension pending"]:
                    return "🟠 Urgent extension follow-up"
                if days <= 30 and ext_status in ["", "Unknown"]:
                    return "🟡 Renewal review needed"
                if ext_status in ["Extended", "Extension confirmed"]:
                    return "🟢 Extension confirmed"
                return "ℹ️ Monitor"
            renewal_window["Renewal Alert"] = renewal_window.apply(renewal_alert, axis=1)
            # Compute renewal_conv_due as 14 days before end
            if "end_date" in renewal_window.columns:
                try:
                    renewal_window["Renewal Conv. Due"] = pd.to_datetime(renewal_window["end_date"]) - pd.Timedelta(days=14)
                    renewal_window["Renewal Conv. Due"] = renewal_window["Renewal Conv. Due"].dt.strftime("%Y-%m-%d")
                except Exception:
                    renewal_window["Renewal Conv. Due"] = ""
            else:
                renewal_window["Renewal Conv. Due"] = ""
            renewal_cols = {
                "worker_name": "Worker",
                "client_name": "Client",
                "end_date": "Assignment End",
                "Renewal Conv. Due": "Renewal Conv. Due",
                "extension_status": "Extension Status",
                "extension_possible": "Extension Likelihood",
                "worker_interest_confirmed": "Worker Interest Confirmed",
                "recruiter_owner": "Recruiter",
                "recommended_action": "Next Action",
                "Renewal Alert": "Renewal Alert",
            }
            disp_r = renewal_window[[c for c in renewal_cols.keys() if c in renewal_window.columns]].copy()
            for dc in ["end_date"]:
                if dc in disp_r.columns:
                    try:
                        disp_r[dc] = pd.to_datetime(disp_r[dc]).dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass
            renewal_html = components.render_styled_table(
                disp_r,
                badge_cols=["Extension Status", "Renewal Alert"],
                column_names=renewal_cols
            )
            st.markdown(renewal_html, unsafe_allow_html=True)
            components.csv_download_button(disp_r.rename(columns=renewal_cols), "renewal_extension_forecast.csv", "⬇ Download Renewal Forecast")

    # G — Upcoming Time Off
    time_off_section_title = "D. Upcoming Time Off" if demo_mode else "G. Upcoming Time Off"
    components.section_header(time_off_section_title,
                               "Workers with scheduled time off — check client notification and coverage status.", "🏖️")
    with st.expander("🗓️ View Upcoming Time Off", expanded=False):
        to_mask = asgn["time_off_start"].astype(str).str.strip().apply(
            lambda x: x not in ["", "NaT", "nan", "<NA>", "None", "None"]
        ) if "time_off_start" in asgn.columns else pd.Series([False] * len(asgn))
        time_off_df = asgn[to_mask].copy()
        if time_off_df.empty:
            st.info("No upcoming time off records in demo data.")
        else:
            def to_alert(row):
                to_start_val = str(row.get("time_off_start", "")).strip()
                notified = str(row.get("client_notified_of_time_off", "")).strip().lower()
                coverage = str(row.get("coverage_needed", "")).strip().lower()
                try:
                    to_date = pd.to_datetime(to_start_val)
                    days_out = (to_date - TODAY).days
                    if days_out <= 7 and coverage in ["yes", "true", "1"]:
                        return "🔴 Urgent — coverage needed"
                    if days_out <= 14 and notified not in ["yes", "true", "1"]:
                        return "🟠 Client not notified"
                    return "🟡 Monitor"
                except Exception:
                    return "ℹ️ Check dates"
            time_off_df["Time-Off Alert"] = time_off_df.apply(to_alert, axis=1)

            # Calc days off
            try:
                time_off_df["Days Off"] = (
                    pd.to_datetime(time_off_df["time_off_end"]) - pd.to_datetime(time_off_df["time_off_start"])
                ).dt.days.fillna(0).astype(int)
            except Exception:
                time_off_df["Days Off"] = ""

            to_cols = {
                "worker_name": "Worker",
                "client_name": "Client",
                "role": "Role",
                "time_off_start": "Time Off Start",
                "time_off_end": "Time Off End",
                "Days Off": "Days Off",
                "client_notified_of_time_off": "Client Notified",
                "coverage_needed": "Coverage Needed",
                "time_off_status": "Approval Status",
                "recruiter_owner": "Recruiter",
                "Time-Off Alert": "Alert",
            }
            disp_to = time_off_df[[c for c in to_cols.keys() if c in time_off_df.columns]].copy()
            for dc in ["time_off_start", "time_off_end"]:
                if dc in disp_to.columns:
                    try:
                        disp_to[dc] = pd.to_datetime(disp_to[dc]).dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass
            to_html = components.render_styled_table(
                disp_to,
                badge_cols=["Approval Status", "Alert"],
                column_names=to_cols
            )
            st.markdown(to_html, unsafe_allow_html=True)
            components.csv_download_button(disp_to.rename(columns=to_cols), "upcoming_time_off.csv", "⬇ Download Time Off Report")

    # H — Bench Signals (collapsed, lower priority)
    if not demo_mode:
        components.section_header("H. Bench Depth Signals",
                                   "Available worker pool health for rapid deployment.", "📊")
        with st.expander("🔍 View Bench Signals & Placement Recommendations", expanded=False):
            try:
                _req_for_bench = st.session_state.requirements
                _avail_workers = workers_live[
                    workers_live["trade_category"].isin(["CNC", "Tooling", "Quality"])
                ] if "trade_category" in workers_live.columns else workers_live.head(0)
                if not _avail_workers.empty:
                    _bench_scored = score_all_workers(_avail_workers, _req_for_bench)
                    _bench        = build_bench_insights(_avail_workers, _bench_scored)
                    col_bi, col_brec = st.columns([1, 1])
                    with col_bi:
                        st.dataframe(_bench["role_depth"], width="stretch", height=220)
                    with col_brec:
                        for rec in _bench["recommendations"]:
                            st.markdown(f"- {rec}")
                else:
                    st.caption("Bench signals available once workers have skill data.")
            except Exception:
                st.caption("Bench signals will appear after the matching engine scores workers.")


# ██████████████████████████████████████████████████████████████████████████████
# PAGE 2 — ASSIGNMENT TIMELINE
# ██████████████████████████████████████████████████████████████████████████████

with tab2:
    components.page_banner(
        "Active Assignment Forecast",
        "Gantt-style timeline showing assignments, renewals, extensions, and time off. See what's coming before it becomes urgent.",
        "📅",
        decision_label="Helps answer: \"Which assignments may create revenue, staffing, or redeployment risk?\""
    )

    # Apply sidebar filters
    filtered = asgn.copy()
    if tl_recruiters:
        filtered = filtered[filtered["recruiter_owner"].isin(tl_recruiters)]
    if tl_clients:
        filtered = filtered[filtered["client_name"].isin(tl_clients)]
    if tl_trades:
        filtered = filtered[filtered["trade_category"].isin(tl_trades)]
    if tl_urgencies:
        filtered = filtered[filtered["urgency"].isin(tl_urgencies)]
    if tl_end_within != "All":
        dm = {"7 Days": 7, "14 Days": 14, "30 Days": 30, "60 Days": 60}
        filtered = filtered[filtered["days_remaining"] <= dm[tl_end_within]]

    components.render_kpi_row([
        {"label": "Shown",            "value": len(filtered),                                              "color": "#1E88E5"},
        {"label": "Critical",         "value": int(len(filtered[filtered["urgency"] == "Critical"])),      "color": "#7B0000"},
        {"label": "Ending ≤ 7 Days",  "value": int(len(filtered[filtered["days_remaining"].between(0,7)])),"color": "#E53935"},
        {"label": "Ending ≤ 14 Days", "value": int(len(filtered[filtered["days_remaining"].between(0,14)])),"color":"#FB8C00"},
        {"label": "Ending ≤ 30 Days", "value": int(len(filtered[filtered["days_remaining"].between(0,30)])),"color":"#FDD835"},
    ])

    st.markdown("### Assignment Gantt Chart")
    st.caption("Each bar = one worker's assignment. Hover for details. Filter using the left sidebar.")

    if filtered.empty:
        st.warning("No assignments match the current filters.")
    else:
        # High-contrast premium HTML Legend & Highlight Filter
        col_l1, col_l2 = st.columns([1, 2])
        with col_l1:
            marker_highlight = st.selectbox(
                "Highlight Event Marker on Chart",
                ["Show All", "Worker Time Off (🔵)", "Renewal Due (🟡)", "Ending in 14d (🟠)", "Ending in 7d (❌)", "Extension Pending (🔷)", "Redeployment Confirmed (⭐)"],
                key="timeline_marker_filter"
            )
        with col_l2:
            st.markdown(
                """
                <div class="custom-legend-card" style="background:var(--card-bg, #ffffff); border: 1px solid var(--card-border, #cbd5e1); border-radius: 8px; padding: 12px 16px; min-height: 80px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                    <div style="color:var(--heading-color, #0f172a) !important; font-weight:700; font-size:0.8rem; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">Timeline Event Markers</div>
                    <div style="display:flex; flex-wrap:wrap; gap:12px; font-size:0.75rem; color:var(--app-text, #475569) !important;">
                        <div style="display:flex; align-items:center; gap:4px;"><span style="color:#1E88E5; font-size:1.1rem; line-height:1;">🔵</span> <span>Time Off</span></div>
                        <div style="display:flex; align-items:center; gap:4px;"><span style="color:#FDD835; font-size:1.1rem; line-height:1;">🟡</span> <span>Renewal Due</span></div>
                        <div style="display:flex; align-items:center; gap:4px;"><span style="color:#FB8C00; font-size:1.1rem; line-height:1;">🟠</span> <span>Ending 14d</span></div>
                        <div style="display:flex; align-items:center; gap:4px;"><span style="color:#E53935; font-size:1.1rem; line-height:1;">❌</span> <span>Ending 7d</span></div>
                        <div style="display:flex; align-items:center; gap:4px;"><span style="color:#0F52BA; font-size:1.1rem; line-height:1;">🔷</span> <span>Extension Pending</span></div>
                        <div style="display:flex; align-items:center; gap:4px;"><span style="color:#43A047; font-size:1.1rem; line-height:1;">⭐</span> <span>Redeployment Confirmed</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.plotly_chart(charts.build_timeline_chart(filtered, highlight=marker_highlight),
                        width="stretch", key=ckey("gantt"))

    st.divider()
    components.section_header("Active Assignment Forecast Table",
                               "Replacing spreadsheets and memory with automated, multi-variable project forecasting.", "📅")
    
    if filtered.empty:
        st.warning("No assignments match the current filters.")
    else:
        # Create structured display DataFrame
        forecast_df = filtered.copy()
        
        # Calculate time off display string
        time_off_display = []
        for idx, row in forecast_df.iterrows():
            to_start = str(row.get("time_off_start", "")).strip()
            to_end = str(row.get("time_off_end", "")).strip()
            if to_start and to_start not in ["NaT", "nan", "<NA>", "None", ""]:
                if to_end and to_end not in ["NaT", "nan", "<NA>", "None", ""]:
                    time_off_display.append(f"{to_start} to {to_end}")
                else:
                    time_off_display.append(to_start)
            else:
                time_off_display.append("None")
                
        forecast_df["Time Off"] = time_off_display
        
        # Define display column mappings
        col_mapping = {
            "worker_name": "Worker Name",
            "client_name": "Client",
            "role": "Role",
            "start_date": "Start Date",
            "current_projected_end_date": "Projected End Date",
            "original_duration": "Duration",
            "extension_status": "Extension Status",
            "Time Off": "Time Off",
            "recruiter_owner": "Recruiter",
            "last_check_in_date": "Last Check-in",
            "next_action": "Next Action",
            "forecast_status": "Forecast Status"
        }
        
        display_cols = [
            "worker_name", "client_name", "role", "start_date", 
            "current_projected_end_date", "original_duration", 
            "extension_status", "Time Off", "recruiter_owner", 
            "last_check_in_date", "next_action", "forecast_status"
        ]
        display_cols = [c for c in display_cols if c in forecast_df.columns]
        display_df = forecast_df[display_cols].copy()
        
        # Format date columns to strings
        for c in ["start_date", "current_projected_end_date", "last_check_in_date"]:
            if c in display_df.columns:
                try:
                    display_df[c] = pd.to_datetime(display_df[c]).dt.strftime('%Y-%m-%d')
                except Exception:
                    pass
                
        # Render beautiful HTML table
        html_table = components.render_styled_table(
            display_df,
            badge_cols=["Extension Status", "Forecast Status"],
            column_names=col_mapping
        )
        
        st.markdown(html_table, unsafe_allow_html=True)
        components.csv_download_button(display_df.rename(columns=col_mapping), "active_assignments_forecast.csv")


# ██████████████████████████████████████████████████████████████████████████████
# PAGE 3 — OPEN POSITIONS
# ██████████████████████████████████████████████████████████████████████████████

with tab3:
    components.page_banner(
        "Open Orders Board",
        "Replace paper tracking for jobs that need to be filled. See every open order, who has been submitted, whether they were approved, and what needs to happen next.",
        "📋",
        decision_label="Helps answer: \"Which jobs need candidates, client follow-up, or approval?\""
    )

    fpos = pos.copy()
    if pos_priorities:
        fpos = fpos[fpos["priority"].isin(pos_priorities)]
    if pos_stages_sel:
        fpos = fpos[fpos["stage"].isin(pos_stages_sel)]
    if pos_rec_sel:
        fpos = fpos[fpos["recruiter_owner"].isin(pos_rec_sel)]
    if pos_stuck_only and "is_stuck" in fpos.columns:
        fpos = fpos[fpos["is_stuck"]]

    high_pri   = int(len(fpos[fpos["priority"] == "High"]))
    stuck_cnt  = int(fpos["is_stuck"].sum()) if "is_stuck" in fpos.columns else 0
    no_subs    = int(len(fpos[fpos["candidates_submitted"] == 0]))
    intake_inc = int(len(fpos[fpos["intake_complete"] == False]))

    components.render_kpi_row([
        {"label": "Total Shown",        "value": len(fpos),   "color": "#1E88E5"},
        {"label": "High Priority",      "value": high_pri,    "color": "#E53935"},
        {"label": "Stuck / Flagged",    "value": stuck_cnt,   "color": "#FB8C00"},
        {"label": "No Submissions Yet", "value": no_subs,     "color": "#FDD835"},
        {"label": "Intake Incomplete",  "value": intake_inc,  "color": "#9E9E9E"},
    ])

    col_s, col_p = st.columns(2)
    with col_s:
        st.plotly_chart(charts.build_positions_by_stage(fpos),
                        width="stretch", key=ckey("stage_donut"))
    with col_p:
        st.plotly_chart(charts.build_priority_breakdown(fpos),
                        width="stretch", key=ckey("priority_bar"))

    if stuck_cnt > 0 and "is_stuck" in fpos.columns:
        components.section_header("Stuck / Flagged Positions",
                                   "Need immediate attention.", "🚧")
        with st.expander(f"🛑 View Stuck & Blocked Positions ({stuck_cnt} positions)", expanded=(stuck_cnt > 0)):
            for _, row in fpos[fpos["is_stuck"]].sort_values(
                    "priority", key=lambda x: x.map({"High": 0, "Medium": 1, "Low": 2})).iterrows():
                col_alert, col_btn = st.columns([5, 1])
                with col_alert:
                    components.alert_row("Open Position",
                        subject=f"{row['role']} @ {row['client_name']}",
                        detail=f"Open {row['days_open']}d · {row['candidates_submitted']} submitted · {row['stuck_reason']}",
                        action="Review and unblock",
                        severity="Orange" if row["priority"] == "High" else "Yellow",
                        recruiter=row["recruiter_owner"])
                with col_btn:
                    st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)
                    if st.button("Unblock", key=f"unblock_pos_{row['position_id']}"):
                        show_unblock_dialog(row.to_dict())

    components.section_header("Master Open Orders Board",
                               "Single master grid replacing paper tracking. Shows every open order, who has been submitted, approval status, and what needs to happen next.", "📋")
    
    if fpos.empty:
        st.warning("No open positions match the current filters.")
    else:
        # Create a display copy
        master_df = fpos.copy()
        
        # Format Stuck Flag
        master_df["Stuck Flag"] = master_df["is_stuck"].map({True: "STUCK", False: "HEALTHY"})

        # Add candidate approval alert column
        def approval_alert(row):
            submitted = row.get("candidates_submitted", 0) or 0
            approval = str(row.get("approval_status", "")).strip()
            days_open = row.get("days_open", 0) or 0
            intake = row.get("intake_complete", True)
            interview = str(row.get("interview_status", "")).strip()

            if not intake:
                return "⚠ Intake incomplete"
            if submitted == 0 and days_open > 7:
                return "🔴 Sourcing needed"
            if submitted == 0:
                return "🟡 No submissions yet"
            if approval == "Pending Client Review":
                return "🟠 Follow-up needed"
            if approval in ["Approved", "Interview Scheduled"] and (not interview or interview in ["", "None", "nan"]):
                return "🟡 Schedule interview"
            if approval == "Approved":
                return "🟢 Approved"
            if approval == "Filled":
                return "🟢 Filled"
            return "ℹ Monitor"

        master_df["Action Needed"] = master_df.apply(approval_alert, axis=1)

        # Compute days since last update (use days_open as proxy if no dedicated field)
        if "days_open" in master_df.columns:
            master_df["Days Open"] = master_df["days_open"].fillna(0).astype(int)
        
        # Define display column mappings
        col_mapping = {
            "client_name": "Client",
            "role": "Position",
            "priority": "Urgency",
            "recruiter_owner": "Recruiter",
            "candidates_submitted": "# Submitted",
            "candidate_submitted_names": "Submitted Names",
            "candidate_submission_dates": "Submission Dates",
            "approval_status": "Approval Status",
            "interview_status": "Interview Status",
            "client_feedback": "Client Feedback",
            "Days Open": "Days Open",
            "next_order_action": "Next Action",
            "Action Needed": "Action Needed",
            "Stuck Flag": "Stuck",
        }
        
        display_cols = [
            "client_name", "role", "priority", "recruiter_owner",
            "candidates_submitted", "candidate_submitted_names", "candidate_submission_dates",
            "approval_status", "interview_status", "client_feedback",
            "Days Open", "next_order_action", "Action Needed", "Stuck Flag"
        ]
        
        display_cols = [c for c in display_cols if c in master_df.columns]
        display_df = master_df[display_cols].copy()
        
        # Format list-like or empty fields
        for col in ["candidate_submitted_names", "candidate_submission_dates", "client_feedback"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].fillna("—")
                display_df[col] = display_df[col].apply(lambda x: "—" if not str(x).strip() or str(x) in ["nan", "None"] else x)

        # Render table
        html_table = components.render_styled_table(
            display_df,
            badge_cols=["Urgency", "Approval Status", "Action Needed", "Stuck"],
            column_names=col_mapping
        )
        
        st.markdown(html_table, unsafe_allow_html=True)

        st.caption("""
        **Approval Status guide:** Not Submitted → Submitted → Waiting on Client → Approved → Interview Scheduled → Offer Pending → Filled
        · Candidate submitted 3+ days with no client response = follow-up needed · No submissions after 7 days = sourcing needed
        """)
        
        st.divider()
        components.csv_download_button(display_df.rename(columns=col_mapping), "master_open_orders.csv",
                                       "⬇ Download Master Open Orders")


# ██████████████████████████████████████████████████████████████████████████████
# PAGE 4 — RECRUITER PROCESS TRACKER  (swapped from tab5)
# ██████████████████████████████████████████████████████████████████████████████

with tab4:
    components.page_banner(
        "Recruiter Process Tracker",
        "Process visibility without micromanagement. See required field completion, proficiency testing status, and candidate submission readiness at a glance.",
        "👥",
        decision_label="Helps answer: \"Is the recruiting process being followed consistently — and what's still incomplete?\""
    )

    # ── Action queue from matching engine ─────────────────────────────────────
    components.section_header("Recruiter Action Queue",
                               "Prioritized tasks based on candidate readiness and open order pipeline.", "⚡")
    try:
        req_wb = st.session_state.requirements
        mr_wb  = add_readiness_status(score_all_workers(workers_live, req_wb))
        acts   = generate_actions(mr_wb)
        if not acts.empty:
            acts["status"] = acts.apply(
                lambda r: st.session_state.action_statuses.get(r["action_id"], r["status"]),
                axis=1,
            )
            aq1, aq2 = st.columns([1, 1])
            with aq1:
                aq_priority = st.multiselect("Priority", ["High", "Medium", "Low"],
                                              default=["High", "Medium"], key="aq_priority")
            with aq2:
                aq_status = st.multiselect("Status",
                                            ["Not Started", "In Progress", "Done", "Blocked"],
                                            default=["Not Started", "In Progress", "Blocked"],
                                            key="aq_status")
            acts_show = acts.copy()
            if aq_priority: acts_show = acts_show[acts_show["priority"].isin(aq_priority)]
            if aq_status:   acts_show = acts_show[acts_show["status"].isin(aq_status)]

            ready_c   = int((mr_wb["readiness_status"] == "Ready for Recruiter Review").sum())
            blocked_c = int(mr_wb["readiness_status"].str.contains("Blocked").sum())
            open_acts = int((acts["status"] != "Done").sum())
            components.render_kpi_row([
                {"label": "Open Actions",     "value": open_acts,  "color": "#E53935"},
                {"label": "High Priority",    "value": int((acts[acts["status"]!="Done"]["priority"]=="High").sum()), "color": "#FB8C00"},
                {"label": "Ready for Review", "value": ready_c,   "color": "#43A047"},
                {"label": "Blocked",          "value": blocked_c, "color": "#7B0000"},
            ])

            if acts_show.empty:
                st.success("No actions match the current filters.")
            else:
                edited = st.data_editor(
                    acts_show[["action_id", "priority", "due_date", "worker_name",
                                "match_score", "action", "reason", "status"]],
                    width="stretch", hide_index=True,
                    disabled=["action_id", "priority", "due_date", "worker_name",
                               "match_score", "action", "reason"],
                    column_config={
                        "status": st.column_config.SelectboxColumn(
                            "Status",
                            options=["Not Started", "In Progress", "Done", "Blocked"],
                        ),
                        "due_date": st.column_config.DateColumn("Due"),
                    },
                    key="aq_editor",
                )
                for _, r in edited.iterrows():
                    st.session_state.action_statuses[r["action_id"]] = r["status"]
                done_count = int((edited["status"] == "Done").sum())
                if done_count:
                    st.success(f"{done_count} action(s) marked Done.")
        else:
            st.info("No actions generated — select a job in the Candidate Matching tab first.")
    except Exception as e:
        st.warning(f"Action queue: {e}")
    st.divider()

    st.plotly_chart(charts.build_recruiter_workload_chart(workload),
                    width="stretch", key=ckey("wl_bar"))

    components.section_header("Recruiter Workload Summary", "How assignments, open orders, and tasks are distributed across recruiters.", "📋")
    wl_disp = workload.copy()
    wl_disp["workload"] = wl_disp["workload_label"] + " (" + wl_disp["workload_score"].astype(str) + ")"
    wl_disp = wl_disp[["recruiter", "open_positions", "active_assignments",
                         "high_priority_positions", "ending_soon",
                         "overdue_actions", "checkin_needed", "workload"]]
    wl_disp.columns = ["Recruiter", "Open Positions", "Active Assignments",
                        "High Priority", "Ending ≤30d", "Overdue", "Check-In Needed", "Workload"]
    st.dataframe(wl_disp, width="stretch", height=210)
    st.caption(
        "Score = (open × 2) + (high_priority × 3) + (overdue × 2) + (ending_soon × 2)  "
        "·  Light < 10  ·  Balanced 10–20  ·  Heavy 20–32  ·  Overloaded 32+"
    )
    st.divider()

    show_recs = (
        [wb_recruiter] if wb_recruiter != "All Recruiters"
        else sorted(workload["recruiter"].tolist())
    )

    for rec in show_recs:
        rec_rows = workload[workload["recruiter"] == rec]
        if rec_rows.empty:
            continue
        rec_row  = rec_rows.iloc[0]
        with st.expander(
            f"**{rec}**  —  {rec_row['workload_label']} Workload  "
            f"(Score: {rec_row['workload_score']})",
            expanded=(wb_recruiter != "All Recruiters"),
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Open Positions",     rec_row["open_positions"])
            c2.metric("Active Assignments", rec_row["active_assignments"])
            c3.metric("Ending ≤30d",        rec_row["ending_soon"])
            c4.metric("Overdue Actions",    rec_row["overdue_actions"])

            rec_pos  = pos[pos["recruiter_owner"] == rec]
            open_pos = rec_pos[~rec_pos["stage"].isin(["Filled", "On Hold"])]
            if not open_pos.empty:
                st.markdown("**Open Positions:**")
                st.dataframe(open_pos[[
                    "position_id", "client_name", "role", "priority",
                    "stage", "days_open", "candidates_submitted",
                    "is_stuck", "stuck_reason"
                ]], width="stretch", height=180)

            rec_asgn = asgn[(asgn["recruiter_owner"] == rec) &
                             asgn["days_remaining"].between(0, 30)]
            if not rec_asgn.empty:
                st.markdown("**Assignments Ending in 30 Days:**")
                st.dataframe(
                    fmt_dates(rec_asgn[[
                        "worker_name", "client_name", "role",
                        "end_date", "days_remaining", "urgency", "redeployment_status"
                    ]], ["end_date"]),
                    width="stretch", height=180)

            if "is_overdue" in act.columns:
                rec_act = act[(act["recruiter_name"] == rec) & act["is_overdue"]]
                if not rec_act.empty:
                    st.markdown("**Overdue Actions:**")
                    st.dataframe(
                        fmt_dates(rec_act[[
                            "activity_id", "activity_type", "related_worker",
                            "related_client", "due_date", "status", "next_action"
                        ]], ["due_date"]),
                        width="stretch", height=160)

            if "checkin_needed" in asgn.columns:
                rec_ci = asgn[(asgn["recruiter_owner"] == rec) & asgn["checkin_needed"]]
                if not rec_ci.empty:
                    st.markdown("**Workers Needing Check-In:**")
                    st.dataframe(
                        fmt_dates(rec_ci[[
                            "worker_name", "client_name", "role",
                            "last_worker_contact", "days_remaining"
                        ]], ["last_worker_contact"]),
                        width="stretch", height=160)

    st.divider()
    st.plotly_chart(charts.build_overdue_by_recruiter(act),
                    width="stretch", key=ckey("overdue_rec_wb"))

    # ── Candidate Readiness & Process Tracker (reference data) ────────────────
    st.divider()
    components.section_header("Candidate Readiness & Process Tracker",
                               "Process visibility checkpoint — track profile completeness and required skills test status before client submission.", "📋")

    if workers_live.empty:
        st.warning("No worker profiles found.")
    else:
        # Pinned candidates: Mike R., Jason T., Robert L.
        pinned_names = ["Mike R.", "Jason T.", "Robert L."]
        pinned_df = workers_live[workers_live["worker_name"].isin(pinned_names)].copy()
        other_df = workers_live[~workers_live["worker_name"].isin(pinned_names)].copy()

        pinned_df["pin_order"] = pinned_df["worker_name"].map({name: idx for idx, name in enumerate(pinned_names)})
        pinned_df = pinned_df.sort_values("pin_order").drop(columns=["pin_order"])
        data_quality_df = pd.concat([pinned_df, other_df], ignore_index=True)

        # Compute profile completion %
        req_fields = ["primary_trade", "skills", "certifications", "willing_to_travel",
                      "shift_preference", "availability_date", "recruiter_notes"]
        def compute_completion(row):
            filled = sum(1 for f in req_fields if pd.notna(row.get(f)) and str(row.get(f, "")).strip() not in ["", "nan", "None"])
            return f"{int(filled / len(req_fields) * 100)}%"
        data_quality_df["Completion %"] = data_quality_df.apply(compute_completion, axis=1)

        col_mapping = {
            "worker_name": "Candidate",
            "primary_trade": "Role / Trade",
            "Completion %": "Profile Complete",
            "missing_fields": "Missing Fields",
            "proficiency_test_status": "Proficiency Test",
            "process_status": "Readiness Status"
        }

        display_cols = ["worker_name", "primary_trade", "Completion %", "missing_fields", "proficiency_test_status", "process_status"]
        display_cols = [c for c in display_cols if c in data_quality_df.columns]
        display_df = data_quality_df[display_cols].copy()

        if "missing_fields" in display_df.columns:
            display_df["missing_fields"] = display_df["missing_fields"].fillna("Complete")
            display_df["missing_fields"] = display_df["missing_fields"].apply(lambda x: "Complete" if not str(x).strip() or str(x) == "nan" else x)
        if "proficiency_test_status" in display_df.columns:
            display_df["proficiency_test_status"] = display_df["proficiency_test_status"].fillna("Complete")
            display_df["proficiency_test_status"] = display_df["proficiency_test_status"].apply(lambda x: "Complete" if not str(x).strip() or str(x) == "nan" else x)
        if "process_status" in display_df.columns:
            display_df["process_status"] = display_df["process_status"].fillna("Ready")

        html_table = components.render_styled_table(
            display_df,
            badge_cols=["Missing Fields", "Proficiency Test", "Readiness Status"],
            column_names=col_mapping
        )
        st.markdown(html_table, unsafe_allow_html=True)
        components.csv_download_button(display_df.rename(columns=col_mapping), "candidate_process_tracker.csv", "⬇ Download Process Tracker")
        st.markdown("<br>", unsafe_allow_html=True)



# ██████████████████████████████████████████████████████████████████████████████
# PAGE 5 — CANDIDATE MATCHING  (Future Expansion — moved from tab4)
# ██████████████████████████████████████████████████████████████████████████████

with tab5:
    components.page_banner(
        "Candidate Matching",
        "Score available workers against a structured job order. Transparent rule-based ranking — recruiter review required. (Future Expansion area)",
        "🔍",
    )
    st.info("💡 **Future Expansion** — This feature is available for exploration but is not part of the core first-meeting demo. Focus on the first four tabs for client presentations.", icon="ℹ️")

    # ── Job order selector
    jo_col, req_col = st.columns([1, 1])
    with jo_col:
        st.markdown("**Select a Job Order**")
        if JO_OPTIONS:
            selected_jo_label = st.selectbox("Load Job Scenario",
                                             list(JO_OPTIONS.keys()),
                                             key="jo_select")
            if st.button("Load This Job", key="jo_load_btn"):
                jo_id  = JO_OPTIONS[selected_jo_label]
                jo_row = job_orders[job_orders["job_order_id"] == jo_id].iloc[0]
                st.session_state.requirements = requirements_from_job_order(jo_row)
                st.session_state.raw_job_text = str(jo_row.get("client_notes", ""))
                st.session_state.jo_raw_text  = str(jo_row.get("client_notes", ""))
                st.session_state.action_statuses = {}
                st.rerun()
        else:
            st.caption("No job orders found. Using default requirements.")
        raw_text = st.text_area("Or paste a client job request",
                                value=st.session_state.jo_raw_text,
                                height=90, key="jo_raw_text")
        if st.button("Extract Requirements", key="jo_extract_btn"):
            st.session_state.raw_job_text  = raw_text
            st.session_state.requirements  = extract_job_requirements(raw_text)
            st.session_state.action_statuses = {}
            st.rerun()

    with req_col:
        req = st.session_state.requirements
        st.markdown("**Active Job Requirements**")
        brief = generate_requirement_brief(req, st.session_state.use_ai_assist,
                                           st.session_state.llm_model)
        st.info(brief)
        with st.expander("Full structured requirements"):
            st.json(req)

    st.divider()

    # ── Run match
    req = st.session_state.requirements
    try:
        match_results = add_readiness_status(
            score_all_workers(workers_live, req)
        )

        strong = int((match_results["match_tier"] == "Strong Fit").sum())
        good   = int((match_results["match_tier"] == "Good Fit").sum())
        review = int((match_results["match_tier"] == "Needs Review").sum())
        blocked_m = int(match_results["readiness_status"].str.contains("Blocked").sum())
        components.render_kpi_row([
            {"label": "Workers Scored",    "value": len(match_results), "color": "#1E88E5"},
            {"label": "Strong Fits",       "value": strong,             "color": "#43A047"},
            {"label": "Good Fits",         "value": good,               "color": "#FDD835"},
            {"label": "Needs Review",      "value": review,             "color": "#FB8C00"},
            {"label": "Blocked",           "value": blocked_m,          "color": "#E53935"},
        ])

        # Tier filter
        tier_filter = st.multiselect(
            "Filter by match tier",
            ["Strong Fit", "Good Fit", "Needs Review", "Not Recommended"],
            default=["Strong Fit", "Good Fit", "Needs Review"],
            key="match_tier_filter",
        )
        visible = match_results[match_results["match_tier"].isin(tier_filter)] if tier_filter else match_results

        st.markdown("### Ranked Worker List")
        disp_cols = ["name", "total_score", "match_tier", "readiness_status",
                     "reason_for_score", "risk_flags", "recommended_action"]
        st.dataframe(
            visible[[c for c in disp_cols if c in visible.columns]],
            width="stretch", height=300, hide_index=True,
        )

        # ── Recruiter digest
        st.markdown("### Recruiter Digest")
        digest = generate_recruiter_digest(
            match_results, req,
            st.session_state.use_ai_assist, st.session_state.llm_model,
        )
        st.write(digest)

        st.divider()
        st.markdown("### Worker Score Breakdown")
        if not match_results.empty:
            inspect_options = [f"{row['name']} ({row['worker_id']})" for _, row in match_results.iterrows()]
            active_role = req.get("role", "default")
            sel_label = st.selectbox(
                "Select worker to inspect",
                inspect_options,
                key=f"match_inspect_select_{active_role}_{len(match_results)}",
            )
            sel_wid  = sel_label.split(" (")[-1].rstrip(")")
            sel_row  = match_results[match_results["worker_id"] == sel_wid].iloc[0]
            sel_w    = workers_live[workers_live["worker_id"] == sel_wid].iloc[0] \
                       if sel_wid and "worker_id" in workers_live.columns else pd.Series(dtype=object)

            sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
            sc1.metric("Required Skill",   sel_row["required_skill_score"])
            sc2.metric("Machine/Control",  sel_row["machine_control_score"])
            sc3.metric("Industry",         sel_row["industry_score"])
            sc4.metric("Travel",           sel_row["travel_score"])
            sc5.metric("Availability",     sel_row["availability_score"])
            sc6.metric("Rating",           sel_row["rating_score"])

            expl = build_match_explanation(sel_row)
            with st.expander("Recruiter explanation", expanded=True):
                st.write("**Strengths**")
                for s in expl["strengths"]:
                    st.write(f"- {s}")
                st.write("**Verification needed**")
                if expl["verification_needed"]:
                    for v in expl["verification_needed"]:
                        st.write(f"- {v}")
                else:
                    st.write("- No major blockers flagged by the rules.")
                st.write(f"**Decision-support note:** {expl['decision_support_note']}")

            if not sel_w.empty:
                with st.expander("Worker profile", expanded=False):
                    p1, p2 = st.columns(2)
                    with p1:
                        st.write(f"**Home state:** {sel_w.get('home_state','—')}")
                        st.write(f"**Travel ready:** {sel_w.get('willing_to_travel','—')}")
                        avail_d = sel_w.get('availability_date', pd.NaT)
                        avail_s = str(avail_d)[:10] if pd.notna(avail_d) else '—'
                        st.write(f"**Available:** {avail_s}")
                        st.write(f"**Shift pref:** {sel_w.get('shift_preference','—')}")
                    with p2:
                        st.write(f"**Machine brands:** {sel_w.get('machine_brands','—')}")
                        st.write(f"**Controls:** {sel_w.get('controls','—')}")
                        st.write(f"**Industry exp:** {sel_w.get('industry_experience','—')}")
                        certs = sel_w.get('certifications','—')
                        st.write(f"**Certifications:** {certs if certs else '—'}")

            # ── Candidate quick-edit & notes
            with st.expander("Quick Edit — Update Worker Profile", expanded=False):
                with st.form(f"quick_edit_{sel_wid}"):
                    qe1, qe2 = st.columns(2)
                    with qe1:
                        avail_val = sel_w.get("availability_date", pd.Timestamp.now()) \
                                    if not sel_w.empty else pd.Timestamp.now()
                        if pd.isna(avail_val): avail_val = pd.Timestamp.now()
                        qe_avail   = st.date_input("Availability date", value=avail_val.date())
                        qe_travel  = st.checkbox("Travel ready",
                                                  value=bool(sel_w.get("willing_to_travel", False))
                                                  if not sel_w.empty else False)
                        qe_shift   = st.selectbox("Shift preference",
                                                   ["1st shift", "2nd shift", "Any"],
                                                   index=["1st shift","2nd shift","Any"].index(
                                                       sel_w.get("shift_preference","Any")
                                                   ) if sel_w.get("shift_preference") in
                                                   ["1st shift","2nd shift","Any"] else 2)
                    with qe2:
                        qe_rdep    = st.text_input("Redeployment status",
                                                    value=str(sel_w.get("redeployment_status","")) if not sel_w.empty else "")
                        qe_missing = st.text_area("Missing info flags",
                                                   value=str(sel_w.get("missing_information_flags","")) if not sel_w.empty else "",
                                                   height=60)
                        qe_notes   = st.text_area("Recruiter notes",
                                                   value=str(sel_w.get("recruiter_notes","")) if not sel_w.empty else "",
                                                   height=60)
                    saved_qe = st.form_submit_button("Save Updates")
                if saved_qe:
                    st.session_state.worker_overrides = update_worker_override(
                        st.session_state.worker_overrides, sel_wid,
                        {"availability_date": qe_avail, "willing_to_travel": qe_travel,
                         "shift_preference": qe_shift, "redeployment_status": qe_rdep,
                         "missing_information_flags": qe_missing, "recruiter_notes": qe_notes},
                    )
                    st.success("Worker updates saved. Matching scores will refresh.")
                    st.rerun()

            with st.expander("Add Recruiter Note", expanded=False):
                with st.form(f"note_form_{sel_wid}"):
                    nt_type = st.selectbox("Note type", NOTE_TYPES)
                    nt_text = st.text_area("Note", height=80)
                    nt_save = st.form_submit_button("Add Note")
                if nt_save and nt_text.strip():
                    jo_id_cur = req.get("raw_request", "")[:20] or "CUSTOM"
                    st.session_state.worker_notes = add_worker_note(
                        st.session_state.worker_notes, sel_wid,
                        jo_id_cur, nt_type, nt_text, "Demo Recruiter",
                    )
                    st.success("Note added.")

            notes = get_worker_notes(sel_wid, st.session_state.worker_notes)
            if notes:
                st.markdown("**Recent Notes**")
                for n in notes[:5]:
                    st.markdown(
                        f"**{n['timestamp']} — {n['note_type']}**  \n"
                        f"{n['note_text']}  \n"
                        f"_Recruiter: {n['recruiter']}_"
                    )

    except Exception as e:
        st.error(f"Candidate matching error: {e}")
        st.exception(e)







# ██████████████████████████████████████████████████████████████████████████████
# PAGE 6 — REDEPLOYMENT (Future Expansion)
# ██████████████████████████████████████████████████████████████████████████████

with tab6:
    components.page_banner(
        "Redeployment Planning",
        "Turn each placement into the next one. Plan ahead before assignments end. (Future Expansion area)",
        "🔄",
        decision_label="Helps answer: \"Which workers should be placed again before they roll off assignment?\""
    )
    st.info("💡 **Future Expansion** — This feature is available for exploration but is not part of the core first-meeting demo.", icon="ℹ️")

    try:
        hmap    = {"30 Days": 30, "60 Days": 60, "90 Days": 90, "All": 9999}
        max_d   = hmap.get(rd_horizon, 60)
        rd_df   = asgn[asgn["days_remaining"] <= max_d].copy()
        if rd_not_started:
            rd_df = rd_df[rd_df["redeployment_status"] == "Not Started"]
        rd_df = rd_df.sort_values("days_remaining")

        components.render_kpi_row([
            {"label": "Workers in Window",       "value": len(rd_df),
             "color": "#1E88E5"},
            {"label": "Not Started",             "value": int((rd_df["redeployment_status"] == "Not Started").sum()),
             "color": "#E53935"},
            {"label": "In Progress / Contacted", "value": int(rd_df["redeployment_status"].isin(["Worker Contacted","Interested"]).sum()),
             "color": "#FB8C00"},
            {"label": "Matched to Role",         "value": int((rd_df["redeployment_status"] == "Matched to Open Role").sum()),
             "color": "#FDD835"},
            {"label": "Redeployed",              "value": int((rd_df["redeployment_status"] == "Redeployed").sum()),
             "color": "#43A047"},
        ])

        priority_rd = rd_df[
            (rd_df["redeployment_status"] == "Not Started") &
            (rd_df["days_remaining"] <= 30)
        ]
        if not priority_rd.empty:
            components.section_header("Priority: Not Started, Ending ≤ 30 Days",
                                       "No redeployment plan yet — ends soon.", "🚨")
            with st.expander(f"⚠️ View Critical Redeployment Alerts ({len(priority_rd)} workers)", expanded=True):
                for _, row in priority_rd.iterrows():
                    components.alert_row("Redeployment",
                        subject=f"{row['worker_name']}  ({row['role']})",
                        detail=(f"@ {row['client_name']} · Ends {str(row['end_date'])[:10]} "
                                f"· {row['days_remaining']} days · {row['recruiter_owner']}"),
                        action=str(row.get("recommended_redeploy_action", "Review")),
                        severity="Red" if row["days_remaining"] <= 14 else "Orange",
                        recruiter=row["recruiter_owner"])

        components.section_header("Redeployment Tracker", "", "📋")
        rd_cols   = ["worker_name", "client_name", "role", "trade_category",
                     "recruiter_owner", "end_date", "days_remaining",
                     "redeployment_status", "possible_next_match",
                     "recommended_redeploy_action", "extension_possible"]
        available = [c for c in rd_cols if c in rd_df.columns]
        show_rd   = fmt_dates(rd_df[available], ["end_date"])
        show_rd.columns = [c.replace("_", " ").title() for c in show_rd.columns]

        with st.expander(f"🔄 View Master Redeployment Tracker ({len(rd_df)} workers)", expanded=True):
            if show_rd.empty:
                st.info("No workers match the current filters.")
            else:
                st.dataframe(show_rd, width="stretch", height=420)
                components.csv_download_button(show_rd, "redeployment_tracker.csv")

        st.divider()
        with st.expander("How does 'Possible Next Match' work?"):
            st.markdown("""
**Deterministic Matching Logic (Demo)**

For each worker ending in the next 60 days, the system scans open positions and finds the best fit based on:
1. **Trade category match** — CNC worker matched to CNC role, welder to welding role, etc.
2. **State preference** — same state as current assignment preferred first
3. **Priority** — High priority open roles surfaced before Medium or Low

This is fully transparent rule-based logic, not AI. A production version would also
factor specific skills, certifications, pay rate, and travel preference.

| Status | Meaning |
|--------|---------|
| Not Started | No action taken |
| Worker Contacted | Recruiter has reached out |
| Interested | Worker open to next role |
| Matched to Open Role | Specific match identified |
| Submitted | Worker submitted to next client |
| Redeployed | Placed in next assignment |
| Not Available | Not looking for work |
| Follow Up Later | Revisit at a later date |
""")

    except Exception as e:
        st.error(f"Redeployment error: {e}")
        st.exception(e)


# ██████████████████████████████████████████████████████████████████████████████
# PAGE 7 — SUBMITTAL PACKETS (Future Expansion)
# ██████████████████████████████████████████████████████████████████████████████

with tab7:
    components.page_banner(
        "Submittal Packets",
        "Generate a client-ready candidate summary. Rule-based draft with optional AI assist — recruiter review always required. (Future Expansion area)",
        "📤",
    )
    st.info("💡 **Future Expansion** — This feature is available for exploration but is not part of the core first-meeting demo.", icon="ℹ️")

    try:
        req_sp = st.session_state.requirements
        mr_sp  = add_readiness_status(score_all_workers(workers_live, req_sp))

        if mr_sp.empty:
            st.info("No workers to summarize. Run matching in the Candidate Matching tab.")
        else:
            sp_options = [f"{row['name']} ({row['worker_id']})" for _, row in mr_sp.iterrows()]
            active_role_sp = req_sp.get("role", "default")
            sel_label_sp = st.selectbox(
                "Select worker for submittal packet",
                sp_options,
                key=f"sp_worker_select_{active_role_sp}_{len(mr_sp)}",
            )
            sel_wid_sp = sel_label_sp.split(" (")[-1].rstrip(")")
            sel_row_sp = mr_sp[mr_sp["worker_id"] == sel_wid_sp].iloc[0]
            sel_w_sp   = workers_live[workers_live["worker_id"] == sel_wid_sp].iloc[0] \
                         if sel_wid_sp and "worker_id" in workers_live.columns else pd.Series(dtype=object)

            # Metrics
            components.render_kpi_row([
                {"label": "Match Score",    "value": sel_row_sp["total_score"],   "color": "#1E88E5"},
                {"label": "Tier",           "value": sel_row_sp["match_tier"],    "color": "#43A047"},
                {"label": "Readiness",      "value": sel_row_sp["readiness_status"], "color": "#FDD835"},
            ])

            # Submittal packet info
            sp_l, sp_r = st.columns(2)
            with sp_l:
                st.write(f"**Worker:** {sel_row_sp.get('name', '—')}")
                st.write(f"**Role:** {req_sp.get('role','—')}")
                st.write(f"**Location:** {req_sp.get('location_state','—')}")
                if not sel_w_sp.empty:
                    avd = sel_w_sp.get('availability_date', pd.NaT)
                    st.write(f"**Available:** {str(avd)[:10] if pd.notna(avd) else '—'}")
                    st.write(f"**Travel ready:** {sel_w_sp.get('willing_to_travel','—')}")
            with sp_r:
                if not sel_w_sp.empty:
                    st.write(f"**Machine brands:** {sel_w_sp.get('machine_brands','—')}")
                    st.write(f"**Controls:** {sel_w_sp.get('controls','—')}")
                    st.write(f"**Industry exp:** {sel_w_sp.get('industry_experience','—')}")
                    st.write(f"**Prior rating:** {sel_w_sp.get('prior_assignment_rating','—')}")

            # Verification checklist
            expl_sp = build_match_explanation(sel_row_sp)
            with st.expander("Verification Checklist", expanded=True):
                if expl_sp["verification_needed"]:
                    for item in expl_sp["verification_needed"]:
                        st.checkbox(item, value=False, key=f"vcheck_{item[:20]}")
                else:
                    st.checkbox("Confirm final availability, interest, and travel logistics",
                                value=False, key="vcheck_default")

            # Recent notes
            sp_notes = get_worker_notes(sel_wid_sp, st.session_state.worker_notes)
            if sp_notes:
                with st.expander("Recent Recruiter Notes"):
                    for n in sp_notes[:5]:
                        st.markdown(
                            f"**{n['timestamp']} — {n['note_type']}**  \n"
                            f"{n['note_text']}  \n"
                            f"_Recruiter: {n['recruiter']}_"
                        )

            # Summary draft
            st.markdown("### Draft Submittal Summary")
            if st.button("Generate Draft", key="sp_gen_btn"):
                with st.spinner("Generating..."):
                    summary = generate_client_summary(
                        sel_w_sp if not sel_w_sp.empty else pd.Series({"name": sel_name_sp}),
                        sel_row_sp,
                        req_sp,
                        st.session_state.use_ai_assist,
                        st.session_state.llm_model,
                    )
                    st.session_state["sp_summary"] = summary

            if "sp_summary" in st.session_state:
                st.text_area("Summary draft (review before use)",
                             value=st.session_state["sp_summary"],
                             height=260, key="sp_summary_display")
                st.download_button(
                    "Download Draft (.txt)",
                    data=st.session_state["sp_summary"],
                    file_name=f"{sel_name_sp.replace(' ','_')}_submittal_draft.txt",
                    mime="text/plain",
                    key="sp_download",
                )
                approved = st.checkbox(
                    "Recruiter reviewed this draft",
                    key="sp_approved"
                )
                if approved:
                    st.success("Demo state only: Review marked.")
                
                st.divider()
                st.markdown("#### 🚀 Stage 2 Demonstration: Outbound Automated Dispatch")
                st.caption("Normally, copy-pasting is a massive manual bottleneck. In our proposed Light ATS, clicking these buttons sends direct outbound communications instantly.")
                
                out_col1, out_col2 = st.columns(2)
                with out_col1:
                    if st.button("💬 Simulate Send Twilio SMS Outreach", key="sp_sim_sms"):
                        with st.spinner("Dispatching Twilio SMS gateway..."):
                            import time
                            time.sleep(1.0)
                            st.session_state.demo_sent_sms.append({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "worker": sel_name_sp,
                                "phone": "+1 (555) 019-2834",
                                "message": f"Hi {sel_name_sp}, we have an active {req_sp.get('role')} position open in {req_sp.get('location_state')} at {sel_row_sp.get('total_score')}% match. Let us know if you're interested!"
                            })
                            st.session_state.worker_notes = add_worker_note(
                                st.session_state.worker_notes, sel_wid_sp,
                                "DEMO", "Call Note", f"Simulated outreach text sent to worker via Twilio: 'Active {req_sp.get('role')} position open...'", "Demo Recruiter"
                            )
                            st.success("✅ Simulated SMS sent to worker! Logged in Candidate Profile notes.")
                
                with out_col2:
                    if st.button("📧 Simulate Email Submittal via SendGrid", key="sp_sim_email"):
                        with st.spinner("Dispatching SendGrid email API..."):
                            import time
                            time.sleep(1.0)
                            st.session_state.demo_sent_emails.append({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "recipient": f"hiring@{req_sp.get('client_name','client').replace(' ','_').lower()}.com",
                                "candidate": sel_name_sp,
                                "subject": f"Candidate Submittal Packet - {sel_name_sp} for {req_sp.get('role')}",
                                "body": st.session_state["sp_summary"]
                            })
                            st.session_state.worker_notes = add_worker_note(
                                st.session_state.worker_notes, sel_wid_sp,
                                "DEMO", "Client Feedback", f"Simulated submittal email sent to client ({req_sp.get('client_name')}) via SendGrid.", "Demo Recruiter"
                            )
                            st.success("✅ Simulated Client email sent via SendGrid! Logged in Candidate Profile notes.")
            else:
                st.caption("Click 'Generate Draft' to create the submittal summary.")

    except Exception as e:
        st.error(f"Submittal error: {e}")
        st.exception(e)


# ██████████████████████████████████████████████████████████████████████████████
# PAGE 8 — DATA / ADMIN
# ██████████████████████████████████████████████████████████████████████████████

with tab8:
    components.page_banner(
        "Data & Admin",
        "View and download the underlying tables that power this prototype.",
        "🗄️",
    )

    st.info(
        "The main dashboard still uses the normalized demo tables. The Customer Imports tab stages the new customer files for review before they replace or extend the live dashboard feed.",
        icon="ℹ️",
    )

    try:
        a1, a2, a3, a4, a5, a6, a7 = st.tabs([
            "Assignments", "Workers", "Open Positions",
            "Recruiter Activity", "Clients", "Alerts", "Customer Imports",
        ])

        with a1:
            st.caption(f"{len(asgn)} records")
            show = fmt_dates(asgn.copy(),
                             ["start_date","end_date","last_worker_contact","last_client_contact"])
            st.dataframe(show, width="stretch", height=440)
            components.csv_download_button(show, "assignments_export.csv")

        with a2:
            st.caption(f"{len(workers)} records")
            show = fmt_dates(workers.copy(), ["availability_date","last_contact"])
            st.dataframe(show, width="stretch", height=440)
            components.csv_download_button(show, "workers_export.csv")

        with a3:
            st.caption(f"{len(pos)} records")
            show = fmt_dates(pos.copy(), ["date_opened","target_start_date"])
            st.dataframe(show, width="stretch", height=440)
            components.csv_download_button(show, "open_positions_export.csv")

        with a4:
            st.caption(f"{len(act)} records")
            show = fmt_dates(act.copy(), ["date","due_date"])
            st.dataframe(show, width="stretch", height=440)
            components.csv_download_button(show, "recruiter_activity_export.csv")

        with a5:
            st.caption(f"{len(clients)} records")
            show = fmt_dates(clients.copy(), ["last_contact"])
            st.dataframe(show, width="stretch", height=440)
            components.csv_download_button(show, "clients_export.csv")

        with a6:
            if alerts.empty:
                st.success("No alerts currently generated.")
            else:
                st.caption(f"{len(alerts)} alerts")
                st.dataframe(alerts, width="stretch", height=440)
                components.csv_download_button(alerts, "alerts_export.csv")

        with a7:
            customer_summary = CUSTOMER_PREVIEW.get("summary", {})
            customer_tables = CUSTOMER_PREVIEW.get("tables", {})
            loaded_sources = customer_summary.get("loaded_sources", 0)

            st.warning(
                "Customer import previews may include private names, phone numbers, emails, and client details. "
                "Keep raw uploads out of GitHub unless the repository and data policy are confirmed private.",
                icon="🔒",
            )

            components.render_kpi_row([
                {"label": "Roster Assignments", "value": customer_summary.get("assignments", 0), "color": "#1f5f8b"},
                {"label": "Open Orders", "value": customer_summary.get("open_positions", 0), "color": "#f97316"},
                {"label": "Candidates", "value": customer_summary.get("candidates", 0), "color": "#16a34a"},
                {"label": "Test Rows", "value": customer_summary.get("candidate_tests", 0), "color": "#7c3aed"},
                {"label": "Intake Prompts", "value": customer_summary.get("intake_questions", 0), "color": "#0f766e"},
            ])

            diag = customer_tables.get("import_diagnostics", pd.DataFrame())
            if loaded_sources == 0:
                st.error("No customer source files were loaded. Add the customer spreadsheets/PDF to the local data folder to preview mappings.")
            elif not diag.empty:
                st.caption("Import diagnostics")
                st.dataframe(diag, width="stretch", hide_index=True)

            ci1, ci2, ci3, ci4, ci5, ci6 = st.tabs([
                "Roster Assignments",
                "Open Orders",
                "Candidates",
                "Tests",
                "Intake & Timecards",
                "Ended Assignments",
            ])

            with ci1:
                cust_asgn = customer_tables.get("customer_assignments", pd.DataFrame())
                st.caption(f"{len(cust_asgn)} staged rows from the active roster workbook.")
                if cust_asgn.empty:
                    st.info("No active roster rows found.")
                else:
                    preview_cols = [
                        "worker_name", "client_name", "role", "trade_category", "start_date",
                        "end_date", "extension_status", "forecast_status", "next_action", "notes",
                    ]
                    show = fmt_dates(cust_asgn[[c for c in preview_cols if c in cust_asgn.columns]], [
                        "start_date", "end_date",
                    ])
                    st.dataframe(show, width="stretch", height=420, hide_index=True)
                    components.csv_download_button(cust_asgn, "customer_assignments_staged.csv", "Download staged assignments")

            with ci2:
                cust_pos = customer_tables.get("customer_open_positions", pd.DataFrame())
                st.caption(f"{len(cust_pos)} staged open-order rows split out of the roster workbook.")
                if cust_pos.empty:
                    st.info("No open-order rows found.")
                else:
                    preview_cols = [
                        "client_name", "role", "trade_category", "stage", "candidates_submitted",
                        "candidate_submitted_names", "approval_status", "next_order_action",
                    ]
                    st.dataframe(cust_pos[[c for c in preview_cols if c in cust_pos.columns]], width="stretch", height=360, hide_index=True)
                    components.csv_download_button(cust_pos, "customer_open_positions_staged.csv", "Download staged open orders")

            with ci3:
                cust_candidates = customer_tables.get("customer_candidates", pd.DataFrame())
                st.caption(f"{len(cust_candidates)} staged candidate/recruiter process rows.")
                if cust_candidates.empty:
                    st.info("No candidate rows found.")
                else:
                    candidate_cols = [
                        "candidate_name", "phone", "email", "primary_trade", "process_status",
                        "application_status", "proficiency_testing", "best_test_score",
                        "interview_completed", "references_completed", "profile_completed",
                        "source_status", "action_item", "notes",
                    ]
                    show = cust_candidates[[c for c in candidate_cols if c in cust_candidates.columns]]
                    st.dataframe(show, width="stretch", height=440, hide_index=True)
                    components.csv_download_button(cust_candidates, "customer_candidates_staged.csv", "Download staged candidates")

            with ci4:
                tests = customer_tables.get("customer_candidate_tests", pd.DataFrame())
                st.caption(f"{len(tests)} staged CNC/welder test result rows.")
                if tests.empty:
                    st.info("No test rows found.")
                else:
                    st.dataframe(tests[["candidate_name", "test_type", "raw_score", "score_percent", "source_file"]], width="stretch", height=420, hide_index=True)
                    components.csv_download_button(tests, "customer_candidate_tests_staged.csv", "Download staged test results")

            with ci5:
                intake = customer_tables.get("customer_intake_questions", pd.DataFrame())
                timecards = customer_tables.get("timecard_blueprint", pd.DataFrame())
                st.caption("Client intake prompts and first-pass timecard module fields.")

                tc1, tc2 = st.columns([1, 1])
                with tc1:
                    st.markdown("**Timecard Module Blueprint**")
                    st.dataframe(timecards, width="stretch", height=360, hide_index=True)
                    components.csv_download_button(timecards, "timecard_blueprint.csv", "Download timecard blueprint")
                with tc2:
                    st.markdown("**Timecard-Related Intake Questions**")
                    if intake.empty:
                        st.info("No intake questions loaded.")
                    else:
                        related = intake[intake.get("timecard_related", False) == True]
                        if related.empty:
                            st.info("No timecard-specific intake questions detected.")
                        else:
                            st.dataframe(related[["section", "question", "page"]], width="stretch", height=360, hide_index=True)

                st.markdown("**Full Intake Question Extract**")
                if intake.empty:
                    st.info("No intake PDF prompts found.")
                else:
                    st.dataframe(intake[["section", "question", "page", "timecard_related"]], width="stretch", height=360, hide_index=True)
                    components.csv_download_button(intake, "client_intake_questions_staged.csv", "Download intake questions")

            with ci6:
                ended = customer_tables.get("customer_ended_assignments", pd.DataFrame())
                st.caption(f"{len(ended)} historical ended-assignment rows.")
                if ended.empty:
                    st.info("No ended assignments found.")
                else:
                    show = fmt_dates(ended, ["start_date", "end_date"])
                    st.dataframe(show, width="stretch", height=420, hide_index=True)
                    components.csv_download_button(ended, "customer_ended_assignments_staged.csv", "Download ended assignments")

    except Exception as e:
        st.error(f"Data/Admin error: {e}")
        st.exception(e)

    st.divider()
    st.markdown("**Regenerate Demo Data**")
    st.caption("Creates fresh random demo data and reloads the page.")
    if st.button("Regenerate All Demo Data", key="regen_btn"):
        with st.spinner("Generating..."):
            try:
                if "src.demo_data_generator" in sys.modules:
                    del sys.modules["src.demo_data_generator"]
                from src.demo_data_generator import generate_all
                generate_all(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
                st.cache_data.clear()
                st.success("Done! Reloading...")
                st.rerun()
            except Exception as e:
                st.error(f"Error regenerating data: {e}")


# ██████████████████████████████████████████████████████████████████████████████
# PAGE 9 — DEMO SIMULATORS
# ██████████████████████████████████████████████████████████████████████████████

with tab9:
    components.page_banner(
        "Demo Simulators",
        "Interactive demonstrations of future workflow capabilities: resume parsing, outbound communication, and client portal preview.",
        "🚀",
    )

    sim_tab1, sim_tab2, sim_tab3 = st.tabs([
        "🎯 Stage 1: AI Resume Parsing & Upload",
        "💬 Stage 2: Outbound Communication logs",
        "🤝 Stage 3: Interactive Client Portal Preview",
    ])

    # ── SIMULATOR 1: STAGE 1 (AI Parsing)
    with sim_tab1:
        st.markdown("### 🎯 Stage 1: AI Resume Parsing & Database Sync")
        st.markdown(
            "Upload a raw resume file (PDF/TXT) or choose a pre-formatted candidate resume scenario below "
            "to test our proposed Gemini-powered extraction and instant database insertion engine."
        )

        scen = st.selectbox(
            "Select Resume Scenario to Parse",
            [
                "Scenario A: Arthur Pendragon (CNC Machinist - Colorado)",
                "Scenario B: Morgana LeFay (PLC Maintenance Tech - Texas)",
                "Scenario C: Lancelot DuLac (AWS Welder - Utah)",
            ],
            key="demo_resume_scen",
        )

        # Mock resume texts
        scenarios_data = {
            "Scenario A: Arthur Pendragon (CNC Machinist - Colorado)": {
                "name": "Arthur Pendragon",
                "trade_category": "CNC",
                "primary_trade": "5-Axis Machinist",
                "home_state": "CO",
                "skills": "G-code Programming; Haas Controls; Tight Tolerance Work; 5-Axis Programming",
                "certifications": "GD&T; Blueprint Reading; OSHA 10",
                "machine_brands": "Haas; Mazak",
                "controls": "Fanuc; Mazatrol",
                "willing_to_travel": True,
                "shift_preference": "1st shift",
                "prior_assignment_rating": 4.8,
                "availability_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                "missing_information_flags": "",
                "status": "Active"
            },
            "Scenario B: Morgana LeFay (PLC Maintenance Tech - Texas)": {
                "name": "Morgana LeFay",
                "trade_category": "Maintenance",
                "primary_trade": "Industrial Maintenance Tech",
                "home_state": "TX",
                "skills": "PLC Troubleshooting; VFD Drives; Panel Building; Motor Controls",
                "certifications": "Electrical Safety; OSHA 10; Forklift",
                "machine_brands": "Allen-Bradley; Siemens",
                "controls": "PLC; HMI",
                "willing_to_travel": False,
                "shift_preference": "2nd shift",
                "prior_assignment_rating": 4.9,
                "availability_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
                "missing_information_flags": "",
                "status": "Active"
            },
            "Scenario C: Lancelot DuLac (AWS Welder - Utah)": {
                "name": "Lancelot DuLac",
                "trade_category": "Welding",
                "primary_trade": "Pipe Welder",
                "home_state": "UT",
                "skills": "TIG Welding; MIG Welding; Stainless Steel; Aluminum Welding",
                "certifications": "AWS D1.1; OSHA 30",
                "machine_brands": "Lincoln; Miller",
                "controls": "",
                "willing_to_travel": True,
                "shift_preference": "Any",
                "prior_assignment_rating": 4.6,
                "availability_date": datetime.now().strftime("%Y-%m-%d"),
                "missing_information_flags": "",
                "status": "Active"
            }
        }

        # Styled resume mockup view
        active_scen = scenarios_data[scen]
        st.markdown(
            f"""
            <div style="background:#f1f5f9; border-radius:8px; border:1px solid #cbd5e1; padding:16px; font-family:monospace; font-size:0.8rem; margin:10px 0;">
                <h4 style="margin:0 0 8px 0; color:#1e3a8a;">📄 RESUME PLAIN TEXT STREAM (SIMULATED UPLOAD)</h4>
                <strong>NAME:</strong> {active_scen['name']}<br>
                <strong>EMAIL:</strong> {active_scen['name'].lower().replace(' ','')}@mock-email.com · <strong>TEL:</strong> +1 (555) 019-2834<br>
                <strong>EXPERIENCE:</strong> 8+ years hands-on specializing in {active_scen['primary_trade']}.<br>
                <strong>SKILLS & HARDWARE:</strong> {active_scen['skills']}<br>
                <strong>CONTROLS & BRANDS:</strong> {active_scen['machine_brands']} - {active_scen['controls']}<br>
                <strong>CERTIFICATIONS:</strong> {active_scen['certifications']}<br>
                <strong>PREFERENCES:</strong> Willing to travel: {active_scen['willing_to_travel']} · Shift: {active_scen['shift_preference']} · State: {active_scen['home_state']}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.file_uploader("Or drag and drop a real PDF/Word resume file here to simulate upload", type=["pdf","docx","txt"], key="demo_file_up")

        if st.button("🚀 Simulate AI Resume Parse & Save to DB", key="demo_parse_btn"):
            p_bar = st.progress(0)
            status_text = st.empty()
            
            steps = [
                ("📂 Opening uploaded file and extracting text bytes...", 15),
                ("🧠 Contacting Gemini 1.5 Flash parsing gateway...", 45),
                ("📝 Extracting structural credentials, travel readiness, and trade category...", 70),
                ("🔐 Opening secure Supabase database session...", 85),
                (f"💾 Inserting parsed profile '{active_scen['name']}' into 'workers' table... Success!", 100),
            ]
            
            import time
            for msg, pct in steps:
                status_text.markdown(f"**{msg}**")
                p_bar.progress(pct)
                time.sleep(0.4)
                
            # Create full worker row matches
            new_worker = {
                "worker_id": f"W-NEW-{len(st.session_state.added_workers) + 1:03d}",
                "worker_name": active_scen["name"],
                "primary_trade": active_scen["primary_trade"],
                "trade_category": active_scen["trade_category"],
                "home_state": active_scen["home_state"],
                "skills": active_scen["skills"],
                "certifications": active_scen["certifications"],
                "machine_brands": active_scen["machine_brands"],
                "controls": active_scen["controls"],
                "materials_experience": "Aluminum; Steel",
                "industry_experience": "Aerospace; Precision Manufacturing",
                "cnc_mill_experience": active_scen["trade_category"] in ("CNC", "Tooling"),
                "five_axis_experience": active_scen["trade_category"] in ("CNC", "Tooling"),
                "setup_ability": active_scen["trade_category"] in ("CNC", "Tooling"),
                "preferred_locations": "Denver" if active_scen["home_state"] == "CO" else "Dallas",
                "preferred_region": active_scen["home_state"],
                "preferred_states": active_scen["home_state"],
                "willing_to_travel": active_scen["willing_to_travel"],
                "shift_preference": active_scen["shift_preference"],
                "prior_assignment_rating": active_scen["prior_assignment_rating"],
                "availability_date": pd.to_datetime(active_scen["availability_date"]),
                "current_assignment_id": "",
                "recruiter_owner": "Sarah Mitchell",
                "last_contact": pd.Timestamp.now().normalize(),
                "redeployment_status": "Not Started",
                "missing_information_flags": "",
                "recruiter_notes": "",
                "status": "Active",
                "notes": "Added via AI Parser Simulator."
            }
            
            # Check for duplicates in session state
            if any(w["worker_name"] == active_scen["name"] for w in st.session_state.added_workers):
                st.warning(f"Candidate '{active_scen['name']}' has already been parsed and added in this session!")
            else:
                st.session_state.added_workers.append(new_worker)
                st.success(
                    f"🎉 SUCCESS! '{active_scen['name']}' has been added to the database.  \n"
                    "**Go to the 'Candidate Matching' tab** and look at the candidate dropdown — they will "
                    "instantly appear and can be ranked against open roles!"
                )
                st.balloons()
                time.sleep(1.0)
                st.rerun()

    # ── SIMULATOR 2: STAGE 2 (Outbox logs)
    with sim_tab2:
        st.markdown("### 💬 Stage 2 Outbox Logs: Automated Outbound Dispatch")
        st.markdown(
            "This logs all simulated text messages and email packets sent during this session. "
            "In production, clicking dispatch triggers outbound Twilio SMS messages and SendGrid email packets to clients."
        )

        col_sms, col_email = st.columns(2)
        
        with col_sms:
            st.markdown("#### 💬 Twilio SMS Gateway Outbox")
            if not st.session_state.demo_sent_sms:
                st.info("No SMS outreach sent yet. Select a worker in the 'Submittal Packets' tab and click 'Simulate Twilio SMS' to log a text.")
            else:
                for msg in st.session_state.demo_sent_sms:
                    st.markdown(
                        f"""
                        <div style="background:#eff6ff; border-radius:12px; border-left:4px solid #1e70bf; padding:10px 14px; margin:8px 0; box-shadow:0 1px 2px rgba(0,0,0,0.05);">
                            <span style="font-size:0.72rem; color:#64748b; font-weight:700;">{msg['timestamp']} · TO: {msg['worker']} ({msg['phone']})</span>
                            <div style="font-size:0.85rem; color:#1e293b; font-family:sans-serif; margin-top:4px;">{msg['message']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with col_email:
            st.markdown("#### 📧 SendGrid Client Email Outbox")
            if not st.session_state.demo_sent_emails:
                st.info("No email submittal packets dispatched yet. Go to the 'Submittal Packets' tab and click 'Simulate SendGrid Client Email' to log a packet.")
            else:
                for email in st.session_state.demo_sent_emails:
                    st.markdown(
                        f"""
                        <div style="background:#fdf2f8; border-radius:12px; border-left:4px solid #ec4899; padding:10px 14px; margin:8px 0; box-shadow:0 1px 2px rgba(0,0,0,0.05);">
                            <span style="font-size:0.72rem; color:#64748b; font-weight:700;">{email['timestamp']} · RECIPIENT: {email['recipient']}</span><br>
                            <span style="font-size:0.8rem; color:#0f172a; font-weight:700;">SUBJ: {email['subject']}</span>
                            <div style="font-size:0.8rem; color:#334155; font-family:monospace; background:#fff; border:1px solid #fbcfe8; padding:8px; border-radius:6px; margin-top:6px; max-height:120px; overflow-y:auto; white-space:pre-wrap;">{email['body']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ── SIMULATOR 3: STAGE 3 (Client Review Portal)
    with sim_tab3:
        st.markdown("### 🤝 Stage 3 Simulator: Secure Client Review Portal")
        st.markdown(
            "Show your prospective client what their customer experiences when reviewing submittals. "
            "Click **[Approve for Interview]** to see the candidate automatically progress in the pipeline!"
        )

        st.markdown("#### Configure Review Scenario")
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            sel_pos_s3 = st.selectbox(
                "Select Active Position",
                pos["role"].dropna().unique().tolist() if not pos.empty else ["CNC Machinist"],
                key="s3_pos_select"
            )
            # Find the position row
            pos_row_s3 = pos[pos["role"] == sel_pos_s3].iloc[0] if not pos.empty else {"client_name": "Apex Precision", "position_id": "P001", "stage": "Sourcing"}
        with c_col2:
            s3_options = [f"{row['worker_name']} ({row['worker_id']})" for _, row in workers_live.iterrows()] if not workers_live.empty else ["John Doe"]
            sel_worker_s3 = st.selectbox(
                "Select Submitted Candidate",
                s3_options,
                key=f"s3_worker_select_{len(workers_live)}",
            )
            sel_wid_s3 = sel_worker_s3.split(" (")[-1].rstrip(")") if not workers_live.empty else ""
            worker_row_s3 = workers_live[workers_live["worker_id"] == sel_wid_s3].iloc[0] if not workers_live.empty else {"skills": "G-code; Fanuc", "certifications": "OSHA 10", "willing_to_travel": True}

        # Simulated browser frame
        st.markdown(
            f"""
            <div style="background:#0f172a; border-top-left-radius:8px; border-top-right-radius:8px; padding:6px 12px; color:#94a3b8; font-size:0.75rem; font-family:monospace; display:flex; align-items:center; gap:8px;">
                <span style="color:#ef4444; font-size:1.1rem; line-height:1;">●</span>
                <span style="color:#eab308; font-size:1.1rem; line-height:1;">●</span>
                <span style="color:#22c55e; font-size:1.1rem; line-height:1;">●</span>
                <span style="margin-left:10px; background:#1e293b; padding:2px 14px; border-radius:4px; width:70%; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
                    https://secure-portal.tradesresource.com/submittals/review-req-{pos_row_s3.get('position_id', 'P001')}
                </span>
            </div>
            <div style="border:1px solid #cbd5e1; border-top:none; background:#ffffff; border-bottom-left-radius:8px; border-bottom-right-radius:8px; padding:24px; box-shadow:0 10px 15px -3px rgba(0,0,0,0.1);">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #e2e8f0; padding-bottom:10px; margin-bottom:15px;">
                    <div>
                        <h4 style="margin:0; color:#1e3b8a; font-size:1.1rem; font-weight:800;">TRADES RESOURCE SUBMITTAL</h4>
                        <span style="font-size:0.75rem; color:#64748b; font-weight:600;">Secure Client Review Link · Req ID: {pos_row_s3.get('position_id', 'P001')}</span>
                    </div>
                    <div style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; padding:4px 10px; text-align:right;">
                        <span style="font-size:0.65rem; color:#475569; display:block; font-weight:700;">CLIENT ASSIGNED</span>
                        <strong style="font-size:0.8rem; color:#0f172a;">{pos_row_s3.get('client_name', 'Client')}</strong>
                    </div>
                </div>
                <div style="margin-bottom:15px;">
                    <span style="font-size:0.7rem; color:#64748b; text-transform:uppercase; font-weight:700; letter-spacing:0.5px;">CANDIDATE PROFILE</span>
                    <h3 style="margin:2px 0 0 0; color:#0f172a; font-weight:800; font-size:1.4rem;">{sel_worker_s3}</h3>
                    <span style="font-size:0.85rem; color:#1e70bf; font-weight:700;">Role under review: {sel_pos_s3}</span>
                </div>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:14px; margin-bottom:15px; font-size:0.82rem;">
                    <div>
                        <strong>Key Skills:</strong> {worker_row_s3.get('skills', 'G-code')}<br>
                        <strong>Certifications:</strong> {worker_row_s3.get('certifications', 'OSHA 10')}<br>
                        <strong>Travel-Ready:</strong> {"Yes" if worker_row_s3.get('willing_to_travel') else "No"}
                    </div>
                    <div>
                        <strong>Controls Experience:</strong> {worker_row_s3.get('controls', 'Fanuc') or 'N/A'}<br>
                        <strong>Shift Preference:</strong> {worker_row_s3.get('shift_preference', 'Any')}<br>
                        <strong>Prior Rating:</strong> ⭐ {worker_row_s3.get('prior_assignment_rating', '4.5')} / 5.0
                    </div>
                </div>
                <div style="background:#eff6ff; border-left:4px solid #1e70bf; padding:10px; border-radius:4px; font-size:0.8rem; font-style:italic; color:#1e3a8a; line-height:1.4; margin-bottom:20px;">
                    <strong>Recruiter Recommendation Note:</strong> Excellent fit with deep hands-on exposure. Highly skilled and willing to travel. Fully verified shift preference and certifications. Highly recommended.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        col_app, col_pass = st.columns(2)
        
        with col_app:
            if st.button("✅ Approve for Interview (Stage 3 Demo)", key="s3_approve_btn"):
                if not pos.empty:
                    # Update stage override to "Interviewing"
                    pos_id_s3 = pos_row_s3.get("position_id")
                    st.session_state.position_overrides = update_position_override(
                        st.session_state.position_overrides,
                        pos_id_s3,
                        {"intake_complete": True, "stage": "Interviewing", "priority": pos_row_s3.get("priority", "High"), "notes": f"Client approved {sel_worker_s3} for interview!"}
                    )
                    st.success(
                        f"🎉 SUCCESS! Client has APPROVED '{sel_worker_s3}' for the '{sel_pos_s3}' role.  \n"
                        f"**The position '{pos_id_s3}' stage has been updated to 'Interviewing'!**  \n"
                        "Check the 'Today Dashboard' (Section C/D) or 'Open Positions' tab to see this candidate in the live pipeline!"
                    )
                    st.balloons()
                    time.sleep(1.0)
                    st.rerun()
                else:
                    st.error("No active positions to update.")

        with col_pass:
            if st.button("❌ Pass on Candidate (Stage 3 Demo)", key="s3_pass_btn"):
                st.info("Simulated client response: Passed. Pipeline remains unchanged. No changes made.")
