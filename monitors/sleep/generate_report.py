"""
Sleep Disorder Weekly Report PDF Generator
Reads all sleep_log_*.json files and produces a 4-page PDF report.
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
C_INDIGO    = "#6366F1"
C_GRAY      = "#6B7280"
C_LIGHT_BG  = "#F8FAFC"
C_HEADER_BG = "#1E293B"

TAG_COLORS = {
    "Snore":         "#6366F1",
    "Cough":         "#F97316",
    "Throat_clear":  "#F59E0B",
    "Yawn":          "#6B7280",
}

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
def load_all_logs():
    """Load all sleep_log_*.json files, return sorted list of (date_str, entries)."""
    files = sorted(glob.glob(os.path.join(LOG_DIR, "sleep_log_*.json")))
    all_data = []
    for fp in files:
        basename = os.path.basename(fp)
        date_str = basename.replace("sleep_log_", "").replace(".json", "")
        with open(fp, "r", encoding="utf-8") as f:
            entries = json.load(f)
        all_data.append((date_str, entries))
    return all_data


def compute_daily_stats(all_data):
    """Compute per-night tag counts, avg snore confidence, and hours."""
    stats = []
    for date_str, entries in all_data:
        counts = defaultdict(int)
        snore_confidences = []
        all_confidences = []
        hours = []
        snore_hours = []

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

                if tag == "Snore":
                    snore_confidences.append(ev["confidence"])
                    snore_hours.append(hour)

        avg_snore_conf = round(sum(snore_confidences) / len(snore_confidences), 2) if snore_confidences else 0
        peak_snore_conf = round(max(snore_confidences), 4) if snore_confidences else 0
        total = sum(counts.values())
        total_snore = counts.get("Snore", 0)
        disruption_count = counts.get("Cough", 0) + counts.get("Throat_clear", 0)

        # REM-band ratio (2-4 AM snoring)
        rem_snore = sum(1 for h in snore_hours if 2 <= h <= 4)
        rem_ratio = round(rem_snore / total_snore * 100) if total_snore > 0 else 0

        stats.append({
            "date": date_str,
            "label": f"Mar {int(date_str[6:])}",
            "counts": dict(counts),
            "total": total,
            "total_snore": total_snore,
            "avg_snore_conf": avg_snore_conf,
            "peak_snore_conf": peak_snore_conf,
            "disruption_count": disruption_count,
            "rem_ratio": rem_ratio,
            "hours": hours,
            "snore_hours": snore_hours,
        })
    return stats


def compute_hourly_distribution(all_data):
    """Compute cumulative hourly distribution of snore events across all nights."""
    hourly = defaultdict(int)
    for date_str, entries in all_data:
        for entry in entries:
            analyzed_at = entry.get("analyzed_at", "")
            try:
                hour = datetime.fromisoformat(analyzed_at).hour
            except Exception:
                continue
            snore_count = sum(1 for ev in entry.get("events", []) if ev["tag"] == "Snore")
            hourly[hour] += snore_count
    return hourly


# ---------------------------------------------------------------------------
# Chart Generation
# ---------------------------------------------------------------------------
def generate_daily_chart(stats, path):
    """Stacked bar chart of nightly events by type."""
    fig, ax = plt.subplots(figsize=(8, 4.5))

    tags = ["Snore", "Cough", "Throat_clear", "Yawn"]
    labels = ["Snore", "Cough", "Throat Clear", "Yawn"]
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
    ax.set_title("Nightly Detected Events by Type", fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="upper left", fontsize=9)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_dual_chart(stats, path):
    """Dual chart: Snoring Intensity (line) + Sleep Disruption Index (bar)."""
    fig, ax1 = plt.subplots(figsize=(8, 4.5))

    dates = [s["label"] for s in stats]
    x = np.arange(len(stats))

    # Left axis: Snoring Intensity (peak confidence)
    snore_confs = [s["peak_snore_conf"] for s in stats]
    ax1.set_ylabel("Peak Snore Confidence", fontsize=11, color=C_INDIGO)

    # Zone bands
    ax1.axhspan(0.95, 1.05, color="#EDE9FE", alpha=0.5)
    ax1.axhspan(0.85, 0.95, color="#FEF3C7", alpha=0.4)
    ax1.axhspan(0.0, 0.85, color="#DCFCE7", alpha=0.4)

    ax1.axhline(y=0.95, color="#7C3AED", linestyle=":", linewidth=1, alpha=0.6)
    ax1.axhline(y=0.85, color="#F59E0B", linestyle=":", linewidth=1, alpha=0.6)

    line = ax1.plot(x, snore_confs, "o-", color=C_INDIGO, linewidth=2.5, markersize=8,
                    zorder=5, label="Peak Snore Intensity")

    for i, c in enumerate(snore_confs):
        color = C_RED if c >= 0.95 else (C_ORANGE if c >= 0.85 else C_GREEN)
        ax1.annotate(f"{c:.2f}", (i, c), textcoords="offset points",
                    xytext=(0, 14), ha="center", fontsize=10, fontweight="bold", color=color)

    ax1.set_ylim(0.5, 1.05)
    ax1.tick_params(axis='y', labelcolor=C_INDIGO)

    # Right axis: Sleep Disruption count
    ax2 = ax1.twinx()
    disruptions = [s["disruption_count"] for s in stats]
    bars = ax2.bar(x + 0.2, disruptions, 0.25, color=C_ORANGE, alpha=0.7,
                   label="Sleep Disruptions", zorder=3)
    for i, v in enumerate(disruptions):
        if v > 0:
            ax2.text(i + 0.2, v + 0.1, str(v), ha="center", va="bottom",
                    fontsize=10, fontweight="bold", color=C_ORANGE)

    ax2.set_ylabel("Disruption Events", fontsize=11, color=C_ORANGE)
    ax2.tick_params(axis='y', labelcolor=C_ORANGE)
    ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax2.set_ylim(0, max(disruptions) + 3 if disruptions else 5)

    # Legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=C_INDIGO, marker="o", label="Peak Snore Intensity"),
        Patch(facecolor=C_ORANGE, alpha=0.7, label="Sleep Disruptions"),
        Patch(facecolor="#EDE9FE", label=u"Severe Zone (\u2265 0.95)"),
        Patch(facecolor="#FEF3C7", label="Moderate (0.85\u20130.95)"),
        Patch(facecolor="#DCFCE7", label="Mild (< 0.85)"),
    ]
    ax1.legend(handles=legend_elements, loc="upper left", fontsize=7.5)

    ax1.set_xticks(x)
    ax1.set_xticklabels(dates, fontsize=11)
    ax1.set_title(f"Snoring Intensity + Sleep Disruption Index \u2014 {len(stats)}-Night Trend",
                  fontsize=13, fontweight="bold", pad=12)
    ax1.spines["top"].set_visible(False)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_hourly_chart(hourly, path):
    """Bar chart of hourly snore distribution with REM sleep band highlight."""
    fig, ax = plt.subplots(figsize=(8, 4))

    # Focus on sleep hours: 22:00 to 08:00
    hour_order = list(range(22, 24)) + list(range(0, 9))
    hour_labels = [f"{h:02d}:00" for h in hour_order]
    values = [hourly.get(h, 0) for h in hour_order]

    x = np.arange(len(hour_order))
    colors_bar = []
    for h in hour_order:
        if 2 <= h <= 4:
            colors_bar.append(C_INDIGO)  # REM band
        elif 1 <= h <= 5:
            colors_bar.append("#818CF8")  # near-REM
        else:
            colors_bar.append("#C7D2FE")  # other sleep

    bars = ax.bar(x, values, color=colors_bar, width=0.7)
    for i, v in enumerate(values):
        if v > 0:
            ax.text(i, v + 0.15, str(v), ha="center", va="bottom", fontsize=9, fontweight="bold")

    # REM band annotation
    ax.annotate("REM Sleep Band\n(2:00\u20134:00 AM)", xy=(5, max(values) * 0.88),
                fontsize=9, color=C_GRAY, ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#EDE9FE", edgecolor="#A5B4FC"))

    ax.set_xticks(x)
    ax.set_xticklabels(hour_labels, fontsize=8, rotation=45, ha="right")
    ax.set_ylabel("Total Snore Events", fontsize=11)
    ax.set_title("When Does Snoring Occur?  (Cumulative Events by Hour)", fontsize=13, fontweight="bold", pad=12)
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
    pdf_path = os.path.join(REPORT_DIR, f"sleep_weekly_report_{today}.pdf")

    # Generate chart images
    daily_chart_path = os.path.join(CHART_DIR, "nightly_events.png")
    dual_chart_path = os.path.join(CHART_DIR, "snore_intensity.png")
    hourly_chart_path = os.path.join(CHART_DIR, "hourly_dist.png")

    generate_daily_chart(stats, daily_chart_path)
    generate_dual_chart(stats, dual_chart_path)
    generate_hourly_chart(hourly, hourly_chart_path)

    # Compute KPI values
    total_snore = sum(s["total_snore"] for s in stats)
    peak_conf = max(s["peak_snore_conf"] for s in stats)
    peak_conf_date = [s for s in stats if s["peak_snore_conf"] == peak_conf][0]["label"]
    total_disruptions = sum(s["disruption_count"] for s in stats)
    avg_rem_ratio = round(sum(s["rem_ratio"] for s in stats) / len(stats)) if stats else 0

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
    latest = stats[-1]
    if latest["peak_snore_conf"] >= 0.95:
        status = "SEVERE"
        status_color = C_RED
    elif latest["peak_snore_conf"] >= 0.85:
        status = "MODERATE"
        status_color = C_ORANGE
    else:
        status = "MILD"
        status_color = C_GREEN

    # ---- Build PDF ----
    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        topMargin=15*mm, bottomMargin=15*mm,
        leftMargin=18*mm, rightMargin=18*mm,
    )

    styles = getSampleStyleSheet()
    W = A4[0] - 36*mm

    s_title = ParagraphStyle("Title2", parent=styles["Title"],
                             fontSize=18, leading=24, textColor=white,
                             fontName="Helvetica-Bold")
    s_subtitle = ParagraphStyle("Sub", parent=styles["Normal"],
                                fontSize=10, textColor=HexColor("#94A3B8"),
                                fontName="Helvetica")
    s_heading = ParagraphStyle("H2", parent=styles["Heading2"],
                               fontSize=16, textColor=HexColor(C_INDIGO),
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

    # ===== PAGE 1: Header + KPI + Nightly Breakdown =====
    header_data = [[
        Paragraph("<b>Sleep Disorder \u00b7 Weekly Report</b>", s_title),
        Paragraph(f"Analysis Period: {date_range}<br/>Monitor: sleep", s_subtitle),
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
        kpi_cell("TOTAL SNORE", str(total_snore), f"{total_snore} events over {num_days} nights", C_INDIGO),
        kpi_cell("PEAK INTENSITY", f"{peak_conf:.2f}", f"Confidence on {peak_conf_date}", C_RED),
        kpi_cell("DISRUPTIONS", str(total_disruptions), f"Cough + Throat clear", C_ORANGE),
        kpi_cell("REM-BAND RATIO", f"{avg_rem_ratio}%", "2\u20134 AM snoring avg", C_PURPLE),
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
        f"Snoring intensity peaked at {peak_conf:.2f} on {peak_conf_date}. "
        f"REM-band (2\u20134 AM) concentration averages {avg_rem_ratio}%. "
    )
    if status == "SEVERE":
        alert_text += (
            "Peak confidence \u2265 0.95 with high REM-band concentration is a strong indicator "
            "of Obstructive Sleep Apnea (OSA). Polysomnography evaluation recommended."
        )
        alert_bg = "#EDE9FE"
        alert_border = "#7C3AED"
    elif status == "MODERATE":
        alert_text += "Moderate snoring detected. Consider a sleep study if symptoms persist."
        alert_bg = "#FEF3C7"
        alert_border = C_ORANGE
    else:
        alert_text += "Mild snoring within normal range."
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

    # Section: Nightly Event Breakdown
    elements.append(Paragraph("<b>1. Nightly Event Breakdown</b>", s_heading))
    elements.append(Spacer(1, 2*mm))
    elements.append(Image(daily_chart_path, width=W, height=W*0.48))
    elements.append(Spacer(1, 4*mm))

    # Data table
    tag_order = ["Snore", "Cough", "Throat_clear", "Yawn"]
    tag_labels_table = ["Snore", "Cough", "Throat Clr", "Yawn"]
    header_row = ["Night"] + tag_labels_table + ["REM %", "Status"]
    table_data = [header_row]
    for s in stats:
        pc = s["peak_snore_conf"]
        if pc >= 0.95:
            st = "SEVERE"
        elif pc >= 0.85:
            st = "MODERATE"
        else:
            st = "MILD"
        row = [s["label"]]
        for tag in tag_order:
            row.append(str(s["counts"].get(tag, 0)))
        row.append(f"{s['rem_ratio']}%")
        row.append(st)
        table_data.append(row)

    col_widths = [W*0.11] + [W*0.11]*4 + [W*0.11, W*0.13]
    data_table = Table(table_data, colWidths=col_widths)

    table_style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(C_INDIGO)),
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
        pc = s["peak_snore_conf"]
        if pc >= 0.95:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor("#7C3AED")))
        elif pc >= 0.85:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor(C_ORANGE)))
        else:
            table_style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), HexColor(C_GREEN)))
        table_style_cmds.append(("FONTNAME", (-1, i), (-1, i), "Helvetica-Bold"))

    data_table.setStyle(TableStyle(table_style_cmds))
    elements.append(data_table)
    elements.append(Spacer(1, 4*mm))

    p1_text = (
        f"Snore events increased from {stats[0]['total_snore']} on {stats[0]['label']} to "
        f"{stats[-1]['total_snore']} on {stats[-1]['label']}. "
        f"REM-band concentration (\u2265 {avg_rem_ratio}%) and sleep disruptions ({total_disruptions} total) "
        f"suggest progressive airway obstruction during deep sleep cycles."
    )
    elements.append(Paragraph(p1_text, s_body))

    # ===== PAGE 2: Snoring Intensity + Sleep Disruption Index =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>2. Snoring Intensity + Sleep Disruption Index</b>", s_heading))
    elements.append(Spacer(1, 4*mm))
    elements.append(Image(dual_chart_path, width=W, height=W*0.5))
    elements.append(Spacer(1, 6*mm))

    p2_text = (
        "Peak snore confidence measures the maximum intensity detected per night. "
        "A peak \u2265 0.95 indicates loud, sustained snoring characteristic of upper airway "
        "obstruction. Sleep disruptions (cough, throat clearing) occurring alongside "
        "high-intensity snoring suggest respiratory effort against a partially collapsed airway. "
    )
    if latest["peak_snore_conf"] >= 0.95:
        p2_text += (
            f"On {latest['label']}, peak intensity reached {latest['peak_snore_conf']:.2f} "
            f"with {latest['disruption_count']} disruption event(s) \u2014 "
            "strongly consistent with OSA. A polysomnography study is recommended to confirm diagnosis."
        )
    else:
        p2_text += "Continued monitoring will help establish whether this pattern escalates."
    elements.append(Paragraph(p2_text, s_body))

    # ===== PAGE 3: Hourly Distribution =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>3. Snoring Distribution by Hour of Night</b>", s_heading))
    elements.append(Spacer(1, 4*mm))
    elements.append(Image(hourly_chart_path, width=W, height=W*0.5))
    elements.append(Spacer(1, 6*mm))

    p3_text = (
        f"Snoring concentrates heavily in the 02:00\u201304:00 AM REM sleep band "
        f"(avg {avg_rem_ratio}% of nightly events). During REM sleep, muscle tone decreases "
        "significantly, causing the upper airway to narrow. In OSA patients, this leads to "
        "complete or partial airway collapse. The sharp intensity increase at 02:00\u201303:00 AM "
        "followed by disruption events (cough, throat clearing) at 03:00\u201304:00 AM "
        "suggests a cycle of obstruction \u2192 arousal \u2192 resumption."
    )
    elements.append(Paragraph(p3_text, s_body))

    # ===== PAGE 4: Recommendations =====
    elements.append(PageBreak())
    elements.append(Paragraph("<b>4. Recommendations</b>", s_heading))
    elements.append(Spacer(1, 4*mm))

    recommendations = []

    if latest["peak_snore_conf"] >= 0.95:
        recommendations.append({
            "title": "Polysomnography (Sleep Study) \u2014 Within 2 Weeks [URGENT]",
            "text": (
                f"Peak snore intensity {peak_conf:.2f}, REM-band concentration {avg_rem_ratio}%, "
                f"and {total_disruptions} disruption events over {num_days} nights meet the screening "
                "threshold for Obstructive Sleep Apnea. A formal polysomnography (PSG) study "
                "will measure AHI (Apnea-Hypopnea Index) and oxygen desaturation. "
                "Share this report with your sleep medicine specialist."
            ),
            "bg": "#EDE9FE",
        })

    recommendations.extend([
        {
            "title": "Positional Therapy \u2014 Side Sleeping",
            "text": (
                "Supine sleeping worsens snoring by allowing gravity to pull the tongue and "
                "soft palate backward. Use a positional therapy device or place a tennis ball "
                "in a sock sewn to the back of your sleep shirt. Monitor for improvement over "
                "the next 7 nights."
            ),
            "bg": "#DBEAFE",
        },
        {
            "title": "CPAP Evaluation",
            "text": (
                "If polysomnography confirms moderate-to-severe OSA (AHI \u2265 15), "
                "Continuous Positive Airway Pressure (CPAP) therapy is the gold standard treatment. "
                "An auto-titrating CPAP device can adjust pressure dynamically during REM cycles."
            ),
            "bg": "#DBEAFE",
        },
        {
            "title": "Weight Management",
            "text": (
                "A 10% reduction in body weight can reduce AHI by 26\u201332% in overweight patients. "
                "Combine with dietary adjustments and avoid alcohol within 4 hours of bedtime, "
                "as alcohol further relaxes upper airway muscles."
            ),
            "bg": "#DCFCE7",
        },
        {
            "title": "Sleep Hygiene Optimization",
            "text": (
                "Maintain a consistent sleep schedule (same bedtime \u00b130 min). "
                "Avoid caffeine after 14:00 and heavy meals within 3 hours of bedtime. "
                "Keep the bedroom cool (18\u201320\u00b0C) and use humidification if air is dry. "
                "Continue audio monitoring to track response to interventions."
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
    footer_text = f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} \u00b7 Sense Monitor \u2014 Sleep Module \u00b7 Powered by Cochl.Sense"
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
