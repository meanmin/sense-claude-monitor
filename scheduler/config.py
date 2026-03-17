"""
Configuration loader — merges .env secrets with scheduler_config.yaml settings.
"""

import os
from dataclasses import dataclass, field
from typing import List

import yaml
from dotenv import load_dotenv

CONFIG_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)
YAML_PATH = os.path.join(CONFIG_DIR, "scheduler_config.yaml")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ScheduleConfig:
    day_of_week: str = "mon"
    hour: int = 9
    minute: int = 0
    timezone: str = "Asia/Seoul"


@dataclass
class MonitorConfig:
    name: str = ""
    enabled: bool = True


@dataclass
class SlackConfig:
    enabled: bool = False
    channel: str = "#sense-reports"
    bot_token: str = ""


@dataclass
class EmailConfig:
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender: str = ""
    password: str = ""
    recipients: List[str] = field(default_factory=list)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_base: int = 2


@dataclass
class AppConfig:
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    monitors: List[MonitorConfig] = field(default_factory=list)
    slack: SlackConfig = field(default_factory=SlackConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    project_root: str = PROJECT_ROOT


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
def load_config() -> AppConfig:
    """Load .env secrets and YAML structural settings, return AppConfig."""
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

    with open(YAML_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Schedule
    sched_raw = raw.get("schedule", {})
    schedule = ScheduleConfig(
        day_of_week=sched_raw.get("day_of_week", "mon"),
        hour=sched_raw.get("hour", 9),
        minute=sched_raw.get("minute", 0),
        timezone=sched_raw.get("timezone", "Asia/Seoul"),
    )

    # Monitors
    monitors = []
    for name, opts in raw.get("monitors", {}).items():
        monitors.append(MonitorConfig(name=name, enabled=opts.get("enabled", True)))

    # Slack (secret from env)
    notif = raw.get("notifications", {})
    slack_raw = notif.get("slack", {})
    slack = SlackConfig(
        enabled=slack_raw.get("enabled", False),
        channel=slack_raw.get("channel", "#sense-reports"),
        bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
    )

    # Email (secrets from env)
    email_raw = notif.get("email", {})
    email = EmailConfig(
        enabled=email_raw.get("enabled", False),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        sender=os.getenv("SMTP_SENDER", ""),
        password=os.getenv("SMTP_PASSWORD", ""),
        recipients=email_raw.get("recipients", []),
    )

    # Retry
    retry_raw = raw.get("retry", {})
    retry = RetryConfig(
        max_attempts=retry_raw.get("max_attempts", 3),
        backoff_base=retry_raw.get("backoff_base", 2),
    )

    return AppConfig(
        schedule=schedule,
        monitors=monitors,
        slack=slack,
        email=email,
        retry=retry,
    )
