"""
Report Runner — orchestrates PDF generation for each monitor.

Imports each monitor's generate_report module and runs:
  load_all_logs() → compute_daily_stats() → compute_hourly_distribution() → build_pdf()

Returns a dict mapping monitor name → {"pdf_path": str, "stats": list}.
"""

import logging
import sys
import os
from typing import Dict, Any, Optional

# Ensure project root is on sys.path so monitors can be imported as packages.
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from monitors.baby_cry import generate_report as baby_cry_report
from monitors.elder_care import generate_report as elder_care_report
from monitors.sleep import generate_report as sleep_report

logger = logging.getLogger(__name__)

_MODULES = {
    "baby_cry": baby_cry_report,
    "elder_care": elder_care_report,
    "sleep": sleep_report,
}


def run_single_report(name: str) -> Optional[Dict[str, Any]]:
    """Generate a report for a single monitor.

    Returns {"pdf_path": str, "stats": list, "hourly": dict} or None on failure.
    """
    mod = _MODULES.get(name)
    if mod is None:
        logger.error("Unknown monitor: %s", name)
        return None

    try:
        all_data = mod.load_all_logs()
        if not all_data:
            logger.warning("[%s] No log files found — skipping.", name)
            return None

        stats = mod.compute_daily_stats(all_data)
        hourly = mod.compute_hourly_distribution(all_data)
        pdf_path = mod.build_pdf(stats, hourly, all_data)
        logger.info("[%s] Report generated: %s", name, pdf_path)
        return {"pdf_path": pdf_path, "stats": stats, "hourly": hourly}

    except Exception:
        logger.exception("[%s] Report generation failed.", name)
        return None


def run_all_reports(enabled_monitors: list[str]) -> Dict[str, Dict[str, Any]]:
    """Generate reports for all enabled monitors.

    Args:
        enabled_monitors: list of monitor names, e.g. ["baby_cry", "elder_care", "sleep"]

    Returns:
        dict mapping monitor name → result dict (only successful ones).
    """
    results: Dict[str, Dict[str, Any]] = {}
    for name in enabled_monitors:
        result = run_single_report(name)
        if result is not None:
            results[name] = result
    return results
