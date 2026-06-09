"""
components.py
Reusable Streamlit UI components: KPI cards, status badges, tables, sidebar filters.

All HTML templates use CSS custom properties (var(--...)) so they automatically
respond to the active theme set in app.py.
"""

import streamlit as st
import pandas as pd
from typing import Optional

# ---------------------------------------------------------------------------
# KPI card  — uses CSS vars so dark/light themes both look correct
# ---------------------------------------------------------------------------

def kpi_card(label: str, value, color: str = "#1E88E5", sub: str = "") -> str:
    """Return an HTML string for a styled KPI card."""
    return f"""
    <div style="
        background: var(--card-bg, #ffffff);
        border: 1px solid var(--card-border, #e2e8f0);
        border-left: 5px solid {color};
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08), 0 2px 4px -1px rgba(0,0,0,0.04);
        min-height: 105px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.2s, box-shadow 0.2s;
    ">
        <div style="font-size:2.2rem;font-weight:800;color:{color};line-height:1.1;">{value}</div>
        <div style="font-size:0.82rem;color:var(--metric-label,#475569);margin-top:6px;font-weight:700;letter-spacing:0.5px;">{label.upper()}</div>
        {f'<div style="font-size:0.72rem;color:var(--caption-color,#64748b);margin-top:4px;font-weight:500;">{sub}</div>' if sub else ""}
    </div>
    """


