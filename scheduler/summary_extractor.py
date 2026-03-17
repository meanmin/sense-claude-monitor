"""
Summary Extractor — converts raw monitor stats into notification-friendly summaries.

Each monitor's stats list is reduced to a MonitorSummary dataclass containing
KPI values, status level, and human-readable text used by both Slack and email notifiers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class KPI:
    label: str
    value: str
    detail: str = ""


@dataclass
class MonitorSummary:
    monitor: str
    status: str            # "CRITICAL", "WARNING", or "NORMAL"
    status_color: str      # hex color for status badge
    headline: str          # one-line summary
    kpis: List[KPI] = field(default_factory=list)
    pdf_path: str = ""


def _extract_baby_cry(stats: list, pdf_path: str) -> MonitorSummary:
    total_cry = sum(s["counts"].get("Baby_cry", 0) for s in stats)
    total_scream = sum(s["counts"].get("Scream", 0) for s in stats)
    peak_conf = max(s["avg_conf"] for s in stats)
    latest_conf = stats[-1]["avg_conf"]
    num_days = len(stats)

    if latest_conf >= 0.90:
        status, color = "CRITICAL", "#EF4444"
    elif latest_conf >= 0.75:
        status, color = "WARNING", "#F97316"
    else:
        status, color = "NORMAL", "#22C55E"

    headline = (
        f"{total_cry} cry events over {num_days} days | "
        f"Latest intensity {latest_conf:.2f} → {status}"
    )

    kpis = [
        KPI("Total Cry Events", str(total_cry), f"{num_days} days"),
        KPI("Scream Events", str(total_scream)),
        KPI("Peak Intensity", f"{peak_conf:.2f}"),
        KPI("Latest Intensity", f"{latest_conf:.2f}"),
    ]

    return MonitorSummary(
        monitor="baby_cry",
        status=status,
        status_color=color,
        headline=headline,
        kpis=kpis,
        pdf_path=pdf_path,
    )


def _extract_elder_care(stats: list, pdf_path: str) -> MonitorSummary:
    total_cough = sum(s["total_cough"] for s in stats)
    total_vomit = sum(s["counts"].get("Vomit", 0) for s in stats)
    total_fall = sum(
        s["counts"].get("Thud", 0) + s["counts"].get("Glass_break", 0)
        for s in stats
    )
    latest_cough = stats[-1]["total_cough"]
    num_days = len(stats)

    if latest_cough >= 12 or total_fall > 0:
        status, color = "CRITICAL", "#EF4444"
    elif latest_cough >= 8:
        status, color = "WARNING", "#F97316"
    else:
        status, color = "NORMAL", "#22C55E"

    headline = (
        f"{total_cough} cough events over {num_days} days | "
        f"Falls: {total_fall} | Vomit: {total_vomit} → {status}"
    )

    kpis = [
        KPI("Total Cough", str(total_cough), f"{num_days} days"),
        KPI("Vomit Events", str(total_vomit)),
        KPI("Fall Incidents", str(total_fall)),
        KPI("Peak Daily Cough", str(max(s["total_cough"] for s in stats))),
    ]

    return MonitorSummary(
        monitor="elder_care",
        status=status,
        status_color=color,
        headline=headline,
        kpis=kpis,
        pdf_path=pdf_path,
    )


def _extract_sleep(stats: list, pdf_path: str) -> MonitorSummary:
    total_snore = sum(s["total_snore"] for s in stats)
    peak_conf = max(s["peak_snore_conf"] for s in stats)
    total_disruptions = sum(s["disruption_count"] for s in stats)
    avg_rem = round(sum(s["rem_ratio"] for s in stats) / len(stats)) if stats else 0
    latest_peak = stats[-1]["peak_snore_conf"]
    num_days = len(stats)

    if latest_peak >= 0.95:
        status, color = "CRITICAL", "#EF4444"
    elif latest_peak >= 0.85:
        status, color = "WARNING", "#F97316"
    else:
        status, color = "NORMAL", "#22C55E"

    headline = (
        f"{total_snore} snore events over {num_days} nights | "
        f"Peak {peak_conf:.2f} | REM-band {avg_rem}% → {status}"
    )

    kpis = [
        KPI("Total Snore", str(total_snore), f"{num_days} nights"),
        KPI("Peak Intensity", f"{peak_conf:.2f}"),
        KPI("Disruptions", str(total_disruptions)),
        KPI("REM-Band Ratio", f"{avg_rem}%"),
    ]

    return MonitorSummary(
        monitor="sleep",
        status=status,
        status_color=color,
        headline=headline,
        kpis=kpis,
        pdf_path=pdf_path,
    )


_EXTRACTORS = {
    "baby_cry": _extract_baby_cry,
    "elder_care": _extract_elder_care,
    "sleep": _extract_sleep,
}


def extract_summary(
    monitor_name: str,
    stats: list,
    pdf_path: str,
) -> MonitorSummary:
    """Extract a MonitorSummary from the given monitor's stats."""
    extractor = _EXTRACTORS.get(monitor_name)
    if extractor is None:
        raise ValueError(f"Unknown monitor: {monitor_name}")
    return extractor(stats, pdf_path)


def extract_all_summaries(
    report_results: Dict[str, Dict[str, Any]],
) -> List[MonitorSummary]:
    """Extract summaries for all monitors in report_results.

    Args:
        report_results: dict from report_runner.run_all_reports()
                        {monitor_name: {"pdf_path": ..., "stats": ..., "hourly": ...}}
    """
    summaries = []
    for name, result in report_results.items():
        summaries.append(extract_summary(name, result["stats"], result["pdf_path"]))
    return summaries
