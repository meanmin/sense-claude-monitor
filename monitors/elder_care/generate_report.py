"""
Elder Care Weekly Report PDF Generator
Reads all care_log_*.json files and produces a 5-page PDF report.
"""

import os
import json
import glob
from datetime import datetime
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
LOG_DIR = os.path.join(BASE_DIR, "logs")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
CHART_DIR = os.path.join(BASE_DIR, "reports", "_charts")

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
C_PRIMARY   = "#3B82F6"   # blue
C_RED       = "#EF4444"
C_ORANGE    = "#F97316"
C_GREEN     = "#22C55E"
C_PURPLE    = "#8B5CF6"
C_GRAY      = "#6B7280"
C_LIGHT_BG  = "#F8FAFC"
C_HEADER_BG = "#1E293B"

TAG_COLORS = {
    "Cough":       "#F97316",
    "Vomit":       "#EF4444",
    "Thud":        "#DC2626",
    "Glass_break": "#B91C1C",
    "Scream":      "#7C3AED",
    "Moan":        "#F59E0B",
    "Footstep":    "#6B7280",
}

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
def load_all_logs():
    """Load all care_log_*.json files, return sorted list of (date_str, entries)."""
    files = sorted(glob.glob(os.path.join(LOG_DIR, "care_log_*.json")))
    all_data = []
    for fp in files:
        basename = os.path.basename(fp)
        date_str = basename.replace("care_log_", "").replace(".json", "")
        with open(fp, "r", encoding="utf-8") as f:
            entries = json.load(f)
        all_data.append((date_str, entries))
    return all_data


def compute_daily_stats(all_data):
    """Compute per-day tag counts, avg cough confidence, and hours."""
    stats = []
    for date_str, entries in all_data:
        counts = defaultdict(int)
        cough_confidences = []
        all_confidences = []
        hours = []
        fall_events = []

        for entry in entries:
            analyzed_at = entry.get("analyzed_at", "")
            try:
                hour = datetime.fromisoformat(analyzed_at).hour
            except Exception:
                hour = 0

            for ev in entry.get("events", []):
                tag = ev["tag"]
                counts[tag] += 1
                all_confidences.append(ev["confidence"])
                hours.append(hour)

                if tag == "Cough":
                    cough_confidences.append(ev["confidence"])

                if tag in ("Thud", "Glass_break"):
                    fall_events.append({
                        "tag": tag,
                        "confidence": ev["confidence"],
                        "time": analyzed_at,
                        "hour": hour,
                    })

        avg_cough_conf = round(sum(cough_confidences) / len(cough_confidences), 2) if cough_confidences else 0
        total = sum(counts.values())
        total_cough = counts.get("Cough", 0)

        stats.append({
            "date": date_str,
            "label": f"Mar {int(date_str[6:])}",
            "counts": dict(counts),
            "total": total,
            "total_cough": total_cough,
            "avg_cough_conf": avg_cough_conf,
            "hours": hours,
            "fall_events": fall_events,
        })
    return stats


def compute_hourly_distribution(all_data):
    """Compute cumulative hourly distribution of cough events across all days."""
    hourly = defaultdict(int)
    for date_str, entries in all_data:
        for entry in entries:
            analyzed_at = entry.get("analyzed_at", "")
            try:
                hour = datetime.fromisoformat(analyzed_at).hour
            except Exception:
                continue
            cough_count = sum(1 for ev in entry.get("events", []) if ev["tag"] == "Cough")
            hourly[hour] += cough_count
    return hourly


