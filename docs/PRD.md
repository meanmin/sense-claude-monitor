# Product Requirements Document (PRD)

## Sense Claude Monitor — AI 음향 기반 건강 모니터링 시스템

| 항목 | 내용 |
|------|------|
| **프로젝트명** | sense-claude-monitor |
| **버전** | 1.0.0 |
| **작성일** | 2026-03-06 |
| **작성자** | Claude Code (Opus 4.6) + Human |
| **상태** | MVP 완료 — 3종 모니터 + 샘플 리포트 |

---

## 1. 개요

### 1.1 프로젝트 목적

Cochl.Sense Cloud API의 음향 인식 기술과 Claude Code 에이전트를 결합하여,
가정 환경에서 발생하는 건강 관련 소리를 실시간으로 감지·기록하고
주간 분석 리포트를 자동 생성하는 모니터링 시스템.

### 1.2 핵심 가치

- **비접촉 모니터링** — 카메라 없이 음향만으로 건강 상태 파악
- **패턴 기반 인사이트** — 단일 이벤트가 아닌 4일 이상의 추세 분석
- **즉시 사용 가능** — 폴더 다운로드 → API 키 입력 → 바로 실행
- **3가지 전문 모니터** — 아기 케어, 노인 케어, 수면 건강

### 1.3 대상 사용자

| 사용자 | 시나리오 |
|--------|----------|
| 신생아 부모 | 야간 울음 패턴 추적, 소아과 상담 시 객관적 데이터 제공 |
| 노인 보호자/요양사 | 낙상 감지, 야간 기침 모니터링, 건강 악화 조기 발견 |
| 수면 장애 환자 | 코골이 패턴 기록, 수면무호흡증(OSA) 선별 데이터 확보 |

---

## 2. 기술 아키텍처

### 2.1 시스템 구성도

```
[Audio File]
     │
     ▼
[logger.py] ── cochl.sense SDK ──▶ [Cochl.Sense Cloud API]
     │                                       │
     │              ◀── window_results ──────┘
     ▼
[filter_events()]  →  SOUND_TAGS 매칭
     │
     ▼
[save_log()]  →  logs/*_log_YYYYMMDD.json
     │
     ▼
[Claude Code]  →  reports/*_weekly_report.pdf
```

### 2.2 기술 스택

| 레이어 | 기술 | 버전 |
|--------|------|------|
| 음향 분석 엔진 | Cochl.Sense Cloud API | v2.33.0 (2025-07-20) |
| Python SDK | `cochl` (cochl.sense) | 1.0.12 |
| SDK 설정 | sense-claude plugin 패턴 | 2.0.0 |
| 에이전트 | Claude Code | Opus 4.6 |
| 리포트 생성 | matplotlib + reportlab | — |
| 런타임 | Python | 3.9+ |

### 2.3 Cochl.Sense SDK 통합 방식

