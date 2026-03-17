"""
Email Notifier — sends HTML summary emails with PDF attachments via SMTP.
Compatible with Gmail App Passwords.
"""

import logging
import os
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from scheduler.config import EmailConfig, RetryConfig
from scheduler.summary_extractor import MonitorSummary

logger = logging.getLogger(__name__)

_MONITOR_LABELS = {
    "baby_cry": "Baby Cry Monitor",
    "elder_care": "Elder Care Monitor",
    "sleep": "Sleep Disorder Monitor",
}

_STATUS_COLORS = {
    "CRITICAL": "#EF4444",
    "WARNING": "#F97316",
    "NORMAL": "#22C55E",
}


def _get_report_date_range() -> str:
    """Return the report week range string, e.g. 'Mar 10 – 16, 2026'."""
    today = datetime.now()
    week_end = today - timedelta(days=1)
    week_start = week_end - timedelta(days=6)
    if week_start.month == week_end.month:
        return f"{week_start.strftime('%b %-d')} – {week_end.strftime('%-d')}, {week_end.year}"
    return f"{week_start.strftime('%b %-d')} – {week_end.strftime('%b %-d')}, {week_end.year}"


def _build_html(summaries: List[MonitorSummary]) -> str:
    """Build an HTML email body from summaries."""
    date_range = _get_report_date_range()
    monitor_sections = ""

    # Check if any monitor has a critical-level status
    _CRITICAL_STATUSES = {"CRITICAL", "ALERT", "SEVERE"}
    has_critical = any(s.status in _CRITICAL_STATUSES for s in summaries)

    for s in summaries:
        label = _MONITOR_LABELS.get(s.monitor, s.monitor)
        color = _STATUS_COLORS.get(s.status, "#6B7280")
        is_critical = s.status in _CRITICAL_STATUSES

        # Urgent banner for critical-level statuses
        urgent_banner = ""
        if is_critical:
            urgent_banner = f"""
                    <tr>
                        <td style="background:#FEF2F2;padding:8px 16px;font-size:12px;color:#991B1B;border-bottom:1px solid #FECACA;">
                            &#9888; <b>Immediate attention required</b> &mdash; This monitor is at the highest severity level.
                        </td>
                    </tr>"""

        kpi_cells = ""
        for k in s.kpis:
            kpi_cells += f"""
            <td style="text-align:center;padding:8px 12px;">
                <div style="font-size:11px;color:#6B7280;">{k.label}</div>
                <div style="font-size:20px;font-weight:bold;color:#1E293B;">{k.value}</div>
                <div style="font-size:10px;color:#9CA3AF;">{k.detail}</div>
            </td>"""

        monitor_sections += f"""
        <tr>
            <td style="padding:16px 0;">
                <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {'#FCA5A5' if is_critical else '#E2E8F0'};border-radius:8px;overflow:hidden;{'box-shadow:0 0 0 2px #FCA5A5;' if is_critical else ''}">
                    <tr>
                        <td style="background:{color};color:white;padding:10px 16px;font-weight:bold;font-size:14px;">
                            {'&#9888; ' if is_critical else ''}{label} &mdash; {s.status}
                        </td>
                    </tr>{urgent_banner}
                    <tr>
                        <td style="padding:12px 16px;font-size:13px;color:#374151;">
                            {s.headline}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:0 16px 12px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>{kpi_cells}</tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>"""

    # Severity legend
    severity_legend = """
        <tr>
            <td style="padding:20px 24px 8px;border-top:1px solid #E2E8F0;">
                <div style="font-size:12px;font-weight:bold;color:#374151;margin-bottom:10px;">Severity Level Reference</div>
                <table width="100%" cellpadding="0" cellspacing="0" style="font-size:11px;color:#6B7280;">
                    <tr>
                        <td style="padding:4px 8px 4px 0;">
                            <span style="color:#EF4444;">&#9679;</span> <b>CRITICAL</b> &ndash; Immediate action required. Medical consultation recommended within 48 hours.
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:4px 8px 4px 0;">
                            <span style="color:#F97316;">&#9679;</span> <b>WARNING</b> &ndash; Close monitoring needed. Schedule a check-up if the condition persists.
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:4px 8px 4px 0;">
                            <span style="color:#22C55E;">&#9679;</span> <b>NORMAL</b> &ndash; Within safe range. Continue routine monitoring.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>"""

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Helvetica,Arial,sans-serif;background:#F1F5F9;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:24px 16px;">
    <table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <!-- Header -->
        <tr>
            <td style="background:#1E293B;color:white;padding:20px 24px;border-radius:12px 12px 0 0;">
                <div style="font-size:20px;font-weight:bold;">Sense Monitor &mdash; Weekly Report</div>
                <div style="font-size:14px;color:#CBD5E1;margin-top:4px;">{date_range}</div>
                <div style="font-size:12px;color:#94A3B8;margin-top:2px;">
                    {len(summaries)} monitor(s) reported &middot; PDF reports attached
                </div>
            </td>
        </tr>
        <!-- Body -->
        <tr>
            <td style="padding:8px 24px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    {monitor_sections}
                </table>
            </td>
        </tr>
        <!-- Severity Legend -->
        {severity_legend}
        <!-- Footer -->
        <tr>
            <td style="padding:16px 24px;font-size:11px;color:#9CA3AF;text-align:center;border-top:1px solid #E2E8F0;">
                Generated by Sense Monitor Scheduler &middot; Powered by Cochl.Sense
            </td>
        </tr>
    </table>
