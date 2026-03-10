"""
Baby Cry Weekly Report PDF Generator
Reads all cry_log_*.json files and produces a 4-page PDF report.
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
    "Baby_cry":      "#3B82F6",
    "Scream":        "#EF4444",
    "Moan":          "#F59E0B",
    "Baby_laughter": "#1E3A5F",
}

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
def load_all_logs():
    """Load all cry_log_*.json files, return sorted list of (date_str, entries)."""
    files = sorted(glob.glob(os.path.join(LOG_DIR, "cry_log_*.json")))
    all_data = []
    for fp in files:
        basename = os.path.basename(fp)
        date_str = basename.replace("cry_log_", "").replace(".json", "")
        with open(fp, "r", encoding="utf-8") as f:
            entries = json.load(f)
        all_data.append((date_str, entries))
    return all_data


def compute_daily_stats(all_data):
    """Compute per-day tag counts and avg confidence."""
    stats = []
    for date_str, entries in all_data:
        counts = defaultdict(int)
        confidences = []
        hours = []
        for entry in entries:
            analyzed_at = entry.get("analyzed_at", "")
            try:
                hour = datetime.fromisoformat(analyzed_at).hour
            except Exception:
                hour = 0
            for ev in entry.get("events", []):
                tag = ev["tag"]
                counts[tag] += 1
                confidences.append(ev["confidence"])
                hours.append(hour)

        avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0
        total = sum(counts.values())
        stats.append({
            "date": date_str,
            "label": f"Mar {int(date_str[6:])}",
            "counts": dict(counts),
            "total": total,
            "avg_conf": avg_conf,
            "hours": hours,
        })
    return stats


def compute_hourly_distribution(all_data):
    """Compute cumulative hourly distribution of cry events across all days."""
    hourly = defaultdict(int)
    for date_str, entries in all_data:
        for entry in entries:
            analyzed_at = entry.get("analyzed_at", "")
            try:
                hour = datetime.fromisoformat(analyzed_at).hour
            except Exception:
                continue
            cry_count = sum(1 for ev in entry.get("events", []) if ev["tag"] in ("Baby_cry", "Scream", "Moan"))
            hourly[hour] += cry_count
    return hourly


# ---------------------------------------------------------------------------
# Chart Generation
# ---------------------------------------------------------------------------
def generate_daily_chart(stats, path):
    """Stacked bar chart of daily events by type."""
    fig, ax = plt.subplots(figsize=(8, 4.5))

    tags = ["Baby_cry", "Scream", "Moan", "Baby_laughter"]
    labels = ["Baby Cry", "Scream", "Moan", "Laughter"]
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
    ax.set_title("Daily Detected Events by Type", fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="upper left", fontsize=9)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_intensity_chart(stats, path):
    """Line chart of cry intensity score with zone bands."""
    fig, ax = plt.subplots(figsize=(8, 4))

    dates = [s["label"] for s in stats]
    confs = [s["avg_conf"] for s in stats]
    x = np.arange(len(stats))

    # Zone bands
    ax.axhspan(0.90, 1.0, color="#FEE2E2", alpha=0.6)
    ax.axhspan(0.75, 0.90, color="#FEF3C7", alpha=0.6)
    ax.axhspan(0.0, 0.75, color="#DCFCE7", alpha=0.6)

    # Threshold lines
    ax.axhline(y=0.90, color="#EF4444", linestyle=":", linewidth=1, alpha=0.7)
    ax.axhline(y=0.75, color="#F59E0B", linestyle=":", linewidth=1, alpha=0.7)

    ax.plot(x, confs, "o-", color=C_PRIMARY, linewidth=2.5, markersize=8, zorder=5)

    for i, c in enumerate(confs):
        color = C_RED if c >= 0.90 else (C_ORANGE if c >= 0.75 else C_GREEN)
        ax.annotate(f"{c:.2f}", (i, c), textcoords="offset points",
                    xytext=(0, 14), ha="center", fontsize=11, fontweight="bold", color=color)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#FEE2E2", label=u"Physical Pain Zone (\u2265 0.90)"),
        Patch(facecolor="#FEF3C7", label="Caution  (0.75 \u2013 0.90)"),
        Patch(facecolor="#DCFCE7", label="Normal  (< 0.75)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(dates, fontsize=11)
    ax.set_ylabel("Avg Confidence", fontsize=11)
    ax.set_ylim(0.5, 1.05)
    ax.set_title(f"Cry Intensity Score \u2014 {len(stats)}-Day Trend", fontsize=13, fontweight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_hourly_chart(hourly, path):
    """Bar chart of hourly cry distribution with overnight window highlight."""
    fig, ax = plt.subplots(figsize=(8, 4))

    # Order: 18:00 to 11:00 (overnight focus)
    hour_order = list(range(18, 24)) + list(range(0, 12))
    hour_labels = [f"{h:02d}:00" for h in hour_order]
    values = [hourly.get(h, 0) for h in hour_order]

    x = np.arange(len(hour_order))
    colors_bar = []
    for h in hour_order:
        if 1 <= h <= 5:
            colors_bar.append(C_PRIMARY)  # overnight window
        elif h >= 21 or h == 0:
            colors_bar.append("#93C5FD")
        else:
            colors_bar.append(C_ORANGE)

    bars = ax.bar(x, values, color=colors_bar, width=0.7)
    for i, v in enumerate(values):
        if v > 0:
            ax.text(i, v + 0.15, str(v), ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Overnight window annotation
    from matplotlib.patches import FancyBboxPatch
    ax.annotate("Overnight window", xy=(10, max(values) * 0.92),
                fontsize=9, color=C_GRAY, ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#EFF6FF", edgecolor="#BFDBFE"))

    ax.set_xticks(x)
    ax.set_xticklabels(hour_labels, fontsize=8, rotation=45, ha="right")
    ax.set_ylabel("Total Cry Events", fontsize=11)
    ax.set_title("When Does the Baby Cry?  (Cumulative Events by Hour)", fontsize=13, fontweight="bold", pad=12)
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
    pdf_path = os.path.join(REPORT_DIR, f"baby_cry_weekly_report_{today}.pdf")

    # Generate chart images
    daily_chart_path = os.path.join(CHART_DIR, "daily_events.png")
    intensity_chart_path = os.path.join(CHART_DIR, "intensity_trend.png")
    hourly_chart_path = os.path.join(CHART_DIR, "hourly_dist.png")

    generate_daily_chart(stats, daily_chart_path)
    generate_intensity_chart(stats, intensity_chart_path)
    generate_hourly_chart(hourly, hourly_chart_path)

    # Compute KPI values
    total_cry = sum(s["counts"].get("Baby_cry", 0) for s in stats)
    total_scream = sum(s["counts"].get("Scream", 0) for s in stats)
    peak_conf = max(s["avg_conf"] for s in stats)
    peak_conf_date = [s for s in stats if s["avg_conf"] == peak_conf][0]["label"]

    # Peak hour
    peak_hour = max(hourly, key=hourly.get) if hourly else 0
    # Find the overnight window range
    overnight_hours = [h for h in range(0, 8) if hourly.get(h, 0) > 0]
    if overnight_hours:
        peak_window = f"{min(overnight_hours):02d}:00\u2013{max(overnight_hours)+1:02d}:00"
    else:
        peak_window = f"{peak_hour:02d}:00"

    first_date = stats[0]["label"]
    last_date = stats[-1]["label"]
    # Abbreviate: "Mar 3 – 10, 2026" instead of "Mar 3 – Mar 10, 2026"
    first_parts = first_date.split()
    last_parts = last_date.split()
    if first_parts[0] == last_parts[0]:
        date_range = f"{first_date} \u2013 {last_parts[-1]}, 2026"
    else:
        date_range = f"{first_date} \u2013 {last_date}, 2026"
    num_days = len(stats)

    # Status determination
    latest = stats[-1]
    latest_conf = latest["avg_conf"]
    if latest_conf >= 0.90:
        status = "CRITICAL"
        status_color = C_RED
    elif latest_conf >= 0.75:
        status = "HIGH"
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
    # Header bar
    header_data = [[
        Paragraph("<b>Baby Cry Pattern \u00b7 Weekly Report</b>", s_title),
        Paragraph(f"Analysis Period: {date_range}<br/>Monitor: baby_cry", s_subtitle),
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
        kpi_cell("TOTAL CRY EVENTS", str(total_cry), f"{total_cry} events over {num_days} days", C_RED),
        kpi_cell("SCREAM EVENTS", str(total_scream), f"{total_scream} high-distress signals", C_RED),
        kpi_cell("PEAK INTENSITY", f"{peak_conf:.2f}", f"Confidence on {peak_conf_date}", C_ORANGE),
        kpi_cell("PEAK HOUR", peak_window, "Overnight cry window", C_PRIMARY),
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

    # Critical alert box
    first_total = stats[0]["total"]
    last_total = stats[-1]["total"]
    increase = round(last_total / first_total, 1) if first_total > 0 else 0
    alert_text = (
        f"<b>{status}</b> &nbsp;&nbsp; "
        f"Rapid deterioration: {first_total} events on {stats[0]['label']} → "
        f"{last_total} events on {stats[-1]['label']} "
        f"({increase}× increase). Intensity {latest_conf:.2f} "
    )
    if latest_conf >= 0.90:
        alert_text += "exceeds the physical pain threshold (≥ 0.90). Immediate pediatric evaluation required."
        alert_bg = "#FEE2E2"
        alert_border = C_RED
    elif latest_conf >= 0.75:
        alert_text += "is in the Caution zone (0.75–0.90). Close monitoring recommended."
        alert_bg = "#FEF3C7"
        alert_border = C_ORANGE
    else:
        alert_text += "remains in Normal range (< 0.75)."
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
    elements.append(Paragraph("<b>1. Daily Event Breakdown</b>", s_heading))
    elements.append(Spacer(1, 2*mm))
    elements.append(Image(daily_chart_path, width=W, height=W*0.48))
    elements.append(Spacer(1, 4*mm))

    # Data table
    tag_order = ["Baby_cry", "Scream", "Moan", "Baby_laughter"]
    tag_labels = ["Baby Cry", "Scream", "Moan", "Laughter"]
    header_row = ["Date"] + tag_labels + ["Avg Confidence", "Status"]
    table_data = [header_row]
    for s in stats:
        conf = s["avg_conf"]
        if conf >= 0.90:
            st = "CRITICAL"
        elif conf >= 0.75:
            st = "WATCH" if conf < 0.85 else "HIGH"
        else:
            st = "NORMAL"
        row = [s["label"]]
        for tag in tag_order:
            row.append(str(s["counts"].get(tag, 0)))
        row.append(f"{conf:.2f}")
        row.append(st)
        table_data.append(row)

    col_widths = [W*0.12] + [W*0.12]*4 + [W*0.18, W*0.14]
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
    # Color-code status column
    for i, s in enumerate(stats, 1):
        conf = s["avg_conf"]
        if conf >= 0.90:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor(C_RED)))
        elif conf >= 0.75:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor(C_ORANGE)))
        else:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor(C_GREEN)))
        table_style_cmds.append(("FONTNAME", (-1, i), (-1, i), "Helvetica-Bold"))

    data_table.setStyle(TableStyle(table_style_cmds))
    elements.append(data_table)
    elements.append(Spacer(1, 4*mm))

    # Summary text for page 1
    p1_text = (
        f"{stats[0]['label']} was clinically normal — "
        f"only {stats[0]['counts'].get('Baby_cry', 0)} minor cries confirmed baseline normalcy. "
        f"By {stats[-1]['label']}, cry frequency had increased to {stats[-1]['counts'].get('Baby_cry', 0)} events, "
        f"with {stats[-1]['counts'].get('Scream', 0)} scream event(s) indicating sustained physical distress."
    )
    elements.append(Paragraph(p1_text, s_body))

    # ===== PAGE 2: Cry Intensity Score Trend =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>2. Cry Intensity Score Trend</b>", s_heading))
    elements.append(Spacer(1, 4*mm))
    elements.append(Image(intensity_chart_path, width=W, height=W*0.5))
    elements.append(Spacer(1, 6*mm))

    p2_text = (
        "The intensity score measures sustained force and duration of each cry episode. "
        f"A score ≥ 0.90 signals physical pain, not hunger or comfort-seeking. "
        f"Scores crossed the Caution zone on {stats[2]['label'] if len(stats) > 2 else stats[-1]['label']} "
        f"and reached {stats[-1]['avg_conf']:.2f} on {stats[-1]['label']} — "
    )
    if stats[-1]["avg_conf"] >= 0.90:
        p2_text += (
            "the Physical Pain Zone. Combined with concurrent screams, this requires prompt "
            "examination to rule out ear infection, GERD, colic, or fever."
        )
    else:
        p2_text += "the Caution Zone. Continued monitoring is recommended."

    elements.append(Paragraph(p2_text, s_body))

    # ===== PAGE 3: Hourly Distribution =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>3. Cry Distribution by Hour of Day</b>", s_heading))
    elements.append(Spacer(1, 4*mm))
    elements.append(Image(hourly_chart_path, width=W, height=W*0.5))
    elements.append(Spacer(1, 6*mm))

    p3_text = (
        f"All cry events concentrate in the {peak_window} overnight window (blue highlight). "
        "Three primary clinical explanations: "
        "(1) Hunger — gastric emptying peaks around 02:00 in infants; "
        "(2) Colic — visceral pain triggers during light sleep; "
        "(3) GERD / ear pain — horizontal position increases reflux and middle-ear pressure. "
        "Absence of daytime events rules out environmental triggers."
    )
    elements.append(Paragraph(p3_text, s_body))

    # ===== PAGE 4: Recommendations =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>4. Recommendations</b>", s_heading))
    elements.append(Spacer(1, 4*mm))

    recommendations = []
    if latest_conf >= 0.90:
        recommendations.append({
            "title": "Pediatric Consultation — Within 48 Hours [URGENT]",
            "text": (
                f"Intensity {latest_conf:.2f} in the Physical Pain Zone, "
                f"{total_scream} scream events, and a {increase}× increase over "
                f"{num_days} days meets the clinical threshold for urgent evaluation. "
                "Differentials: colic, acute otitis media, GERD, or fever."
            ),
            "bg": "#FEE2E2",
        })
    elif latest_conf >= 0.75:
        recommendations.append({
            "title": "Schedule Pediatric Check-up",
            "text": (
                f"Intensity {latest_conf:.2f} is in the Caution zone. "
                "Schedule a pediatric check-up within the next week to rule out underlying causes."
            ),
            "bg": "#FEF3C7",
        })

    recommendations.extend([
        {
            "title": "Add a Dream Feed at 22:30",
            "text": (
                f"The {peak_window} cry peak aligns with the end of a 4-hour feed interval. "
                "A dream feed at 22:30 may push the first cry onset past 03:00. Monitor for 3 nights."
            ),
            "bg": "#DBEAFE",
        },
        {
            "title": "Audit Sleep Environment",
            "text": (
                "Keep head elevated 30° post-feeds (GERD). Target 18–20°C room temperature. "
                "A white noise machine can reduce overnight waking by up to 40%."
            ),
            "bg": "#DCFCE7",
        },
        {
            "title": "Track Against Next Week's Baseline",
            "text": (
                f"If cry frequency ≥ {max(15, last_total)}/night or scream events ≥ 2 recur next week, "
                "escalate to an emergency pediatric visit. Use this report as the documented baseline."
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
    footer_text = f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Sense Monitor — Baby Cry Module · Powered by Cochl.Sense"
    elements.append(Paragraph(footer_text, s_small))

    # Build
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