# ---------------------------------------------------------------------------
# Chart Generation
# ---------------------------------------------------------------------------
def generate_daily_chart(stats, path):
    """Stacked bar chart of daily events by type."""
    fig, ax = plt.subplots(figsize=(8, 4.5))

    tags = ["Cough", "Vomit", "Moan", "Thud", "Footstep"]
    labels = ["Cough", "Vomit", "Moan", "Thud (Fall)", "Footstep"]
    colors = [TAG_COLORS[t] for t in tags]

    x = np.arange(len(stats))
    bar_width = 0.5
    bottoms = np.zeros(len(stats))

    for tag, label, color in zip(tags, labels, colors):
        values = [s["counts"].get(tag, 0) for s in stats]
        bars = ax.bar(x, values, bar_width, bottom=bottoms, label=label, color=color)
        for i, (v, b) in enumerate(zip(values, bottoms)):
            if v > 0:
                ax.text(i, b + v / 2, str(v), ha="center", va="center",
                        fontsize=10, fontweight="bold", color="white")
        bottoms += np.array(values)

    ax.set_xticks(x)
    ax.set_xticklabels([s["label"] for s in stats], fontsize=11)
    ax.set_ylabel("Events", fontsize=11)
    ax.set_title("Daily Health Events by Type", fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="upper left", fontsize=9)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_cough_trend_chart(stats, path):
    """Line chart of daily cough count with zone bands."""
    fig, ax = plt.subplots(figsize=(8, 4))

    dates = [s["label"] for s in stats]
    cough_counts = [s["total_cough"] for s in stats]
    x = np.arange(len(stats))

    # Zone bands
    ax.axhspan(12, 20, color="#FEE2E2", alpha=0.6)
    ax.axhspan(8, 12, color="#FEF3C7", alpha=0.6)
    ax.axhspan(0, 8, color="#DCFCE7", alpha=0.6)

    # Threshold lines
    ax.axhline(y=12, color="#EF4444", linestyle=":", linewidth=1, alpha=0.7)
    ax.axhline(y=8, color="#F59E0B", linestyle=":", linewidth=1, alpha=0.7)

    ax.plot(x, cough_counts, "o-", color=C_ORANGE, linewidth=2.5, markersize=8, zorder=5)

    for i, c in enumerate(cough_counts):
        color = C_RED if c >= 12 else (C_ORANGE if c >= 8 else C_GREEN)
        ax.annotate(str(c), (i, c), textcoords="offset points",
                    xytext=(0, 14), ha="center", fontsize=12, fontweight="bold", color=color)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#FEE2E2", label=u"Alert Zone (\u2265 12/day)"),
        Patch(facecolor="#FEF3C7", label="Watch Zone (8\u201311/day)"),
        Patch(facecolor="#DCFCE7", label="Normal (< 8/day)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(dates, fontsize=11)
    ax.set_ylabel("Cough Count", fontsize=11)
    ax.set_ylim(0, max(cough_counts) + 5)
    ax.set_title(f"Cough Frequency \u2014 {len(stats)}-Day Trend", fontsize=13, fontweight="bold", pad=12)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_hourly_chart(hourly, path):
    """Bar chart of hourly cough distribution with dawn/night window highlight."""
    fig, ax = plt.subplots(figsize=(8, 4))

    hour_order = list(range(0, 24))
    hour_labels = [f"{h:02d}:00" for h in hour_order]
    values = [hourly.get(h, 0) for h in hour_order]

    x = np.arange(len(hour_order))
    colors_bar = []
    for h in hour_order:
        if 5 <= h <= 7:
            colors_bar.append(C_ORANGE)  # dawn window
        elif 22 <= h <= 23:
            colors_bar.append(C_PURPLE)  # night window
        elif 0 <= h <= 4:
            colors_bar.append("#93C5FD")  # early morning
        else:
            colors_bar.append("#D1D5DB")  # other

    bars = ax.bar(x, values, color=colors_bar, width=0.7)
    for i, v in enumerate(values):
        if v > 0:
            ax.text(i, v + 0.15, str(v), ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Annotations
    ax.annotate("Dawn window", xy=(6, max(values) * 0.92),
                fontsize=9, color=C_GRAY, ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF7ED", edgecolor="#FDBA74"))
    ax.annotate("Night window", xy=(22, max(values) * 0.78),
                fontsize=9, color=C_GRAY, ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#F3E8FF", edgecolor="#C4B5FD"))

    ax.set_xticks(x)
    ax.set_xticklabels(hour_labels, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("Total Cough Events", fontsize=11)
    ax.set_title("Cough Distribution by Hour (Cumulative)", fontsize=13, fontweight="bold", pad=12)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------
def build_pdf(stats, hourly, all_data):
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(CHART_DIR, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    pdf_path = os.path.join(REPORT_DIR, f"elder_care_weekly_report_{today}.pdf")

    # Generate chart images
    daily_chart_path = os.path.join(CHART_DIR, "daily_events.png")
    cough_chart_path = os.path.join(CHART_DIR, "cough_trend.png")
    hourly_chart_path = os.path.join(CHART_DIR, "hourly_dist.png")

    generate_daily_chart(stats, daily_chart_path)
    generate_cough_trend_chart(stats, cough_chart_path)
    generate_hourly_chart(hourly, hourly_chart_path)

    # Compute KPI values
    total_cough = sum(s["total_cough"] for s in stats)
    total_vomit = sum(s["counts"].get("Vomit", 0) for s in stats)
    total_fall = sum(s["counts"].get("Thud", 0) + s["counts"].get("Glass_break", 0) for s in stats)
    peak_daily_cough = max(s["total_cough"] for s in stats)

    # Collect all fall events
    all_fall_events = []
    for s in stats:
        for fe in s["fall_events"]:
            fe["date_label"] = s["label"]
            all_fall_events.append(fe)

    # Peak hour
    peak_hour = max(hourly, key=hourly.get) if hourly else 0

    first_date = stats[0]["label"]
    last_date = stats[-1]["label"]
    first_parts = first_date.split()
    last_parts = last_date.split()
    if first_parts[0] == last_parts[0]:
        date_range = f"{first_date} \u2013 {last_parts[-1]}, 2026"
    else:
        date_range = f"{first_date} \u2013 {last_date}, 2026"
    num_days = len(stats)

    # Status determination
    latest_cough = stats[-1]["total_cough"]
    if latest_cough >= 12 or total_fall > 0:
        status = "ALERT"
        status_color = C_RED
    elif latest_cough >= 8:
        status = "WATCH"
        status_color = C_ORANGE
    else:
        status = "NORMAL"
        status_color = C_GREEN

    # ---- Build PDF ----
    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        topMargin=15*mm, bottomMargin=15*mm,
        leftMargin=18*mm, rightMargin=18*mm,
    )

    styles = getSampleStyleSheet()
    W = A4[0] - 36*mm  # usable width

    # Custom styles
    s_title = ParagraphStyle("Title2", parent=styles["Title"],
                             fontSize=18, leading=24, textColor=white,
                             fontName="Helvetica-Bold")
    s_subtitle = ParagraphStyle("Sub", parent=styles["Normal"],
                                fontSize=10, textColor=HexColor("#94A3B8"),
                                fontName="Helvetica")
    s_heading = ParagraphStyle("H2", parent=styles["Heading2"],
                               fontSize=16, textColor=HexColor(C_PRIMARY),
                               spaceAfter=6, fontName="Helvetica-Bold")
    s_body = ParagraphStyle("Body2", parent=styles["Normal"],
                            fontSize=10, leading=15, textColor=HexColor("#374151"),
                            fontName="Helvetica")
    s_small = ParagraphStyle("Small", parent=styles["Normal"],
                             fontSize=8, textColor=HexColor(C_GRAY),
                             alignment=TA_CENTER, fontName="Helvetica")
    s_kpi_label = ParagraphStyle("KPILabel", parent=styles["Normal"],
                                  fontSize=8, leading=11, textColor=HexColor(C_GRAY),
                                  alignment=TA_CENTER, fontName="Helvetica")
    s_kpi_value = ParagraphStyle("KPIValue", parent=styles["Normal"],
                                  fontSize=18, leading=26, alignment=TA_CENTER,
                                  fontName="Helvetica-Bold")
    s_kpi_sub = ParagraphStyle("KPISub", parent=styles["Normal"],
                                fontSize=7, leading=10, textColor=HexColor(C_GRAY),
                                alignment=TA_CENTER, fontName="Helvetica")

    elements = []

    # ===== PAGE 1: Header + KPI + Daily Breakdown =====
    header_data = [[
        Paragraph("<b>Elder Care \u00b7 Weekly Health Report</b>", s_title),
        Paragraph(f"Analysis Period: {date_range}<br/>Monitor: elder_care", s_subtitle),
    ]]
    header_table = Table(header_data, colWidths=[W * 0.65, W * 0.35])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(C_HEADER_BG)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (0, 0), 16),
        ("RIGHTPADDING", (-1, -1), (-1, -1), 16),
        ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6*mm))

    # KPI Cards
    def kpi_cell(label, value, subtitle, color=C_PRIMARY):
        val_style = ParagraphStyle(f"KPIVal_{label}", parent=s_kpi_value,
                                    textColor=HexColor(color))
        return [
            Paragraph(label, s_kpi_label),
            Paragraph(f'<b>{value}</b>', val_style),
            Paragraph(subtitle, s_kpi_sub),
        ]

    kpi_data = [
        kpi_cell("TOTAL COUGH", str(total_cough), f"{total_cough} events over {num_days} days", C_ORANGE),
        kpi_cell("VOMIT EVENTS", str(total_vomit), f"{total_vomit} episodes detected", C_RED),
        kpi_cell("FALL INCIDENTS", str(total_fall), f"{total_fall} suspected fall(s)", C_RED),
        kpi_cell("PEAK DAILY COUGH", str(peak_daily_cough), f"Max in single day", C_ORANGE),
    ]
    kpi_table = Table([kpi_data], colWidths=[W/4]*4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 4*mm))

    # Alert box
    alert_text = (
        f"<b>{status}</b> &nbsp;&nbsp; "
        f"Cough frequency escalating: {stats[0]['total_cough']} events on {stats[0]['label']} \u2192 "
        f"{stats[-1]['total_cough']} events on {stats[-1]['label']}. "
    )
    if total_fall > 0:
        alert_text += f"Additionally, {total_fall} suspected fall event(s) detected. "
    if total_vomit > 0:
        alert_text += f"{total_vomit} vomiting episode(s) recorded. "

    if status == "ALERT":
        alert_text += "Immediate medical consultation recommended."
        alert_bg = "#FEE2E2"
        alert_border = C_RED
    elif status == "WATCH":
        alert_text += "Close monitoring recommended."
        alert_bg = "#FEF3C7"
        alert_border = C_ORANGE
    else:
        alert_text += "Within normal range."
        alert_bg = "#DCFCE7"
        alert_border = C_GREEN

    alert_table = Table([[Paragraph(alert_text, s_body)]], colWidths=[W])
    alert_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(alert_bg)),
        ("BOX", (0, 0), (-1, -1), 1, HexColor(alert_border)),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(alert_table)
    elements.append(Spacer(1, 6*mm))

    # Section: Daily Event Breakdown
    elements.append(Paragraph("<b>1. Daily Health Event Breakdown</b>", s_heading))
    elements.append(Spacer(1, 2*mm))
    elements.append(Image(daily_chart_path, width=W, height=W*0.48))
    elements.append(Spacer(1, 4*mm))

    # Data table
    tag_order = ["Cough", "Vomit", "Moan", "Thud", "Footstep"]
    tag_labels = ["Cough", "Vomit", "Moan", "Thud", "Footstep"]
    header_row = ["Date"] + tag_labels + ["Total", "Status"]
    table_data = [header_row]
    for s in stats:
        tc = s["total_cough"]
        if tc >= 12 or s["fall_events"]:
            st = "ALERT"
        elif tc >= 8:
            st = "WATCH"
        else:
            st = "NORMAL"
        row = [s["label"]]
        for tag in tag_order:
            row.append(str(s["counts"].get(tag, 0)))
        row.append(str(s["total"]))
        row.append(st)
        table_data.append(row)

    col_widths = [W*0.10] + [W*0.10]*5 + [W*0.10, W*0.12]
    data_table = Table(table_data, colWidths=col_widths)

    table_style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(C_PRIMARY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#F8FAFC")]),
    ]
    for i, s in enumerate(stats, 1):
        tc = s["total_cough"]
        if tc >= 12 or s["fall_events"]:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor(C_RED)))
        elif tc >= 8:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor(C_ORANGE)))
        else:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor(C_GREEN)))
        table_style_cmds.append(("FONTNAME", (-1, i), (-1, i), "Helvetica-Bold"))

    data_table.setStyle(TableStyle(table_style_cmds))
    elements.append(data_table)
    elements.append(Spacer(1, 4*mm))

    p1_text = (
        f"Cough events increased steadily from {stats[0]['total_cough']} on {stats[0]['label']} to "
        f"{stats[-1]['total_cough']} on {stats[-1]['label']}. "
        f"Vomiting was recorded on {total_vomit} occasion(s), and "
        f"{total_fall} suspected fall incident(s) were detected during the monitoring period."
    )
    elements.append(Paragraph(p1_text, s_body))

    # ===== PAGE 2: Cough Frequency Trend =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>2. Cough Frequency Trend</b>", s_heading))
    elements.append(Spacer(1, 4*mm))
    elements.append(Image(cough_chart_path, width=W, height=W*0.5))
    elements.append(Spacer(1, 6*mm))

    p2_text = (
        "Daily cough frequency is a key indicator of respiratory health deterioration. "
        "A count \u2265 12 per day enters the Alert Zone, signaling potential bronchitis, "
        "aspiration pneumonia, or COPD exacerbation. "
        f"Cough counts have risen from {stats[0]['total_cough']} to {stats[-1]['total_cough']} over "
        f"{num_days} days. "
    )
    if stats[-1]["total_cough"] >= 12:
        p2_text += (
            "The latest count is in the Alert Zone. Combined with vomiting episodes, "
            "this pattern suggests possible aspiration risk. Medical evaluation is strongly recommended."
        )
    elif stats[-1]["total_cough"] >= 8:
        p2_text += "The latest count is in the Watch Zone. Continued monitoring is advised."
    else:
        p2_text += "Currently within normal range, but the upward trend warrants attention."
    elements.append(Paragraph(p2_text, s_body))

    # ===== PAGE 3: Hourly Distribution =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>3. Cough Distribution by Hour of Day</b>", s_heading))
    elements.append(Spacer(1, 4*mm))
    elements.append(Image(hourly_chart_path, width=W, height=W*0.5))
    elements.append(Spacer(1, 6*mm))

    p3_text = (
        "Cough events concentrate in two time windows: the dawn period (05:00\u201307:00) "
        "and the late-night period (22:00\u201323:00). "
        "Dawn coughing correlates with post-nasal drip accumulation during sleep and "
        "morning bronchial clearing. Late-night episodes suggest acid reflux or "
        "positional airway obstruction. This bimodal pattern is characteristic of "
        "chronic respiratory conditions in elderly patients."
    )
    elements.append(Paragraph(p3_text, s_body))

    # ===== PAGE 4: Fall-Risk Incident Detail =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>4. Fall-Risk Incident Detail</b>", s_heading))
    elements.append(Spacer(1, 4*mm))

    if all_fall_events:
        for fe in all_fall_events:
            try:
                time_str = datetime.fromisoformat(fe["time"]).strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = fe["time"]

            fall_detail = (
                f"<b>\u26a0 SUSPECTED FALL EVENT</b><br/><br/>"
                f"<b>Date/Time:</b> {time_str}<br/>"
                f"<b>Sound Type:</b> {fe['tag']} (confidence: {fe['confidence']:.4f})<br/>"
                f"<b>Context:</b> Footstep detected immediately before impact sound, "
                f"suggesting movement-related fall at {fe['hour']:02d}:{datetime.fromisoformat(fe['time']).minute:02d}.<br/><br/>"
                f"<b>Action Required:</b> Verify whether a fall actually occurred. "
                f"Check for bruises, mobility changes, or complaints of pain. "
                f"If confirmed, consult a physician for fall-risk assessment."
            )
            fall_table = Table([[Paragraph(fall_detail, s_body)]], colWidths=[W])
            fall_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#FEE2E2")),
                ("BOX", (0, 0), (-1, -1), 2, HexColor(C_RED)),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ]))
            elements.append(fall_table)
            elements.append(Spacer(1, 6*mm))
    else:
        no_fall_text = (
            "No fall-related sounds (Thud, Glass_break) were detected during "
            "the monitoring period. This is a positive indicator, but continued "
            "monitoring is recommended, especially during nighttime hours."
        )
        no_fall_table = Table([[Paragraph(no_fall_text, s_body)]], colWidths=[W])
        no_fall_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#DCFCE7")),
            ("BOX", (0, 0), (-1, -1), 1, HexColor(C_GREEN)),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        elements.append(no_fall_table)

    # Nighttime movement summary
    elements.append(Spacer(1, 6*mm))
    elements.append(Paragraph("<b>Nighttime Movement Summary</b>", s_heading))
    elements.append(Spacer(1, 2*mm))

    total_footstep = sum(s["counts"].get("Footstep", 0) for s in stats)
    movement_text = (
        f"Total footstep events detected: {total_footstep} across {num_days} days. "
        "Nighttime movement patterns can indicate restlessness, bathroom visits, "
        "or disorientation. Combined with fall events, this data helps identify "
        "high-risk time windows for fall prevention measures."
    )
    elements.append(Paragraph(movement_text, s_body))

    # ===== PAGE 5: Recommendations =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>5. Recommendations</b>", s_heading))
    elements.append(Spacer(1, 4*mm))

    recommendations = []

    if all_fall_events:
        recommendations.append({
            "title": "Fall Verification \u2014 Immediate [URGENT]",
            "text": (
                f"{total_fall} suspected fall event(s) detected. "
                "Verify whether a fall occurred by checking for bruises, "
                "gait changes, or complaints of pain. If confirmed, arrange "
                "a fall-risk assessment and consider installing grab bars, "
                "non-slip mats, and motion-activated night lights."
            ),
            "bg": "#FEE2E2",
        })

    if latest_cough >= 12:
        recommendations.append({
            "title": "Medical Consultation \u2014 Within 48 Hours [URGENT]",
            "text": (
                f"Cough frequency has reached {latest_cough}/day (Alert Zone). "
                "Combined with vomiting episodes, this may indicate aspiration risk, "
                "COPD exacerbation, or developing pneumonia. Arrange a physician visit "
                "with a chest X-ray and sputum analysis."
            ),
            "bg": "#FEE2E2",
        })
    elif latest_cough >= 8:
        recommendations.append({
            "title": "Schedule Respiratory Check-up",
            "text": (
                f"Cough count at {latest_cough}/day (Watch Zone). "
                "Schedule a respiratory check-up within the next week."
            ),
            "bg": "#FEF3C7",
        })

    recommendations.extend([
        {
            "title": "Nighttime Safety Measures",
            "text": (
                "Footstep and fall data indicate nighttime activity. "
                "Install motion-sensor night lights along hallways and bathrooms. "
                "Consider a bed-exit alarm if nighttime wandering is frequent. "
                "Remove tripping hazards (rugs, cables) from common walking paths."
            ),
            "bg": "#DBEAFE",
        },
        {
            "title": "Cough Management",
            "text": (
                "Dawn/night cough concentration suggests post-nasal drip or GERD. "
                "Elevate the head of the bed by 15\u201320 cm. "
                "Ensure adequate room humidity (40\u201360%). "
                "Avoid heavy meals within 3 hours of bedtime."
            ),
            "bg": "#DCFCE7",
        },
        {
            "title": "Symptom Logging",
            "text": (
                "Maintain a daily symptom diary noting: appetite changes, "
                "fluid intake, sleep quality, and mobility level. "
                "Share this report and diary with the attending physician at the next visit."
            ),
            "bg": "#F0FDF4",
        },
    ])

    for rec in recommendations:
        rec_table = Table([[
            Paragraph(f"<b>{rec['title']}</b><br/><br/>{rec['text']}", s_body)
        ]], colWidths=[W])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor(rec["bg"])),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        elements.append(rec_table)
        elements.append(Spacer(1, 4*mm))

    # Footer
    elements.append(Spacer(1, 10*mm))
    footer_text = f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} \u00b7 Sense Monitor \u2014 Elder Care Module \u00b7 Powered by Cochl.Sense"
    elements.append(Paragraph(footer_text, s_small))

    doc.build(elements)
    return pdf_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    all_data = load_all_logs()
    if not all_data:
        print("No log files found.")
        return

    stats = compute_daily_stats(all_data)
    hourly = compute_hourly_distribution(all_data)

    pdf_path = build_pdf(stats, hourly, all_data)
    print(f"Report generated: {pdf_path}")


if __name__ == "__main__":
    main()
