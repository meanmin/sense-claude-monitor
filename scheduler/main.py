"""
Scheduler Entry Point — runs weekly report generation + Slack/Email delivery.

Usage:
    # Immediate test run (no schedule wait)
    python scheduler/main.py --run-now

    # Start as scheduled daemon
    python -m scheduler.main
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scheduler.config import load_config
from scheduler.report_runner import run_all_reports
from scheduler.summary_extractor import extract_all_summaries
from scheduler.notifier_slack import send_slack_notification
from scheduler.notifier_email import send_email_notification, preview_email_html

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)

# Rotating file handler: 5 MB per file, keep 3 backups
fh = RotatingFileHandler(
    os.path.join(LOG_DIR, "scheduler.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
fh.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(ch)

# Propagate to child loggers
logging.getLogger("scheduler.report_runner").setLevel(logging.INFO)
logging.getLogger("scheduler.notifier_slack").setLevel(logging.INFO)
logging.getLogger("scheduler.notifier_email").setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------
def weekly_report_job(dry_run: bool = False) -> None:
    """Generate all reports, extract summaries, and send notifications."""
    logger.info("=" * 60)
    logger.info("Weekly report job started at %s", datetime.now().isoformat())

    cfg = load_config()

    # 1. Determine enabled monitors
    enabled = [m.name for m in cfg.monitors if m.enabled]
    if not enabled:
        logger.warning("No monitors enabled — nothing to do.")
        return
    logger.info("Enabled monitors: %s", enabled)

    # 2. Generate reports
    results = run_all_reports(enabled)
    if not results:
        logger.error("All report generations failed — aborting notifications.")
        return
    logger.info("Reports generated for: %s", list(results.keys()))

    # 3. Extract summaries
    summaries = extract_all_summaries(results)
    for s in summaries:
        logger.info("[%s] %s — %s", s.monitor, s.status, s.headline)

    # 4. Send notifications (or preview in dry-run mode)
    if dry_run:
        preview_path = os.path.join(
            os.path.dirname(__file__), "logs", "email_preview.html"
        )
        saved = preview_email_html(summaries, preview_path)
        logger.info("Dry-run mode — email preview: %s", saved)
        logger.info("Slack/Email sending skipped (dry-run).")
    else:
        send_slack_notification(cfg.slack, cfg.retry, summaries)
        send_email_notification(cfg.email, cfg.retry, summaries)

    logger.info("Weekly report job completed.")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Sense Monitor Weekly Report Scheduler")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the report job immediately (skip schedule wait)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate reports and save email HTML preview locally (no actual sending)",
    )
    args = parser.parse_args()

    if args.run_now or args.dry_run:
        mode = "dry-run" if args.dry_run else "run-now"
        logger.info("--%s flag detected. Running report job immediately.", mode)
        weekly_report_job(dry_run=args.dry_run)
        return

    cfg = load_config()
    sched = cfg.schedule

    scheduler = BlockingScheduler()
    trigger = CronTrigger(
        day_of_week=sched.day_of_week,
        hour=sched.hour,
        minute=sched.minute,
        timezone=sched.timezone,
    )
    scheduler.add_job(weekly_report_job, trigger, id="weekly_report")

    logger.info(
        "Scheduler started. Next run: every %s at %02d:%02d (%s)",
        sched.day_of_week, sched.hour, sched.minute, sched.timezone,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
