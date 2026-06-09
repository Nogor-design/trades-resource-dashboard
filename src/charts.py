"""
charts.py
Plotly chart builders for the Trades Resource Command Center.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

TODAY = pd.Timestamp.now().normalize()


def get_theme_colors():
    """Returns (bg_color, text_color, grid_color, zeroline_color, today_line_color) based on the active theme."""
    try:
        import streamlit as st
        theme = st.session_state.get("app_theme", "Light Corporate")
    except:
        theme = "Light Corporate"

    if theme == "Dark Mode":
        return "#1c2128", "#e2e8f0", "rgba(240, 246, 252, 0.08)", "rgba(240, 246, 252, 0.3)", "#58a6ff"
    elif theme == "Steel & Slate":
        return "#1e2d3d", "#d4e0f0", "rgba(212, 224, 240, 0.08)", "rgba(212, 224, 240, 0.3)", "#4db8e8"
    elif theme == "Executive Gold":
        return "#161410", "#f0e6c8", "rgba(240, 230, 200, 0.08)", "rgba(240, 230, 200, 0.3)", "#f0c040"
    else: # Light Corporate
        return "#ffffff", "#0f172a", "rgba(15, 23, 42, 0.08)", "rgba(15, 23, 42, 0.4)", "#1f5f8b"


# ---------------------------------------------------------------------------
# Gantt / Assignment Timeline chart
# ---------------------------------------------------------------------------

def build_timeline_chart(df: pd.DataFrame, highlight: str = "Show All") -> go.Figure:
    """
    Build a Plotly Gantt-style timeline for assignments.
    df must have: worker_name, client_name, role, recruiter_owner,
                  start_date, end_date, days_remaining, urgency,
                  urgency_color, recommended_action
    """
    bg_color, text_color, grid_color, zero_color, today_color = get_theme_colors()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No assignments to display", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=18, color=text_color))
        fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font=dict(color=text_color))
        return fig

    df = df.copy().sort_values("days_remaining")

    # Build color map
    color_map = {
        "Critical": "#7B0000",
        "Red":      "#E53935",
        "Orange":   "#FB8C00",
        "Yellow":   "#FDD835",
        "Green":    "#43A047",
    }

    # Create label for y-axis
    df["label"] = df["worker_name"] + " — " + df["client_name"]

    # Hover text
    df["hover"] = df.apply(lambda r: (
        f"<b>{r['worker_name']}</b><br>"
        f"Client: {r['client_name']}<br>"
        f"Role: {r['role']}<br>"
        f"Recruiter: {r['recruiter_owner']}<br>"
        f"Start: {str(r['start_date'])[:10]}<br>"
        f"End: {str(r['end_date'])[:10]}<br>"
        f"Projected End: {str(r.get('current_projected_end_date', r['end_date']))[:10]}<br>"
        f"Days Remaining: {r['days_remaining']}<br>"
        f"Status: <b>{r['urgency']}</b><br>"
        f"Forecast Status: {r.get('forecast_status', 'N/A')}<br>"
        f"Next Action: {r.get('recommended_action','')}"
    ), axis=1)

    # One trace per urgency level for clean legend
    fig = go.Figure()

    urgency_order = ["Critical", "Red", "Orange", "Yellow", "Green"]
    shown = set()

    for urgency in urgency_order:
        subset = df[df["urgency"] == urgency]
        if subset.empty:
            continue
        color = color_map[urgency]
        show_legend = urgency not in shown
        shown.add(urgency)

        for _, row in subset.iterrows():
            start = row["start_date"]
            end = row["end_date"]
            label = row["label"]
            days_rem = row["days_remaining"]
            redeploy_status = row.get("redeployment_status", "")
            ext_status = row.get("extension_status", "")

            # Calculate individual bar opacity based on the active marker highlight filter
            row_opacity = 1.0
            if highlight != "Show All":
                has_marker = False
                if highlight == "Worker Time Off (🔵)":
                    to_start = row.get("time_off_start")
                    if pd.notna(to_start) and str(to_start).strip() != "":
                        has_marker = True
                elif highlight == "Renewal Due (🟡)":
                    ren_due = row.get("renewal_due_date")
                    if pd.notna(ren_due) and str(ren_due).strip() != "":
                        has_marker = True
                elif highlight == "Ending in 14d (🟠)":
                    if 7 < days_rem <= 14:
                        has_marker = True
                elif highlight == "Ending in 7d (❌)":
                    if 0 <= days_rem <= 7:
                        has_marker = True
                elif highlight == "Extension Pending (🔷)":
                    if ext_status == "Extension pending":
                        has_marker = True
                elif highlight == "Redeployment Confirmed (⭐)":
                    if redeploy_status in ["Redeployed", "Matched to Open Role"]:
                        has_marker = True
                
                row_opacity = 1.0 if has_marker else 0.18

            # Clamp display range to reasonable window
            display_start = max(start, TODAY - pd.Timedelta(days=60))

            fig.add_trace(go.Bar(
                x=[(end - display_start).days],
                y=[label],
                base=[(display_start - TODAY).days],
                orientation="h",
                marker_color=color,
                name=urgency,
                legendgroup=urgency,
                showlegend=show_legend,
                hovertext=row["hover"],
                hoverinfo="text",
                text=f"  {row['role']}  ({row['days_remaining']}d)" if row["days_remaining"] > 10 else "",
                textposition="inside",
                insidetextanchor="start",
                cliponaxis=False,
                opacity=row_opacity,
            ))
            show_legend = False  # only show legend for first bar in each urgency

    # Group overlay marker data by urgency level to link their visibility in the legend
    overlays = {
        urg: {
            "to_x": [], "to_y": [], "to_text": [],
            "ren_x": [], "ren_y": [], "ren_text": [],
            "end14_x": [], "end14_y": [], "end14_text": [],
            "end7_x": [], "end7_y": [], "end7_text": [],
            "ext_x": [], "ext_y": [], "ext_text": [],
            "redeploy_x": [], "redeploy_y": [], "redeploy_text": [],
        } for urg in urgency_order
    }

    for _, row in df.iterrows():
        label = row["label"]
        days_rem = row["days_remaining"]
        redeploy_status = row.get("redeployment_status", "")
        urgency = row["urgency"]
        if urgency not in overlays:
            continue

        # 1. Time off
        to_start = row.get("time_off_start")
        if pd.notna(to_start) and to_start != "":
            try:
                to_start_ts = pd.to_datetime(to_start)
                offset = (to_start_ts - TODAY).days
                overlays[urgency]["to_x"].append(offset)
                overlays[urgency]["to_y"].append(label)
                overlays[urgency]["to_text"].append(f"Worker Scheduled Time Off: {to_start[:10]} to {str(row.get('time_off_end',''))[:10]}")
            except:
                pass

        # 2. Renewal conversation due
        ren_due = row.get("renewal_due_date")
        if pd.notna(ren_due) and ren_due != "":
            try:
                ren_due_ts = pd.to_datetime(ren_due)
                offset = (ren_due_ts - TODAY).days
                overlays[urgency]["ren_x"].append(offset)
                overlays[urgency]["ren_y"].append(label)
                overlays[urgency]["ren_text"].append(f"Renewal Conversation Due: {str(ren_due)[:10]}")
            except:
                pass

        # 3. Ending in 14 days
        if 7 < days_rem <= 14:
            overlays[urgency]["end14_x"].append(days_rem)
            overlays[urgency]["end14_y"].append(label)
            overlays[urgency]["end14_text"].append(f"Assignment Ending in {int(days_rem)} Days")

        # 4. Ending in 7 days
        if 0 <= days_rem <= 7:
            overlays[urgency]["end7_x"].append(days_rem)
            overlays[urgency]["end7_y"].append(label)
            overlays[urgency]["end7_text"].append(f"Critical Ending in {int(days_rem)} Days")

        # 5. Extension decision pending
        ext_status = row.get("extension_status", "")
        if ext_status == "Extension pending":
            overlays[urgency]["ext_x"].append(days_rem)
            overlays[urgency]["ext_y"].append(label)
            overlays[urgency]["ext_text"].append("Extension Pending Decision")

        # 6. Redeployment confirmed
        if redeploy_status in ["Redeployed", "Matched to Open Role"]:
            overlays[urgency]["redeploy_x"].append(days_rem)
            overlays[urgency]["redeploy_y"].append(label)
            overlays[urgency]["redeploy_text"].append(f"Redeployment Plan Confirmed: {redeploy_status}")

    # Opacity and size calculations based on active highlight
    def get_marker_props(marker_type: str):
        is_highlighted = (highlight == marker_type)
        if highlight == "Show All":
            return 1.0, False  # opacity 1.0, not isolated
        elif is_highlighted:
            return 1.0, True   # opacity 1.0, isolated
        else:
            return 0.12, False # opacity 0.12, dimmed

    # 1. Worker Time Off
    to_opacity, to_hi = get_marker_props("Worker Time Off (🔵)")
    to_size = 18 if to_hi else 11

    # 2. Renewal Due
    ren_opacity, ren_hi = get_marker_props("Renewal Due (🟡)")
    ren_size = 19 if ren_hi else 12

    # 3. Ending in 14d
    end14_opacity, end14_hi = get_marker_props("Ending in 14d (🟠)")
    end14_size = 18 if end14_hi else 11

    # 4. Ending in 7d
    end7_opacity, end7_hi = get_marker_props("Ending in 7d (❌)")
    end7_size = 18 if end7_hi else 11

    # 5. Extension Pending
    ext_opacity, ext_hi = get_marker_props("Extension Pending (🔷)")
    ext_size = 19 if ext_hi else 12

    # 6. Redeployment Confirmed
    redeploy_opacity, redeploy_hi = get_marker_props("Redeployment Confirmed (⭐)")
    redeploy_size = 20 if redeploy_hi else 13

    # Add Scatter traces for overlays, grouped under their respective worker's urgency legendgroup
    for urgency in urgency_order:
        data = overlays[urgency]
        
        if data["to_x"]:
            fig.add_trace(go.Scatter(
                x=data["to_x"], y=data["to_y"], mode="markers",
                marker=dict(symbol="circle", size=to_size, color="#1E88E5", line=dict(color="#FFFFFF", width=1)),
                name="Worker Time Off", hovertext=data["to_text"], hoverinfo="text", 
                showlegend=False, opacity=to_opacity, legendgroup=urgency
            ))

        if data["ren_x"]:
            fig.add_trace(go.Scatter(
                x=data["ren_x"], y=data["ren_y"], mode="markers",
                marker=dict(symbol="diamond", size=ren_size, color="#FDD835", line=dict(color="#000000", width=1)),
                name="Renewal Due", hovertext=data["ren_text"], hoverinfo="text", 
                showlegend=False, opacity=ren_opacity, legendgroup=urgency
            ))

        if data["end14_x"]:
            fig.add_trace(go.Scatter(
                x=data["end14_x"], y=data["end14_y"], mode="markers",
                marker=dict(symbol="square", size=end14_size, color="#FB8C00", line=dict(color="#000000", width=1)),
                name="Ending in 14d", hovertext=data["end14_text"], hoverinfo="text", 
                showlegend=False, opacity=end14_opacity, legendgroup=urgency
            ))

        if data["end7_x"]:
            fig.add_trace(go.Scatter(
                x=data["end7_x"], y=data["end7_y"], mode="markers",
                marker=dict(symbol="x", size=end7_size, color="#E53935", line=dict(color="#FFFFFF", width=1.5)),
                name="Ending in 7d", hovertext=data["end7_text"], hoverinfo="text", 
                showlegend=False, opacity=end7_opacity, legendgroup=urgency
            ))

        if data["ext_x"]:
            fig.add_trace(go.Scatter(
                x=data["ext_x"], y=data["ext_y"], mode="markers",
                marker=dict(symbol="triangle-up", size=ext_size, color="#0F52BA", line=dict(color="#FFFFFF", width=1)),
                name="Extension Pending", hovertext=data["ext_text"], hoverinfo="text", 
                showlegend=False, opacity=ext_opacity, legendgroup=urgency
            ))

        if data["redeploy_x"]:
            fig.add_trace(go.Scatter(
                x=data["redeploy_x"], y=data["redeploy_y"], mode="markers",
                marker=dict(symbol="star", size=redeploy_size, color="#43A047", line=dict(color="#FFFFFF", width=1)),
                name="Redeployment Confirmed", hovertext=data["redeploy_text"], hoverinfo="text", 
                showlegend=False, opacity=redeploy_opacity, legendgroup=urgency
            ))

    # Dummy trace to force xaxis2 (top axis) tick labels to render in Plotly spanning the full range
    if not df.empty:
        fig.add_trace(go.Scatter(
            x=[-60, 180],
            y=[df["label"].iloc[0], df["label"].iloc[0]],
            mode="markers",
            marker=dict(opacity=0, size=1),
            showlegend=False,
            xaxis="x2"
        ))

    # Today vertical line
    fig.add_vline(x=0, line_width=2, line_dash="solid", line_color=today_color,
                  annotation_text="TODAY", annotation_position="top",
                  annotation_font_color=today_color, annotation_font_size=11)

    # X-axis ticks at -30, -14, 0, 7, 14, 30, 60, 90
    tick_vals = [-60, -30, -14, 0, 7, 14, 30, 60, 90, 120, 180]
    tick_texts = [(TODAY + pd.Timedelta(days=d)).strftime("%b %d") for d in tick_vals]

    fig.update_layout(
        barmode="stack",
        height=max(500, len(df) * 30 + 120),
        xaxis=dict(
            tickvals=tick_vals,
            ticktext=tick_texts,
            title="",
            showgrid=True,
            gridcolor=grid_color,
            zeroline=True,
            zerolinecolor=zero_color,
            zerolinewidth=2,
            side="bottom",
        ),
        xaxis2=dict(
            tickvals=tick_vals,
            ticktext=tick_texts,
            title="",
            showgrid=False,
            overlaying="x",
            side="top",
            matches="x",
        ),
        yaxis=dict(
            title="",
            autorange="reversed",
            tickfont=dict(size=11),
        ),
        legend=dict(
            title="Timeline Keys & Event Markers (Click to Toggle, Double-Click to Isolate)",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            itemclick="toggle",            # SINGLE-CLICK toggles this trace (back to default!)
            itemdoubleclick="toggleothers",# DOUBLE-CLICK shows only this trace (back to default!)
        ),
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, size=12),
        margin=dict(l=10, r=20, t=65, b=40),
        hoverlabel=dict(bgcolor=bg_color, font_color=text_color, bordercolor=grid_color),
    )
    return fig


# ---------------------------------------------------------------------------
# Assignments ending by week bar chart
# ---------------------------------------------------------------------------

def build_endings_by_week(df: pd.DataFrame) -> go.Figure:
    """Bar chart: how many assignments end each week over the next 12 weeks."""
    bg_color, text_color, grid_color, zero_color, today_color = get_theme_colors()
    if df.empty:
        fig = go.Figure()
        fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font=dict(color=text_color))
        return fig

    df = df.copy()
    df = df[df["days_remaining"].between(0, 90)]
    if df.empty:
        fig = go.Figure()
        fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font=dict(color=text_color))
        return fig

    df["week_label"] = df["end_date"].dt.to_period("W").apply(
        lambda p: p.start_time.strftime("Week of %b %d")
    )
    counts = df.groupby("week_label").size().reset_index(name="count")

    colors = ["#43A047" if i > 30 else "#FB8C00" if i > 14 else "#E53935"
              for i in range(len(counts))]

    fig = go.Figure(go.Bar(
        x=counts["week_label"],
        y=counts["count"],
        marker_color=today_color,
        text=counts["count"],
        textposition="outside",
    ))
    fig.update_layout(
        title="Assignments Ending by Week (Next 90 Days)",
        xaxis_title="",
        yaxis_title="# Assignments",
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, size=12),
        margin=dict(l=10, r=10, t=50, b=80),
        xaxis=dict(tickangle=-35, showgrid=False),
        yaxis=dict(gridcolor=grid_color, showgrid=True),
        height=340,
    )
    return fig


# ---------------------------------------------------------------------------
# Open positions by stage donut chart
# ---------------------------------------------------------------------------

def build_positions_by_stage(df: pd.DataFrame) -> go.Figure:
    bg_color, text_color, grid_color, zero_color, today_color = get_theme_colors()
    if df.empty:
        fig = go.Figure()
        fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font=dict(color=text_color))
        return fig

    stage_counts = df.groupby("stage").size().reset_index(name="count")

    palette = [
        "#1E88E5", "#43A047", "#FB8C00", "#E53935", "#0F52BA",
        "#00ACC1", "#F4511E", "#3949AB", "#00897B", "#7CB342",
    ]

    fig = go.Figure(go.Pie(
        labels=stage_counts["stage"],
        values=stage_counts["count"],
        hole=0.5,
        marker_colors=palette[:len(stage_counts)],
        textinfo="label+value",
        hoverinfo="label+value+percent",
    ))
    fig.update_layout(
        title="Open Positions by Stage",
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, size=12),
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(font=dict(size=11)),
        height=340,
    )
    return fig


# ---------------------------------------------------------------------------
# Recruiter workload bar chart
# ---------------------------------------------------------------------------

def build_recruiter_workload_chart(workload_df: pd.DataFrame) -> go.Figure:
    bg_color, text_color, grid_color, zero_color, today_color = get_theme_colors()
    if workload_df.empty:
        fig = go.Figure()
        fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font=dict(color=text_color))
        return fig

    fig = go.Figure()
    metrics = [
        ("open_positions", "Open Positions", "#1E88E5"),
        ("high_priority_positions", "High Priority Positions", "#E53935"),
        ("ending_soon", "Ending in 30 Days", "#FB8C00"),
        ("overdue_actions", "Overdue Actions", "#7B0000"),
    ]
    for col, name, color in metrics:
        fig.add_trace(go.Bar(
            name=name,
            x=workload_df["recruiter"],
            y=workload_df[col],
            marker_color=color,
            text=workload_df[col],
            textposition="outside",
        ))

    fig.update_layout(
        barmode="group",
        title="Recruiter Workload Breakdown",
        xaxis_title="",
        yaxis_title="Count",
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=60, b=40),
        height=380,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=grid_color, showgrid=True),
    )
    return fig


# ---------------------------------------------------------------------------
# Overdue actions by recruiter
# ---------------------------------------------------------------------------

def build_overdue_by_recruiter(activity_df: pd.DataFrame) -> go.Figure:
    bg_color, text_color, grid_color, zero_color, today_color = get_theme_colors()
    if activity_df.empty:
        fig = go.Figure()
        fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font=dict(color=text_color))
        return fig

    overdue = activity_df[activity_df.get("is_overdue", False) == True] if "is_overdue" in activity_df.columns else pd.DataFrame()
    if overdue.empty:
        fig = go.Figure()
        fig.add_annotation(text="No overdue actions 🎉", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="#43A047"))
        fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color,
                          font=dict(color=text_color, size=12), height=260)
        return fig

    counts = overdue.groupby("recruiter_name").size().reset_index(name="overdue_count")
    fig = go.Figure(go.Bar(
        x=counts["recruiter_name"],
        y=counts["overdue_count"],
        marker_color="#E53935",
        text=counts["overdue_count"],
        textposition="outside",
    ))
    fig.update_layout(
        title="Overdue Actions by Recruiter",
        xaxis_title="",
        yaxis_title="# Overdue",
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, size=12),
        margin=dict(l=10, r=10, t=50, b=40),
        height=300,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=grid_color, showgrid=True),
    )
    return fig


# ---------------------------------------------------------------------------
# Priority breakdown for open positions
# ---------------------------------------------------------------------------

def build_priority_breakdown(df: pd.DataFrame) -> go.Figure:
    bg_color, text_color, grid_color, zero_color, today_color = get_theme_colors()
    if df.empty:
        fig = go.Figure()
        fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font=dict(color=text_color))
        return fig

    counts = df.groupby("priority").size().reset_index(name="count")
    color_map = {"High": "#E53935", "Medium": "#FB8C00", "Low": "#43A047"}
    colors = [color_map.get(p, "#9E9E9E") for p in counts["priority"]]

    fig = go.Figure(go.Bar(
        x=counts["priority"],
        y=counts["count"],
        marker_color=colors,
        text=counts["count"],
        textposition="outside",
    ))
    fig.update_layout(
        title="Open Positions by Priority",
        xaxis_title="",
        yaxis_title="Count",
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, size=12),
        margin=dict(l=10, r=10, t=50, b=40),
        height=300,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=grid_color, showgrid=True),
    )
    return fig
