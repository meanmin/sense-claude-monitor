# Sense Claude Monitor

Cochl.Sense Cloud API + Claude Code로 구동되는 음향 기반 건강 모니터링 시스템.
아기 울음, 노인 케어, 수면 장애를 실시간으로 감지하고 주간 분석 리포트를 자동 생성합니다.

---

## Quick Start (5분 셋업)

### 1. 프로젝트 다운로드

```bash
git clone https://github.com/your-repo/sense-claude-monitor.git
cd sense-claude-monitor
```

또는 ZIP 다운로드 후 압축 해제.

### 2. Python 가상환경 생성 + 의존성 설치

> Python 3.9 이상 필수. Python 3.11+는 가상환경이 반드시 필요합니다.

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install python-dotenv
pip install cochl --no-deps
pip install soundfile requests numpy python-dateutil urllib3 pydantic
```

### 3. API 키 설정

[Cochl Dashboard](https://dashboard.cochl.ai)에서 프로젝트 키를 발급받으세요.

```bash
cp .env.example .env
# .env 파일을 열어 실제 키로 교체
```

```
COCHL_API_KEY=your_actual_api_key_here
```

### 4. 오디오 분석 실행

```bash
# 아기 울음 분석
python monitors/baby_cry/logger.py /path/to/baby_audio.wav

# 노인 케어 분석
python monitors/elder_care/logger.py /path/to/coughing.mp3

# 수면 모니터링
python monitors/sleep/logger.py /path/to/snoring.mp3
```

### 5. 결과 확인

```bash
# 각 모니터별 로그
cat monitors/baby_cry/logs/cry_log_*.json
cat monitors/elder_care/logs/care_log_*.json
cat monitors/sleep/logs/sleep_log_*.json

# 주간 리포트 PDF (샘플 포함)
ls monitors/*/reports/*.pdf
```

---

## 프로젝트 구조

```
sense-claude-monitor/
├── .env                          # API 키 (git에 포함하지 않음)
├── .env.example                  # API 키 템플릿
├── README.md                     # 이 파일
├── docs/
│   └── PRD.md                    # Product Requirements Document
│
├── monitors/
│   ├── baby_cry/
│   │   ├── config.json           # Cochl SDK 설정
│   │   ├── logger.py             # 분석 스크립트
│   │   ├── logs/                 # JSON 분석 로그
│   │   │   └── cry_log_YYYYMMDD.json
│   │   └── reports/              # 주간 리포트 PDF
│   │       └── baby_cry_weekly_report_20260306.pdf
│   │
│   ├── elder_care/
│   │   ├── config.json
│   │   ├── logger.py
│   │   ├── logs/
│   │   │   └── care_log_YYYYMMDD.json
│   │   └── reports/
│   │       └── elder_care_weekly_report_20260306.pdf
│   │
│   └── sleep/
│       ├── config.json
│       ├── logger.py
│       ├── logs/
│       │   └── sleep_log_YYYYMMDD.json
│       └── reports/
│           └── sleep_weekly_report_20260306.pdf
│
└── venv/                         # Python 가상환경 (git에 포함하지 않음)
```

---

## 모니터별 감지 태그

모든 태그는 [Cochl.Sense Sound Tags](https://docs.cochl.ai/sense/home/soundtags/) 공식 목록 기반입니다.

### Baby Cry Monitor

| Tag | Severity | 용도 |
|-----|----------|------|
| `Baby_cry` | critical | 아기 울음 직접 감지 |
| `Scream` | high | 비명/공포 반응 |
| `Moan` | medium | 고통 신음 |
| `Baby_laughter` | info | 아기 웃음 (상태 참고) |

### Elder Care Monitor

| Tag | Severity | Category | 용도 |
|-----|----------|----------|------|
| `Thud` | critical | fall | 낙상 충격음 |
| `Glass_break` | critical | fall | 유리 깨짐 |
| `Scream` | critical | distress | 비명 |
| `Moan` | high | distress | 고통 신음 |
| `Vomit` | high | health | 구토 |
| `Cough` | medium | health | 기침 |
| `Footstep` | info | night_movement | 야간 움직임 |

### Sleep Monitor

| Tag | Severity | Category | 용도 |
|-----|----------|----------|------|
| `Snore` | high | snoring | 코골이 |
| `Cough` | medium | sleep_disruption | 수면 중 기침 |
| `Throat_clear` | medium | sleep_disruption | 목 가다듬기 |
| `Yawn` | info | sleep_quality | 하품 |

---

## 로그 포맷

각 분석 실행 시 `logs/` 폴더에 날짜별 JSON 파일이 생성됩니다.
같은 날 여러 번 실행하면 동일 파일에 append됩니다.

```json
[
  {
    "monitor": "baby_cry",
    "source_file": "sample.wav",
    "analyzed_at": "2026-03-06T03:10:42.553",
    "events": [
      {
        "tag": "Baby_cry",
        "confidence": 0.9710,
        "severity": "critical",
        "description": "Sound of a baby crying, often high-pitched and repetitive.",
        "start_time": 0,
        "end_time": 2
      }
    ]
  }
]
```

---

## 기술 스택

| 구성요소 | 기술 |
|----------|------|
| 음향 분석 | [Cochl.Sense Cloud API](https://docs.cochl.ai) v2.33.0 |
| Python SDK | `cochl` 1.0.12 (`cochl.sense`) |
| 에이전트 | Claude Code (Claude Opus 4.6) |
| 리포트 | matplotlib + reportlab PDF |
| 런타임 | Python 3.9+ |

---

## 주간 리포트 샘플

`monitors/*/reports/` 폴더에 3종의 샘플 리포트가 포함되어 있습니다:

- **Baby Cry** — 4일간 울음 5배 증가 추세, Physical Pain Zone 진입
- **Elder Care** — 낙상(Thud) 이벤트, 기침 새벽/야간 집중 패턴
- **Sleep** — 새벽 2-4시 코골이 집중, OSA(폐쇄성 수면무호흡) 의심

---

## Powered by

- [Cochl.Sense](https://www.cochl.ai/product/) — AI 음향 인식
- [sense-claude plugin](https://github.com/meanmin/sense-claude) — Claude Code 통합