</td></tr>
</table>
</body>
</html>"""
    return html


def _send_with_retry(
    email_cfg: EmailConfig,
    retry_cfg: RetryConfig,
    msg: MIMEMultipart,
) -> None:
    """Send an email with exponential backoff retry."""
    for attempt in range(1, retry_cfg.max_attempts + 1):
        try:
            with smtplib.SMTP(email_cfg.smtp_host, email_cfg.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(email_cfg.sender, email_cfg.password)
                server.send_message(msg)
            return
        except Exception as e:
            if attempt == retry_cfg.max_attempts:
                raise
            wait = retry_cfg.backoff_base ** attempt
            logger.warning(
                "SMTP error (attempt %d/%d): %s — retrying in %ds",
                attempt, retry_cfg.max_attempts, e, wait,
            )
            time.sleep(wait)


def preview_email_html(summaries: List[MonitorSummary], output_path: str) -> str:
    """Save email HTML to a file for local preview (dry-run mode).

    Returns the absolute path to the saved HTML file.
    """
    html_body = _build_html(summaries)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_body)
    logger.info("Email preview saved to %s", output_path)
    return os.path.abspath(output_path)


def send_email_notification(
    email_cfg: EmailConfig,
    retry_cfg: RetryConfig,
    summaries: List[MonitorSummary],
) -> None:
    """Send an HTML email with PDF attachments to all recipients."""
    if not email_cfg.enabled:
        logger.info("Email notifications disabled — skipping.")
        return

    if not email_cfg.sender or not email_cfg.password:
        logger.error("SMTP_SENDER or SMTP_PASSWORD not set — skipping email notification.")
        return

    if not email_cfg.recipients:
        logger.warning("No email recipients configured — skipping.")
        return

    msg = MIMEMultipart("mixed")
    msg["From"] = email_cfg.sender
    msg["To"] = ", ".join(email_cfg.recipients)
    msg["Subject"] = f"Sense Monitor — Weekly Report ({_get_report_date_range()})"

    # HTML body
    html_body = _build_html(summaries)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # PDF attachments
    for s in summaries:
        if not s.pdf_path or not os.path.isfile(s.pdf_path):
            continue
        with open(s.pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
        filename = os.path.basename(s.pdf_path)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    try:
        _send_with_retry(email_cfg, retry_cfg, msg)
        logger.info("Email sent to %s", email_cfg.recipients)
    except Exception:
        logger.exception("Failed to send email notification.")