def render_kpi_row(cards: list):
    """
    Render a row of KPI cards.
    cards = list of dicts: {label, value, color, sub}
    """
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                kpi_card(
                    card["label"],
                    card["value"],
                    card.get("color", "#1E88E5"),
                    card.get("sub", ""),
                ),
                unsafe_allow_html=True,
            )
    st.markdown("<br>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Status badge
# ---------------------------------------------------------------------------

BADGE_COLORS = {
    "Critical":            ("#7B0000", "#FFB3B3"),
    "Red":                 ("#E53935", "#FFCDD2"),
    "Orange":              ("#FB8C00", "#FFE0B2"),
    "Yellow":              ("#9E7700", "#FFF9C4"),
    "Green":               ("#1B5E20", "#C8E6C9"),
    "High":                ("#C62828", "#FFCDD2"),
    "Medium":              ("#E65100", "#FFE0B2"),
    "Low":                 ("#1B5E20", "#C8E6C9"),
    "Active":              ("#0D47A1", "#BBDEFB"),
    "Complete":            ("#1B5E20", "#C8E6C9"),
    "Overdue":             ("#B71C1C", "#FFCDD2"),
    "Pending":             ("#0F52BA", "#EBF3FF"),
    "In Progress":         ("#01579B", "#B3E5FC"),
    "Filled":              ("#1B5E20", "#C8E6C9"),
    "On Hold":             ("#37474F", "#CFD8DC"),
    # Trades Resource Forecasting Badges
    "Redeployment needed": ("#C62828", "#FFCDD2"),
    "Ending soon":         ("#E53935", "#FFCDD2"),
    "Renewal needed":      ("#FB8C00", "#FFE0B2"),
    "Extension pending":   ("#0F52BA", "#EBF3FF"),
    "Time off upcoming":   ("#0277BD", "#E1F5FE"),
    "Check-in needed":     ("#006064", "#E0F7FA"),
    "Active / healthy":    ("#1B5E20", "#C8E6C9"),
    "At Risk":             ("#C62828", "#FFCDD2"),
    "Pending Extension":   ("#0F52BA", "#EBF3FF"),
    "Healthy":             ("#1B5E20", "#C8E6C9"),
    # Recruiter Process Tracker Badges
    "Ready":               ("#1B5E20", "#C8E6C9"),
    "Needs update":        ("#E65100", "#FFE0B2"),
    "Needs Update":        ("#E65100", "#FFE0B2"),
    "Submitted":           ("#0277BD", "#E1F5FE"),
    "Pending Welder Safety":     ("#B71C1C", "#FFCDD2"),
    "Pending CNC Proficiency":   ("#B71C1C", "#FFCDD2"),
    "Pay rate, availability":    ("#E53935", "#FFCDD2"),
    "Travel preference":         ("#E65100", "#FFE0B2"),
    "Certifications":            ("#E53935", "#FFCDD2"),
}


def badge(text: str, level: str = "") -> str:
    bg, fg_contrast = BADGE_COLORS.get(level, BADGE_COLORS.get(text, ("#37474F", "#E0E0E0")))
    return (
        f'<span style="background:{fg_contrast};color:{bg};'
        f'border-radius:4px;padding:2px 8px;font-size:0.78rem;'
        f'font-weight:700;white-space:nowrap;">{text}</span>'
    )


def urgency_badge(urgency: str) -> str:
    return badge(urgency, urgency)


def priority_badge(priority: str) -> str:
    return badge(priority, priority)


# ---------------------------------------------------------------------------
# Section header  — uses CSS vars
# ---------------------------------------------------------------------------

def section_header(title: str, subtitle: str = "", icon: str = ""):
    icon_str = f"{icon} " if icon else ""
    st.markdown(
        f"""
        <div style="margin:24px 0 12px 0;border-bottom:2px solid var(--divider-color,#e2e8f0);padding-bottom:6px;">
            <h2 style="color:var(--heading-color,#0f172a);font-weight:700;margin:0;font-size:1.3rem;display:flex;align-items:center;gap:8px;">
                <span>{icon_str}</span><span>{title}</span>
            </h2>
            {f'<p style="color:var(--caption-color,#475569);font-size:0.88rem;margin:4px 0 0 0;font-weight:500;">{subtitle}</p>' if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Alert row  — uses CSS vars
# ---------------------------------------------------------------------------

def alert_row(category: str, subject: str, detail: str, action: str,
              severity: str = "Orange", recruiter: str = ""):
    severity_colors = {
        "Critical": ("🔴", "#dc2626"),
        "Red":      ("🔴", "#ef4444"),
        "Orange":   ("🟠", "#f97316"),
        "Yellow":   ("🟡", "#d97706"),
        "Green":    ("🟢", "#16a34a"),
    }
    icon, accent = severity_colors.get(severity, ("⚪", "#475569"))

    st.markdown(
        f"""
        <div style="
            border-left: 5px solid {accent};
            background: var(--card-bg, #ffffff);
            border: 1px solid var(--card-border, #e2e8f0);
            border-left-width: 5px;
            border-radius: 8px;
            padding: 12px 18px;
            margin: 8px 0;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        ">
            <span style="font-size:1.1rem;flex-shrink:0;margin-top:2px;">{icon}</span>
            <div style="flex:1;">
                <div style="font-size:0.75rem;color:var(--caption-color,#64748b);text-transform:uppercase;
                     letter-spacing:0.6px;margin-bottom:3px;font-weight:600;">
                    {category}{(' · ' + recruiter) if recruiter else ''}
                </div>
                <div style="font-weight:700;color:var(--heading-color,#0f172a);font-size:0.95rem;">{subject}</div>
                <div style="color:var(--app-text,#334155);font-size:0.85rem;margin-top:2px;line-height:1.4;opacity:0.85;">{detail}</div>
                <div style="color:{accent};font-size:0.82rem;margin-top:5px;font-weight:700;display:flex;align-items:center;gap:4px;">
                    <span>→</span> <span>{action}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Styled dataframe display
# ---------------------------------------------------------------------------

def show_dataframe(
    df: pd.DataFrame,
    height: int = 400,
    hide_cols: list = None,
    use_container_width: bool = True,
):
    display = df.copy()
    if hide_cols:
        display = display.drop(columns=[c for c in hide_cols if c in display.columns], errors="ignore")
    for col in display.columns:
        if pd.api.types.is_datetime64_any_dtype(display[col]):
            display[col] = display[col].dt.strftime("%Y-%m-%d")
    st.dataframe(display, height=height, use_container_width=use_container_width)


def render_styled_table(df: pd.DataFrame, badge_cols: list = None, column_names: dict = None) -> str:
    """
    Converts a DataFrame to an elegant styled HTML table.
    Uses CSS custom properties throughout so the table adapts to all four themes.
    """
    display = df.copy()

    if column_names:
        display = display.rename(columns=column_names)

    cols = display.columns.tolist()

    html = """
    <div style="overflow-x:auto;border-radius:10px;border:1px solid var(--card-border,#e2e8f0);
         margin-top:15px;margin-bottom:20px;
         box-shadow:0 4px 12px rgba(0,0,0,0.08);">
    <table style="width:100%;border-collapse:collapse;text-align:left;
         font-family:'Inter','Segoe UI',sans-serif;font-size:0.85rem;
         color:var(--app-text,#1e293b);background-color:var(--card-bg,#ffffff);">
        <thead>
            <tr style="background:var(--accent-grad, linear-gradient(90deg, #1b5f8b 0%, #0e7fb5 100%));
                color:#ffffff;font-weight:700;text-transform:uppercase;
                font-size:0.72rem;letter-spacing:0.6px;">
    """

    for col in cols:
        html += f'<th style="padding:12px 16px;border-bottom:2px solid rgba(255,255,255,0.15);white-space:nowrap;">{col}</th>\n'

    html += """
            </tr>
        </thead>
        <tbody>
    """

    for idx, row in display.reset_index(drop=True).iterrows():
        # Alternating rows: use CSS vars with slight opacity overlay
        if idx % 2 == 1:
            row_bg = "background-color:var(--app-bg,#f8fafc);"
        else:
            row_bg = "background-color:var(--card-bg,#ffffff);"

        html += f'<tr style="{row_bg}border-bottom:1px solid var(--card-border,#f1f5f9);transition:background 0.15s;" ' \
                f'onmouseover="this.style.opacity=\'0.85\'" onmouseout="this.style.opacity=\'1\'">'

        for col in cols:
            val = row[col]
            if pd.isna(val) or val is None:
                val_str = ""
            else:
                if hasattr(val, "strftime"):
                    val_str = val.strftime("%Y-%m-%d")
                elif isinstance(val, float):
                    val_str = f"{val:,.2f}"
                elif isinstance(val, bool):
                    val_str = "Yes" if val else "No"
                else:
                    val_str = str(val)

            is_badge = False
            if badge_cols:
                orig_col = col
                if column_names:
                    for k, v in column_names.items():
                        if v == col:
                            orig_col = k
                            break
                if col in badge_cols or orig_col in badge_cols:
                    is_badge = True

            if is_badge and val_str.strip():
                if "," in val_str and ("Fields" in col or "fields" in col):
                    badges_html = " ".join([badge(s.strip(), s.strip()) for s in val_str.split(",")])
                    html += f'<td style="padding:10px 16px;vertical-align:middle;">{badges_html}</td>'
                else:
                    html += f'<td style="padding:10px 16px;vertical-align:middle;">{badge(val_str, val_str)}</td>'
            else:
                if val_str == "Yes":
                    html += f'<td style="padding:12px 16px;vertical-align:middle;font-weight:600;color:#16a34a;">{val_str}</td>'
                elif val_str == "No":
                    html += f'<td style="padding:12px 16px;vertical-align:middle;color:#dc2626;">{val_str}</td>'
                else:
                    html += f'<td style="padding:12px 16px;vertical-align:middle;line-height:1.4;color:var(--app-text,#1e293b);">{val_str}</td>'

        html += "</tr>\n"

    html += """
        </tbody>
    </table>
    </div>
    """
    return html.replace("\n", "").replace("\r", "")


# ---------------------------------------------------------------------------
# CSV download button
# ---------------------------------------------------------------------------

def csv_download_button(df: pd.DataFrame, filename: str, label: str = "⬇ Download CSV"):
    csv = df.copy()
    for col in csv.columns:
        if pd.api.types.is_datetime64_any_dtype(csv[col]):
            csv[col] = csv[col].dt.strftime("%Y-%m-%d")
    st.download_button(
        label=label,
        data=csv.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

def sidebar_multiselect(label: str, options: list, key: str, default_all: bool = True):
    all_options = sorted([str(o) for o in options if pd.notna(o) and str(o).strip()])
    default = all_options if default_all else []
    return st.sidebar.multiselect(label, all_options, default=default, key=key)


def apply_multiselect_filter(df: pd.DataFrame, col: str, selected: list) -> pd.DataFrame:
    if not selected:
        return df
    return df[df[col].astype(str).isin([str(s) for s in selected])]


# ---------------------------------------------------------------------------
# Workload label chip
# ---------------------------------------------------------------------------

def workload_chip(label: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:#fff;'
        f'border-radius:12px;padding:3px 10px;font-size:0.78rem;'
        f'font-weight:700;">{label}</span>'
    )


# ---------------------------------------------------------------------------
# Page intro banner  — gradient always visible regardless of theme
# ---------------------------------------------------------------------------

def page_banner(title: str, description: str, icon: str = "📊", decision_label: str = ""):
    decision_html = ""
    if decision_label:
        decision_html = (
            f'<div style="margin-top:10px;background:rgba(255,255,255,0.14);border-radius:6px;'
            f'padding:7px 12px;display:inline-block;">'
            f'<span style="color:#ffffff !important;font-size:0.8rem;font-weight:700;'
            f'opacity:0.95;letter-spacing:0.2px;">💡 {decision_label}</span></div>'
        )
    st.markdown(
        f"""
        <div class="custom-page-banner" style="
            background: var(--accent-grad, linear-gradient(135deg, #1b5f8b 0%, #0e7fb5 100%));
            border-radius: 12px;
            padding: 24px 28px;
            margin-bottom: 24px;
            border: 1px solid var(--card-border, rgba(255,255,255,0.15));
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        ">
            <div style="font-size:2.2rem;margin-bottom:8px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.2));">{icon}</div>
            <h1 style="color:#FFFFFF !important;font-size:1.65rem;font-weight:800;margin:0;letter-spacing:-0.5px;">{title}</h1>
            <p style="color:#ffffff !important;font-size:0.92rem;margin:8px 0 0 0;font-weight:500;line-height:1.4;opacity:0.95;">{description}</p>
            {decision_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
