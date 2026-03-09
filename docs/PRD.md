# Product Requirements Document (PRD)

## Sense Claude Monitor — AI Acoustic Health Monitoring System

| Field | Details |
|-------|---------|
| **Project** | sense-claude-monitor |
| **Version** | 1.0.0 |
| **Date** | 2026-03-06 |
| **Authors** | Claude Code (Opus 4.6) + Human |
| **Status** | MVP Complete — 3 Monitors + Sample Reports |

---

## 1. Overview

### 1.1 Project Purpose

A monitoring system that combines Cochl.Sense Cloud API's acoustic recognition technology with Claude Code agent to detect, record, and generate weekly analysis reports for health-related sounds occurring in home environments.

### 1.2 Core Values

- **Contactless Monitoring** — Health status tracking through sound only, no cameras
- **Pattern-Based Insights** — Trend analysis over 4+ days, not just individual events
- **Ready to Use** — Download folder, enter API key, run immediately
- **3 Specialized Monitors** — Baby care, elder care, sleep health

### 1.3 Target Users

| User | Scenario |
|------|----------|
| New Parents | Track nighttime crying patterns, provide objective data for pediatric consultations |
| Elder Caregivers | Fall detection, nighttime cough monitoring, early detection of health deterioration |
| Sleep Disorder Patients | Record snoring patterns, collect screening data for OSA (Obstructive Sleep Apnea) |

---

## 2. Technical Architecture

### 2.1 System Diagram

```
[Audio File]
     │
     ▼
[logger.py] ── cochl.sense SDK ──▶ [Cochl.Sense Cloud API]
     │                                       │
     │              ◀── window_results ──────┘
     ▼
[filter_events()]  →  SOUND_TAGS matching
     │
     ▼
[save_log()]  →  logs/*_log_YYYYMMDD.json
     │
     ▼
[Claude Code]  →  reports/*_weekly_report.pdf
```

### 2.2 Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Sound Analysis Engine | Cochl.Sense Cloud API | v2.33.0 (2025-07-20) |
| Python SDK | `cochl` (cochl.sense) | 1.0.12 |
| SDK Configuration | sense-claude plugin pattern | 2.0.0 |
| Agent | Claude Code | Opus 4.6 |
| Report Generation | matplotlib + reportlab | — |
| Runtime | Python | 3.9+ |

### 2.3 Cochl.Sense SDK Integration