[sense-claude plugin](https://github.com/meanmin/sense-claude) 패턴을 채택:

```python
import cochl.sense as sense

api_config = sense.APIConfigFromJson("config.json")
client = sense.Client(api_key, api_config=api_config)
result = client.predict(audio_file)
events_data = result.events.to_dict(api_config)
window_results = events_data.get("window_results", [])
```

REST API 직접 호출 대신 공식 SDK를 사용하여:
- 인증, 파일 업로드, 응답 파싱을 SDK가 처리
- `config.json`으로 추론 설정을 외부화
- `window_results` 구조로 시간대별 태그 + 확률값 수신

---

## 3. 모니터 설계

### 3.1 Baby Cry Monitor

| 항목 | 내용 |
|------|------|
| **목적** | 아기 울음 패턴 추적 및 건강 이상 조기 발견 |
| **스크립트** | `monitors/baby_cry/logger.py` |
| **로그 파일** | `logs/cry_log_YYYYMMDD.json` |
| **리포트** | `reports/baby_cry_weekly_report_YYYYMMDD.pdf` |

**감지 태그:**

| Tag | Cochl 분류 | Severity | 선정 근거 |
|-----|-----------|----------|-----------|
| `Baby_cry` | Human status | critical | 핵심 감지 대상 — 아기 울음 직접 감지 |
| `Scream` | Emergency | high | 공포/고통 반응 — 긴급 상황 보조 지표 |
| `Moan` | Human status | medium | 고통 신음 — 불편함 지속 여부 추적 |
| `Baby_laughter` | Human status | info | 정상 상태 확인용 — 베이스라인 비교 |

**리포트 분석 항목:**
1. Daily Event Breakdown (일별 이벤트 추이 차트)
2. Cry Intensity Score Trend (울음 강도 추세 — Normal/Caution/Pain Zone)
3. Cry Distribution by Hour (시간대별 울음 분포)
4. Recommendations (소아과 상담, 수유, 수면환경 권고)

### 3.2 Elder Care Monitor

| 항목 | 내용 |
|------|------|
| **목적** | 노인 낙상 감지, 기침 패턴 추적, 야간 움직임 모니터링 |
| **스크립트** | `monitors/elder_care/logger.py` |
| **로그 파일** | `logs/care_log_YYYYMMDD.json` |
| **리포트** | `reports/elder_care_weekly_report_YYYYMMDD.pdf` |

**감지 태그:**

| Tag | Cochl 분류 | Severity | Category | 선정 근거 |
|-----|-----------|----------|----------|-----------|
| `Thud` | Home context | critical | fall | 낙상 충격음 — 즉각 대응 필요 |
| `Glass_break` | Emergency | critical | fall | 유리 깨짐 — 낙상 동반 가능성 |
| `Scream` | Emergency | critical | distress | 비명 — 긴급 상황 |
| `Moan` | Human status | high | distress | 고통 신음 — 도움 요청 불가 상태 |
| `Vomit` | Human status | high | health | 구토 — 건강 악화 지표 |
| `Cough` | Human status | medium | health | 기침 — 호흡기 상태 추적 |
| `Footstep` | Human action | info | night_movement | 야간 움직임 — 낙상 위험 시간대 파악 |

**리포트 분석 항목:**
1. Daily Health Event Breakdown (일별 건강 이벤트 차트)
2. Cough Frequency Trend (기침 빈도 추세 — Normal/Watch/Alert Zone)
3. Cough Distribution by Hour (시간대별 기침 분포)
4. Fall-Risk Incident Detail (낙상 의심 이벤트 상세)
5. Recommendations (낙상 확인, 진료, 야간 안전장치, 증상 기록)

### 3.3 Sleep Monitor

| 항목 | 내용 |
|------|------|
| **목적** | 코골이 패턴 추적 및 수면무호흡증(OSA) 선별 |
| **스크립트** | `monitors/sleep/logger.py` |
| **로그 파일** | `logs/sleep_log_YYYYMMDD.json` |
| **리포트** | `reports/sleep_weekly_report_YYYYMMDD.pdf` |

**감지 태그:**

| Tag | Cochl 분류 | Severity | Category | 선정 근거 |
|-----|-----------|----------|----------|-----------|
| `Snore` | Human status | high | snoring | 핵심 감지 대상 — 코골이 |
| `Cough` | Human status | medium | sleep_disruption | 수면 중 기침 — 수면 분절 지표 |
| `Throat_clear` | Human status | medium | sleep_disruption | 목 가다듬기 — 수면 방해 |
| `Yawn` | Human status | info | sleep_quality | 하품 — 수면 부채/피로 지표 |

**리포트 분석 항목:**
1. Nightly Event Breakdown (야간 이벤트 추이 차트)
2. Snoring Intensity & Sleep Disruption Index (듀얼 차트)
3. Snoring Distribution by Hour (시간대별 코골이 분포 — REM 수면 대역)
4. Recommendations (수면다원검사, 옆으로 자기, CPAP, 체중 관리)

---

## 4. 데이터 파이프라인

### 4.1 분석 흐름

```
오디오 입력 → Cochl API 전송 → window_results 수신
    → SOUND_TAGS 필터링 → severity 매핑 + 콘솔 로그
    → JSON 파일 저장 (날짜별 append)
    → Claude Code가 JSON 읽고 주간 리포트 PDF 생성
```

### 4.2 JSON 로그 스키마

```json
{
  "monitor": "string (baby_cry | elder_care | sleep)",
  "source_file": "string (파일명)",
  "analyzed_at": "string (ISO 8601)",
  "events": [
    {
      "tag": "string (Cochl Sound Tag)",
      "confidence": "float (0.0 ~ 1.0)",
      "severity": "string (critical | high | medium | info)",
      "category": "string (선택, elder_care/sleep만 해당)",
      "description": "string (태그 설명)",
      "start_time": "float (초)",
      "end_time": "float (초)"
    }
  ]
}
```

### 4.3 SDK 설정 (config.json)

```json
{
  "format": { "type": "json" },
  "inference": {
    "result_summarization": { "interval_margin": 1 }
  }
}
```

- `interval_margin: 1` — 1초 간격 슬라이딩 윈도우로 분석
- 각 모니터 디렉토리에 동일 설정 파일 배치

---

## 5. 산출물 목록

### 5.1 핵심 파일

| 구분 | 파일 | 설명 |
|------|------|------|
| **에이전트 설정** | `monitors/*/config.json` (x3) | Cochl SDK 추론 설정 |
| **분석 스크립트** | `monitors/baby_cry/logger.py` | 아기 울음 분석 |
| | `monitors/elder_care/logger.py` | 노인 케어 분석 |
| | `monitors/sleep/logger.py` | 수면 모니터 분석 |
| **샘플 로그** | `monitors/*/logs/*.json` (x12) | 4일치 x 3모니터 |
| **리포트 PDF** | `monitors/baby_cry/reports/baby_cry_weekly_report_20260306.pdf` | 4p, 차트 3개 |
| | `monitors/elder_care/reports/elder_care_weekly_report_20260306.pdf` | 5p, 차트 3개 + 낙상 상세 |
| | `monitors/sleep/reports/sleep_weekly_report_20260306.pdf` | 4p, 듀얼 차트 + 시간대 분포 |
| **문서** | `README.md` | Setup Guide |
| | `docs/PRD.md` | 이 문서 |
| | `.env.example` | API 키 템플릿 |

### 5.2 리포트 PDF 상세

**Baby Cry Weekly Report (4페이지)**
- p1: KPI 카드 + Daily Event Breakdown (스택 바 차트 + 테이블)
- p2: Cry Intensity Score Trend (라인 차트, Pain/Caution/Normal 존)
- p3: Cry Distribution by Hour (바 차트, Overnight window 하이라이트)
- p4: Recommendations (4개 권고사항, 색상 구분 카드)

**Elder Care Weekly Report (5페이지)**
- p1: KPI 카드 + Daily Health Event Breakdown (스택 바 차트 + 테이블)
- p2: Cough Frequency Trend (라인 차트, Alert/Watch/Normal 존)
- p3: Cough Distribution by Hour (바 차트, Overnight window 하이라이트)
- p4: Fall-Risk Incident Detail (빨간 경고 박스)
- p5: Recommendations (5개 권고사항)

**Sleep Weekly Report (4페이지)**
- p1: KPI 카드 + Nightly Event Breakdown (스택 바 차트 + 테이블)
- p2: Snoring Intensity + Sleep Disruption Index (듀얼 차트)
- p3: Snoring Distribution by Hour (바 차트, REM 수면 대역 하이라이트)
- p4: Recommendations (5개 권고사항)

---

## 6. 샘플 데이터 패턴 설계

### 6.1 Baby Cry — 울음 증가 추세

| 날짜 | Baby_cry | Scream | Moan | Avg Confidence | 설계 의도 |
|------|----------|--------|------|---------------|-----------|
| Mar 3 | 3 | 0 | 0 | 0.62 | 정상 베이스라인 |
| Mar 4 | 6 | 1 | 1 | 0.76 | 이상 징후 시작 |
| Mar 5 | 9 | 1 | 2 | 0.89 | Caution Zone 진입 |
| Mar 6 | 16 | 3 | 1 | 0.94 | Physical Pain Zone — 5배 증가 |

### 6.2 Elder Care — 새벽/야간 기침 집중

| 날짜 | Cough | 집중 시간대 | 특이 이벤트 | 설계 의도 |
|------|-------|-----------|-----------|-----------|
| Mar 3 | 9 | 06시, 22시 | — | Watch Zone 시작 |
| Mar 4 | 11 | 05-07시, 23시 | Vomit (07시) | 구토 동반 |
| Mar 5 | 11 | 05-06시, 22시 | Thud (02:30) | 낙상 의심 이벤트 |
| Mar 6 | 12 | 06-07시, 22시 | Vomit (06시) | Alert Zone 진입 |

### 6.3 Sleep — 새벽 2-4시 코골이 집중

| 날짜 | Snore | 2-4시 비율 | 피로 지표 | 설계 의도 |
|------|-------|----------|----------|-----------|
| Mar 3 | 10 | 80% | — | REM 대역 집중 패턴 확립 |
| Mar 4 | 12 | 85% | Yawn x2 | 주간 졸음 시작 |
| Mar 5 | 16 | 88% | Yawn x2, Cough | Severe Zone 진입 |
| Mar 6 | 16 | 90% | Yawn x1, Cough | OSA 의심 확정 |

---

## 7. 작업 이력

| 단계 | 작업 내용 | 산출물 |
|------|----------|--------|
| 1 | Cochl Sound Tags 전체 목록 조사 (PDF 15p 분석) | 태그 목록 확보 |
| 2 | 3종 모니터별 적합 태그 선정 + 초기 logger.py 생성 | `logger.py` x3 (v1, 콘솔 전용) |
| 3 | 실제 Cochl API 연동 구조로 baby_cry/logger.py 리팩토링 | `logger.py` (v2, httpx) |
| 4 | sense-claude plugin 방식(cochl.sense SDK)으로 전면 전환 | `logger.py` (v3, SDK) + `config.json` |
| 5 | 3종 모니터 실제 오디오 테스트 (baby_cry.mp3, coughing.mp3, snoring.mp3) | 실제 분석 로그 |
| 6 | 4일치 샘플 데이터 생성 (패턴 설계 포함) | JSON x12 |
| 7 | 주간 리포트 PDF 생성 (차트 + 분석 + 권고) | PDF x3 |
| 8 | Setup Guide + PRD 작성 | README.md, docs/PRD.md |

---

## 8. 향후 확장 가능성

| 기능 | 설명 |
|------|------|
| 실시간 스트리밍 분석 | 마이크 입력 → cochl.sense 실시간 모드 전환 |
| 알림 연동 | Slack/LINE/카카오톡 즉시 알림 (Thud, Scream 등) |
| 대시보드 | Flask/FastAPI 웹 대시보드로 실시간 모니터링 |
| 다중 모니터 동시 실행 | asyncio 기반 3종 모니터 병렬 처리 |
| 리포트 자동화 | cron + Claude Code로 매주 자동 리포트 생성 |
| 커스텀 태그 | Cochl Dashboard에서 사용자 정의 사운드 태그 추가 |

---

*Generated by Claude Code (Opus 4.6) — Powered by Cochl.Sense Cloud API v2.33.0*
