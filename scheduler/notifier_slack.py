"""
Slack Notifier — sends Block Kit summary messages and uploads PDF attachments.
"""

import logging
import time
from typing import List

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from scheduler.config import SlackConfig, RetryConfig
from scheduler.summary_extractor import MonitorSummary

logger = logging.getLogger(__name__)

# Status emoji mapping
_STATUS_EMOJI = {
    "CRITICAL": ":rotating_light:",
    "WARNING": ":warning:",
    "NORMAL": ":white_check_mark:",
}

# Display names
_MONITOR_LABELS = {
    "baby_cry": "Baby Cry Monitor",
    "elder_care": "Elder Care Monitor",
    "sleep": "Sleep Disorder Monitor",
}


def _build_blocks(summaries: List[MonitorSummary]) -> list:
    """Build Slack Block Kit blocks from a list of MonitorSummary objects."""
    blocks: list = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Sense Monitor — Weekly Report",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":bar_chart: *{len(summaries)} monitor(s)* reported",
                }
            ],
        },
        {"type": "divider"},
    ]

    for s in summaries:
        emoji = _STATUS_EMOJI.get(s.status, ":question:")
        label = _MONITOR_LABELS.get(s.monitor, s.monitor)

        kpi_lines = "  |  ".join(f"*{k.label}:* {k.value}" for k in s.kpis)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{emoji} *{label}*  —  `{s.status}`\n"
                    f"{s.headline}\n"
                    f"{kpi_lines}"
                ),
            },
        })
        blocks.append({"type": "divider"})

    return blocks


def _retry(fn, retry_cfg: RetryConfig):
    """Execute fn with exponential backoff retries."""
    for attempt in range(1, retry_cfg.max_attempts + 1):
        try:
            return fn()
        except SlackApiError as e:
            if attempt == retry_cfg.max_attempts:
                raise
            wait = retry_cfg.backoff_base ** attempt
            logger.warning(
                "Slack API error (attempt %d/%d): %s — retrying in %ds",
                attempt, retry_cfg.max_attempts, e.response["error"], wait,
            )
            time.sleep(wait)


def send_slack_notification(
    slack_cfg: SlackConfig,
    retry_cfg: RetryConfig,
    summaries: List[MonitorSummary],
) -> None:
    """Post a Block Kit summary message and upload PDF files to Slack."""
    if not slack_cfg.enabled:
        logger.info("Slack notifications disabled — skipping.")
        return

    if not slack_cfg.bot_token:
        logger.error("SLACK_BOT_TOKEN is not set — skipping Slack notification.")
        return

    client = WebClient(token=slack_cfg.bot_token)
    channel = slack_cfg.channel

    # 1. Post summary message
    blocks = _build_blocks(summaries)

    def _post_message():
        return client.chat_postMessage(
            channel=channel,
            text="Sense Monitor — Weekly Report",
            blocks=blocks,
        )

    try:
        _retry(_post_message, retry_cfg)
        logger.info("Slack summary message sent to %s", channel)
    except SlackApiError:
        logger.exception("Failed to send Slack summary message.")
        return

    # 2. Upload PDF files
    for s in summaries:
        if not s.pdf_path:
            continue

        def _upload(path=s.pdf_path, monitor=s.monitor):
            return client.files_upload_v2(
                channel=channel,
                file=path,
                title=f"{_MONITOR_LABELS.get(monitor, monitor)} Weekly Report",
                initial_comment=f":page_facing_up: {_MONITOR_LABELS.get(monitor, monitor)} PDF report attached.",
            )

        try:
            _retry(_upload, retry_cfg)
            logger.info("Uploaded PDF for %s to %s", s.monitor, channel)
        except SlackApiError:
            logger.exception("Failed to upload PDF for %s.", s.monitor)