Adopted the [sense-claude plugin](https://github.com/meanmin/sense-claude) pattern:

```python
import cochl.sense as sense

api_config = sense.APIConfigFromJson("config.json")
client = sense.Client(api_key, api_config=api_config)
result = client.predict(audio_file)
events_data = result.events.to_dict(api_config)
window_results = events_data.get("window_results", [])
```

Using the official SDK instead of direct REST API calls:
- SDK handles authentication, file upload, and response parsing
- Inference settings externalized via `config.json`
- `window_results` structure provides per-window tags + probability values

---

## 3. Monitor Design

### 3.1 Baby Cry Monitor

| Field | Details |
|-------|---------|
| **Purpose** | Track baby crying patterns and detect early health anomalies |
| **Script** | `monitors/baby_cry/logger.py` |
| **Log File** | `logs/cry_log_YYYYMMDD.json` |
| **Report** | `reports/baby_cry_weekly_report_YYYYMMDD.pdf` |

**Detection Tags:**

| Tag | Cochl Category | Severity | Selection Rationale |
|-----|---------------|----------|---------------------|
| `Baby_cry` | Human status | critical | Primary target — direct baby cry detection |
| `Scream` | Emergency | high | Fear/pain response — emergency supplementary indicator |
| `Moan` | Human status | medium | Pain groaning — tracking persistent discomfort |
| `Baby_laughter` | Human status | info | Normal state verification — baseline comparison |

**Report Analysis Items:**
1. Daily Event Breakdown (daily event trend chart)
2. Cry Intensity Score Trend (Normal/Caution/Pain Zone)
3. Cry Distribution by Hour (hourly crying distribution)
4. Recommendations (pediatric consultation, feeding, sleep environment)

### 3.2 Elder Care Monitor

| Field | Details |
|-------|---------|
| **Purpose** | Fall detection, cough pattern tracking, nighttime movement monitoring |
| **Script** | `monitors/elder_care/logger.py` |
| **Log File** | `logs/care_log_YYYYMMDD.json` |
| **Report** | `reports/elder_care_weekly_report_YYYYMMDD.pdf` |

**Detection Tags:**

| Tag | Cochl Category | Severity | Category | Selection Rationale |
|-----|---------------|----------|----------|---------------------|
| `Thud` | Home context | critical | fall | Fall impact sound — requires immediate response |
| `Glass_break` | Emergency | critical | fall | Glass breaking — possible fall accompaniment |
| `Scream` | Emergency | critical | distress | Screaming — emergency situation |
| `Moan` | Human status | high | distress | Pain groaning — unable to call for help |
| `Vomit` | Human status | high | health | Vomiting — health deterioration indicator |
| `Cough` | Human status | medium | health | Coughing — respiratory status tracking |
| `Footstep` | Human action | info | night_movement | Nighttime movement — identifying fall-risk time windows |

**Report Analysis Items:**
1. Daily Health Event Breakdown (daily health event chart)
2. Cough Frequency Trend (Normal/Watch/Alert Zone)
3. Cough Distribution by Hour (hourly cough distribution)
4. Fall-Risk Incident Detail (suspected fall event details)
5. Recommendations (fall verification, medical consultation, nighttime safety, symptom logging)

### 3.3 Sleep Monitor

| Field | Details |
|-------|---------|
| **Purpose** | Snoring pattern tracking and OSA (Obstructive Sleep Apnea) screening |
| **Script** | `monitors/sleep/logger.py` |
| **Log File** | `logs/sleep_log_YYYYMMDD.json` |
| **Report** | `reports/sleep_weekly_report_YYYYMMDD.pdf` |

**Detection Tags:**

| Tag | Cochl Category | Severity | Category | Selection Rationale |
|-----|---------------|----------|----------|---------------------|
| `Snore` | Human status | high | snoring | Primary target — snoring detection |
| `Cough` | Human status | medium | sleep_disruption | Coughing during sleep — sleep fragmentation indicator |
| `Throat_clear` | Human status | medium | sleep_disruption | Throat clearing — sleep disturbance |
| `Yawn` | Human status | info | sleep_quality | Yawning — sleep debt/fatigue indicator |

**Report Analysis Items:**
1. Nightly Event Breakdown (nightly event trend chart)
2. Snoring Intensity + Sleep Disruption Index (dual chart)
3. Snoring Distribution by Hour (hourly snoring distribution — REM sleep band)
4. Recommendations (polysomnography, side sleeping, CPAP, weight management)

---

## 4. Data Pipeline

### 4.1 Analysis Flow

```
Audio Input → Send to Cochl API → Receive window_results
    → SOUND_TAGS filtering → severity mapping + console logging
    → JSON file save (daily append)
    → Claude Code reads JSON and generates weekly report PDF
```

### 4.2 JSON Log Schema

```json
{
  "monitor": "string (baby_cry | elder_care | sleep)",
  "source_file": "string (filename)",
  "analyzed_at": "string (ISO 8601)",
  "events": [
    {
      "tag": "string (Cochl Sound Tag)",
      "confidence": "float (0.0 ~ 1.0)",
      "severity": "string (critical | high | medium | info)",
      "category": "string (optional, elder_care/sleep only)",
      "description": "string (tag description)",
      "start_time": "float (seconds)",
      "end_time": "float (seconds)"
    }
  ]
}
```

### 4.3 SDK Configuration (config.json)

```json
{
  "format": { "type": "json" },
  "inference": {
    "result_summarization": { "interval_margin": 1 }
  }
}
```

- `interval_margin: 1` — 1-second sliding window analysis
- Identical configuration file placed in each monitor directory

---

## 5. Deliverables

### 5.1 Key Files

| Type | File | Description |
|------|------|-------------|
| **Agent Config** | `monitors/*/config.json` (x3) | Cochl SDK inference settings |
| **Analysis Scripts** | `monitors/baby_cry/logger.py` | Baby cry analysis |
| | `monitors/elder_care/logger.py` | Elder care analysis |
| | `monitors/sleep/logger.py` | Sleep monitor analysis |
| **Sample Logs** | `monitors/*/logs/*.json` (x12) | 4 days x 3 monitors |
| **Report PDFs** | `monitors/baby_cry/reports/baby_cry_weekly_report_20260306.pdf` | 4 pages, 3 charts |
| | `monitors/elder_care/reports/elder_care_weekly_report_20260306.pdf` | 5 pages, 3 charts + fall detail |
| | `monitors/sleep/reports/sleep_weekly_report_20260306.pdf` | 4 pages, dual chart + hourly distribution |
| **Documentation** | `README.md` | Setup Guide |
| | `docs/PRD.md` | This document |
| | `.env.example` | API key template |

### 5.2 Report PDF Details

**Baby Cry Weekly Report (4 pages)**
- p1: KPI cards + Daily Event Breakdown (stacked bar chart + table)
- p2: Cry Intensity Score Trend (line chart, Pain/Caution/Normal zones)
- p3: Cry Distribution by Hour (bar chart, overnight window highlight)
- p4: Recommendations (4 action items, color-coded cards)

**Elder Care Weekly Report (5 pages)**
- p1: KPI cards + Daily Health Event Breakdown (stacked bar chart + table)
- p2: Cough Frequency Trend (line chart, Alert/Watch/Normal zones)
- p3: Cough Distribution by Hour (bar chart, overnight window highlight)
- p4: Fall-Risk Incident Detail (red alert box)
- p5: Recommendations (5 action items)

**Sleep Weekly Report (4 pages)**
- p1: KPI cards + Nightly Event Breakdown (stacked bar chart + table)
- p2: Snoring Intensity + Sleep Disruption Index (dual chart)
- p3: Snoring Distribution by Hour (bar chart, REM sleep band highlight)
- p4: Recommendations (5 action items)

---

## 6. Sample Data Pattern Design

### 6.1 Baby Cry — Increasing Cry Trend

| Date | Baby_cry | Scream | Moan | Avg Confidence | Design Intent |
|------|----------|--------|------|---------------|---------------|
| Mar 3 | 3 | 0 | 0 | 0.62 | Normal baseline |
| Mar 4 | 6 | 1 | 1 | 0.76 | Anomaly onset |
| Mar 5 | 9 | 1 | 2 | 0.89 | Entering Caution Zone |
| Mar 6 | 16 | 3 | 1 | 0.94 | Physical Pain Zone — 5x increase |

### 6.2 Elder Care — Dawn/Night Cough Concentration

| Date | Cough | Peak Hours | Special Events | Design Intent |
|------|-------|------------|----------------|---------------|
| Mar 3 | 9 | 06h, 22h | — | Watch Zone onset |
| Mar 4 | 11 | 05-07h, 23h | Vomit (07h) | Accompanied by vomiting |
| Mar 5 | 11 | 05-06h, 22h | Thud (02:30) | Suspected fall event |
| Mar 6 | 12 | 06-07h, 22h | Vomit (06h) | Entering Alert Zone |

### 6.3 Sleep — 2-4 AM Snoring Concentration

| Date | Snore | 2-4 AM Ratio | Fatigue Indicators | Design Intent |
|------|-------|-------------|-------------------|---------------|
| Mar 3 | 10 | 80% | — | Establishing REM band concentration |
| Mar 4 | 12 | 85% | Yawn x2 | Daytime drowsiness onset |
| Mar 5 | 16 | 88% | Yawn x2, Cough | Entering Severe Zone |
| Mar 6 | 16 | 90% | Yawn x1, Cough | OSA suspicion confirmed |

---

## 7. Development History

| Phase | Work Description | Deliverable |
|-------|-----------------|-------------|
| 1 | Investigated full Cochl Sound Tags list (15-page PDF analysis) | Tag inventory |
| 2 | Selected tags per monitor + initial logger.py creation | `logger.py` x3 (v1, console only) |
| 3 | Refactored baby_cry/logger.py for actual Cochl API integration | `logger.py` (v2, httpx) |
| 4 | Full migration to sense-claude plugin pattern (cochl.sense SDK) | `logger.py` (v3, SDK) + `config.json` |
| 5 | Tested all 3 monitors with real audio (baby_cry.mp3, coughing.mp3, snoring.mp3) | Actual analysis logs |
| 6 | Generated 4-day sample data (with designed patterns) | JSON x12 |
| 7 | Created weekly report PDFs (charts + analysis + recommendations) | PDF x3 |
| 8 | Wrote Setup Guide + PRD | README.md, docs/PRD.md |

---

## 8. Future Extensions

| Feature | Description |
|---------|-------------|
| Real-time Streaming Analysis | Microphone input → cochl.sense real-time mode |
| Alert Integration | Slack/LINE/push notification for Thud, Scream events |
| Dashboard | Flask/FastAPI web dashboard for real-time monitoring |
| Multi-Monitor Concurrent Execution | asyncio-based parallel processing of all 3 monitors |
| Automated Reporting | cron + Claude Code for automatic weekly report generation |
| Custom Tags | User-defined sound tags via Cochl Dashboard |

---

*Generated by Claude Code (Opus 4.6) — Powered by Cochl.Sense Cloud API v2.33.0*
