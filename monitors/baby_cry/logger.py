"""
Baby Cry Monitor Logger
Analyzes audio files for baby crying sounds using the cochl.sense SDK
and saves results to daily JSON log files.

Reference: https://github.com/meanmin/sense-claude
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Optional

import cochl.sense as sense
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MONITOR_NAME = "baby_cry"
BASE_DIR = os.path.dirname(__file__)
LOG_DIR = os.path.join(BASE_DIR, "logs")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

SOUND_TAGS = {
    "Baby_cry": {
        "description": "Sound of a baby crying, often high-pitched and repetitive.",
        "severity": "critical",
    },
    "Scream": {
        "description": "The sound of a scream in response to fear or surprise.",
        "severity": "high",
    },
    "Moan": {
        "description": "A vocal sound expressing pain or pleasure.",
        "severity": "medium",
    },
    "Baby_laughter": {
        "description": "A baby's laughing sound, typically high-pitched and joyful.",
        "severity": "info",
    },
}

SEVERITY_LEVELS = {
    "critical": logging.CRITICAL,
    "high": logging.ERROR,
    "medium": logging.WARNING,
    "info": logging.INFO,
}

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(MONITOR_NAME)
logger.setLevel(logging.DEBUG)

_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(name)s | %(levelname)s | %(message)s")
)
logger.addHandler(_handler)


# ---------------------------------------------------------------------------
# Cochl.Sense SDK Analysis
# ---------------------------------------------------------------------------
def analyze_audio(file_path: str, api_key: str) -> List[dict]:
    """Analyze an audio file via cochl.sense SDK and return window_results."""
    logger.info(f"Starting Cochl.Sense analysis: {os.path.basename(file_path)}")

    api_config = sense.APIConfigFromJson(CONFIG_PATH)
    client = sense.Client(api_key, api_config=api_config)
    result = client.predict(file_path)

    events_data = result.events.to_dict(api_config)
    window_results = events_data.get("window_results", [])

    logger.info(f"Analysis complete: {len(window_results)} windows received")
    return window_results


# ---------------------------------------------------------------------------
# Event Filtering & Logging
# ---------------------------------------------------------------------------
def filter_events(window_results: List[dict]) -> List[dict]:
    """Filter window_results to keep only tags registered in SOUND_TAGS."""
    matched = []

    for window in window_results:
        start_time = window.get("start_time", 0)
        end_time = window.get("end_time", 0)

        for tag in window.get("sound_tags", []):
            name = tag.get("name", "")
            probability = tag.get("probability", 0)

            if name not in SOUND_TAGS:
                logger.debug(f"Ignored untracked tag: {name}")
                continue

            meta = SOUND_TAGS[name]
            level = SEVERITY_LEVELS[meta["severity"]]

            event = {
                "tag": name,
                "confidence": round(probability, 4),
                "severity": meta["severity"],
                "description": meta["description"],
                "start_time": start_time,
                "end_time": end_time,
            }
            matched.append(event)
            logger.log(level, json.dumps(event, ensure_ascii=False))

    return matched


# ---------------------------------------------------------------------------
# Log Persistence
# ---------------------------------------------------------------------------
def save_log(file_path: str, events: List[dict]) -> str:
    """Save analysis results to cry_log_YYYYMMDD.json."""
    os.makedirs(LOG_DIR, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(LOG_DIR, f"cry_log_{today}.json")

    entry = {
        "monitor": MONITOR_NAME,
        "source_file": os.path.basename(file_path),
        "analyzed_at": datetime.now().isoformat(),
        "events": events,
    }

    existing = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing.append(entry)

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    logger.info(f"Log saved: {log_path}")
    return log_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    load_dotenv()

    api_key = os.getenv("COCHL_API_KEY")
    if not api_key or api_key == "your_project_key_here":
        logger.error("COCHL_API_KEY is not configured.")
        logger.error("Get your key at https://dashboard.cochl.ai")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <audio_file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    window_results = analyze_audio(file_path, api_key)
    events = filter_events(window_results)
    log_path = save_log(file_path, events)

    print(f"Results saved: {log_path}")


if __name__ == "__main__":
    main()
