"""
Baby Cry Monitor Logger
cochl.sense SDK(plugin 방식)를 사용하여 오디오 파일에서
아기 울음 관련 사운드를 분석하고 결과를 JSON 로그로 저장한다.

참고: https://github.com/meanmin/sense-claude
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
# 설정
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
# 로거
# ---------------------------------------------------------------------------
logger = logging.getLogger(MONITOR_NAME)
logger.setLevel(logging.DEBUG)

_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(name)s | %(levelname)s | %(message)s")
)
logger.addHandler(_handler)


# ---------------------------------------------------------------------------
# Cochl.Sense SDK 분석
# ---------------------------------------------------------------------------
def analyze_audio(file_path: str, api_key: str) -> List[dict]:
    """cochl.sense SDK로 오디오 파일을 분석하여 window_results를 반환"""
    logger.info(f"Cochl.Sense 분석 시작: {os.path.basename(file_path)}")

    api_config = sense.APIConfigFromJson(CONFIG_PATH)
    client = sense.Client(api_key, api_config=api_config)
    result = client.predict(file_path)

    events_data = result.events.to_dict(api_config)
    window_results = events_data.get("window_results", [])

    logger.info(f"분석 완료: {len(window_results)}개 윈도우 수신")
    return window_results


# ---------------------------------------------------------------------------
# 이벤트 필터링 및 로깅
# ---------------------------------------------------------------------------
def filter_events(window_results: List[dict]) -> List[dict]:
    """window_results에서 SOUND_TAGS에 등록된 태그만 필터링"""
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
# 로그 저장
# ---------------------------------------------------------------------------
def save_log(file_path: str, events: List[dict]) -> str:
    """분석 결과를 cry_log_YYYYMMDD.json 파일로 저장"""
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

    logger.info(f"로그 저장 완료: {log_path}")
    return log_path


# ---------------------------------------------------------------------------
# 메인 실행
# ---------------------------------------------------------------------------
def main():
    load_dotenv()

    api_key = os.getenv("COCHL_API_KEY")
    if not api_key or api_key == "your_project_key_here":
        logger.error("COCHL_API_KEY가 설정되지 않았습니다.")
        logger.error("https://dashboard.cochl.ai 에서 키를 발급받으세요.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <audio_file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        logger.error(f"파일을 찾을 수 없습니다: {file_path}")
        sys.exit(1)

    window_results = analyze_audio(file_path, api_key)
    events = filter_events(window_results)
    log_path = save_log(file_path, events)

    print(f"결과 저장: {log_path}")


if __name__ == "__main__":
    main()
