# Sense Claude Monitor

An acoustic health monitoring system powered by Cochl.Sense Cloud API + Claude Code.
Detects baby crying, elder care events, and sleep disorders in real time, with automated weekly analysis reports.

---

## Quick Start (5-Minute Setup)

### 1. Download the Project

```bash
git clone https://github.com/meanmin/sense-claude-monitor.git
cd sense-claude-monitor
```

Or download the ZIP and extract it.

### 2. Install the sense-claude Plugin (Claude Code Users)

If you use [Claude Code](https://claude.com/claude-code), install the [sense-claude plugin](https://github.com/meanmin/sense-claude) for guided Cochl.Sense integration:

```bash
/plugin marketplace add meanmin/sense-claude
/plugin install cochl-sense-api
```

### 3. Create Python Virtual Environment + Install Dependencies

> Python 3.9 or higher required. Python 3.11+ requires a virtual environment.

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install python-dotenv
pip install cochl --no-deps
pip install soundfile requests numpy python-dateutil urllib3 pydantic
```

### 4. Configure API Key

Get your project key from the [Cochl Dashboard](https://dashboard.cochl.ai).

```bash
cp .env.example .env
# Open .env and replace with your actual key
```

```
COCHL_API_KEY=your_actual_api_key_here
```

### 5. Run Audio Analysis

Provide your own audio file as an argument. Supported formats: `.wav`, `.mp3`, `.flac`, `.ogg`, etc.

```bash
# Baby cry analysis
python monitors/baby_cry/logger.py your_audio_file.mp3

# Elder care analysis
python monitors/elder_care/logger.py your_audio_file.mp3

# Sleep monitoring
python monitors/sleep/logger.py your_audio_file.mp3
```

### 6. View Results

```bash
# Per-monitor logs
cat monitors/baby_cry/logs/cry_log_*.json
cat monitors/elder_care/logs/care_log_*.json
cat monitors/sleep/logs/sleep_log_*.json

# Weekly report PDFs (samples included)
ls monitors/*/reports/*.pdf
```

---

## Project Structure

```
sense-claude-monitor/
├── .env                          # API key (not included in git)
├── .env.example                  # API key template
├── README.md                     # This file
├── docs/
│   └── PRD.md                    # Product Requirements Document
│
├── monitors/
│   ├── baby_cry/
│   │   ├── config.json           # Cochl SDK configuration
│   │   ├── logger.py             # Analysis script
│   │   ├── logs/                 # JSON analysis logs
│   │   │   └── cry_log_YYYYMMDD.json
│   │   └── reports/              # Example weekly report PDFs
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
└── venv/                         # Python virtual environment (not in git)
```

---

## Detection Tags by Monitor

All tags are based on the official [Cochl.Sense Sound Tags](https://docs.cochl.ai/sense/home/soundtags/) list.

### Baby Cry Monitor

| Tag | Purpose |
|-----|---------|
| `Baby_cry` | Direct baby crying detection |
| `Scream` | Fear/distress response |
| `Moan` | Pain-related groaning |
| `Baby_laughter` | Baby laughter (baseline reference) |

### Elder Care Monitor

| Tag | Category | Purpose |
|-----|----------|---------|
| `Thud` | fall | Fall impact sound |
| `Glass_break` | fall | Glass breaking |
| `Scream` | distress | Screaming |
| `Moan` | distress | Pain-related groaning |
| `Vomit` | health | Vomiting |
| `Cough` | health | Coughing |
| `Footstep` | night_movement | Nighttime movement |

### Sleep Monitor

| Tag | Category | Purpose |
|-----|----------|---------|
| `Snore` | snoring | Snoring |
| `Cough` | sleep_disruption | Coughing during sleep |
| `Throat_clear` | sleep_disruption | Throat clearing |
| `Yawn` | sleep_quality | Yawning |

---

## Log Format

Each analysis run generates a date-based JSON file in the `logs/` folder.
Multiple runs on the same day are appended to the same file.

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

## Tech Stack

| Component | Technology |
|-----------|------------|
| Sound Analysis | [Cochl.Sense Cloud API](https://docs.cochl.ai) v2.33.0 |
| Python SDK | `cochl` 1.0.12 (`cochl.sense`) |
| Agent | Claude Code (Claude Opus 4.6) |
| Reports | matplotlib + reportlab PDF |
| Runtime | Python 3.9+ |

---

## Weekly Report Samples

The `monitors/*/reports/` folders contain **example reports** generated from the included sample data.
These demonstrate the kind of output you can expect when running the system with your own audio files.

- **Baby Cry** — 5x increase in crying over 4 days, entering Physical Pain Zone
- **Elder Care** — Fall (Thud) event detected, coughing concentrated at dawn/night
- **Sleep** — Snoring concentrated at 2-4 AM, suspected OSA (Obstructive Sleep Apnea)

---

## Powered by

- [Cochl.Sense](https://www.cochl.ai/product/) — AI Sound Recognition
- [sense-claude plugin](https://github.com/meanmin/sense-claude) — Claude Code Integration
