# 📋 Masterplan.md 구조 분석 보고서

> **분석 대상**: `docs/Plan/masterplan.md` (v2.0)  
> **분석 일자**: 2026-01-02  
> **분석 목적**: 구조적 문제, 논리적 오류, 논리적/구조적 공백 식별

---

## 📊 종합 평가

| 평가 항목 | 상태 | 심각도 |
|-----------|------|--------|
| **구조적 완결성** | 🟡 부분적 | Medium |
| **논리적 일관성** | 🟢 양호 | Low |
| **데이터 흐름 명확성** | 🟡 부분적 | Medium |
| **Phase 간 연결성** | 🟡 보완 필요 | Medium |
| **구현 가능성** | 🟢 양호 | Low |

---

## 1. 구조적 문제 (Structural Issues)

### 1.1 [MEDIUM] 섹션 번호 중복

**위치**: Section 3.2가 두 번 정의됨

| Line | 섹션 제목 |
|------|-----------|
| 131 | `3.2 Universe Filter Logic` |
| 141 | `3.2 Accumulation Stage Detection` |

**문제점**: 동일한 섹션 번호(3.2)가 두 개의 다른 주제에 사용되어 문서 참조 시 혼란 발생

**권장 수정**:
```diff
- ### 3.2 Universe Filter Logic (Local DB)
+ ### 3.2 Universe Filter Logic (Local DB)
...
- ### 3.2 Accumulation Stage Detection (매집 단계 탐지)
+ ### 3.3 Accumulation Stage Detection (매집 단계 탐지)
```

---

### 1.2 [LOW] 목차(TOC) 부재

**문제점**: 978줄의 대형 문서임에도 목차가 없어 탐색이 어려움

**권장 수정**: 문서 상단에 목차 추가
```markdown
## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Tech Stack](#2-tech-stack)
3. [Phase 1: The Setup](#3-phase-1-the-setup-strategy-scanning)
...
```

---

### 1.3 [LOW] 일관성 없는 하위 섹션 네이밍

**문제점**: 일부 섹션은 숫자 기반(`3.1.1`), 일부는 내용 기반 명명

| 패턴 | 예시 |
|------|------|
| 숫자 기반 | `3.1.1 실시간 데이터 파이프라인`, `3.2.1 매집 4단계` |
| 내용 기반 | `Phase 1: The Setup`, `Phase 2: The Trigger` |

---

## 2. 논리적 오류 (Logical Errors)

### 2.1 [HIGH] Class Diagram과 실제 구현 불일치

**위치**: Section 6.1 Class Diagram (Line 225-261)

**문서 내용**:
```mermaid
OmniController --> IBKRConnector
OmniController --> StrategyBase
```

**실제 구현**: 
- `OmniController` 클래스는 존재하지 않음
- 현재는 `server.py`의 `AppState`와 `FastAPI` 라우터가 해당 역할 수행
- `TradingEngine`이 전략 실행을 담당해야 하지만 아직 미구현 (KI 참조)

**권장 수정**: Class Diagram을 현재 구현에 맞게 업데이트하거나, `OmniController` 구현 계획 명시

---

### 2.2 [MEDIUM] Phase 2 Trigger 조건과 데이터 소스 불일치

**위치**: Section 4.1 Ignition Conditions (Line 180-186)

**문서 내용**:
| 조건 | 로직 |
|------|------|
| **Buy Pressure** | 시장가 매수/매도 > 1.8 |

**문제점**: 
- "시장가 매수/매도" 비율은 **Level 2 Quote Data** (Order Book) 필요
- 현재 Massive.com WebSocket은 `AM` (Aggregate Minute)과 `T` (Trades)만 지원
- Level 2 데이터는 IBKR에서만 가능하나, IBKR는 "주문 실행 전용"으로 정의됨 (Section 3.1)

**권장 수정**:
1. Buy Pressure 지표 계산 방법 재정의 (Tick 데이터 기반 추정 로직)
2. 또는 IBKR Level 2 데이터 활용 계획 명시

---

### 2.3 [MEDIUM] Anti-Trap Filter의 데이터 의존성 미명시

**위치**: Section 4.2 Anti-Trap Filter (Line 187-194)

**문서 내용**:
| 조건 | 설명 |
|------|------|
| VWAP 위에 위치 | 당일 평균 이상에서만 진입 |

**문제점**: 
- VWAP 계산에는 **당일 전체 틱 데이터**가 필요
- 실시간 VWAP 계산 모듈이 어디서 수행되는지 명시되지 않음

**권장 수정**: `technical_analysis.py` 또는 Strategy 내부에서 VWAP 계산 로직 위치 명시

---

## 3. 논리적/구조적 공백 (Logical Gaps)

### 3.1 [CRITICAL] TradingEngine 구현 누락

**문제점**: 
- Class Diagram에는 전략 실행 흐름이 `OmniController → StrategyBase` 로 표현
- 실제로는 `TradingEngine`이 전략 신호를 받아 주문 실행까지 연결해야 함
- KI 분석에서도 "Skipping the TradingEngine implementation... removes a vital abstraction layer"로 지적됨

**필요한 명시 사항**:
1. `TradingEngine`의 책임 범위
2. Strategy Signal → OrderManager 연결 로직
3. Multi-strategy 시 실행 우선순위 및 리스크 분배

---

### 3.2 [HIGH] Tier 2 → Entry 동선 미정의

**위치**: Section 7.4 Tiered Watchlist System (Line 408-454)

**문서 내용**:
- Tier 2 승격 조건: `Ignition ≥ 70 또는 Day Gainer`
- Tier 2 표시 항목: zenV, zenP 등

**공백**: 
- Tier 2에서 **실제 진입 트리거**까지의 흐름이 없음
- Ignition ≥ 70이면 자동 진입? 또는 수동 확인?
- zenV-zenP Divergence 전략 (Line 452-453)과 Ignition Score 기반 진입의 관계 불명확

**권장 수정**:
```markdown
### Tier 2 → Entry Flow
1. Tier 2 승격 시 IgnitionMonitor 자동 감시 시작
2. Ignition Score ≥ 70 && Anti-Trap OK → 자동 Market Buy
3. GUI에서 수동 Override 가능 (Toggle)
```

---

### 3.3 [HIGH] 마켓 시간 관리 로직 부재

**문제점**: 미국 주식 시장 관련 시간 로직이 문서에 없음

| 누락 항목 | 설명 |
|-----------|------|
| Pre-market / After-hours | 프리마켓(4:00-9:30) 및 애프터마켓(16:00-20:00) 처리 |
| Market Open 감지 | 장 시작 15분 이후 진입 (Section 4.2 언급)하려면 장 시작 시간 추적 필요 |
| 공휴일 처리 | NYSE/NASDAQ 휴장일 처리 |
| Timezone 관리 | Backend(AWS us-east-1) vs Frontend(Local) 시간대 동기화 |

**권장 수정**: `backend/core/market_hours.py` 또는 관련 모듈 정의 추가

---

### 3.4 [MEDIUM] 재시작/장애 복구 시나리오 부재

**문제점**: 다음 상황에서의 시스템 동작이 정의되지 않음

| 시나리오 | 필요한 정의 |
|----------|-------------|
| Backend 재시작 | 활성 주문 상태 복구, 포지션 동기화 |
| WebSocket 재연결 | 구독 복원 (일부 구현됨), 누락된 데이터 백필 |
| IBKR 연결 끊김 | 긴급 복구 절차, 미체결 주문 처리 |
| GUI 재연결 | 상태 동기화 (Watchlist, Positions, Engine Status) |

---

### 3.5 [MEDIUM] Double Tap 재진입의 불명확한 트리거

**위치**: Section 5.2 Double Tap (Line 211-218)

**문서 내용**:
```
3. Trigger: HOD 돌파 시 Stop-Limit @ HOD + $0.01
```

**공백**:
- HOD (High of Day)는 **실시간 추적** 필요
- HOD가 언제 업데이트되는지 (Bar 마감? 틱마다?)
- HOD 돌파 감지는 `on_tick()`에서? 아니면 별도 모듈?

**권장 수정**: `double_tap.py`에서 HOD 추적 메커니즘 명시

---

### 3.6 [MEDIUM] Backtesting 모듈의 데이터 흐름 미정의

**위치**: Section 12.1 프로젝트 구조 (Line 685-686)

**문서 내용**:
```
│   │   ├── backtest_engine.py        # 백테스팅 엔진
│   │   └── backtest_report.py        # 백테스트 리포트 생성
```

**공백**:
- 백테스팅에 사용되는 **히스토리 데이터 소스** 미정의 (SQLite? Polygon REST?)
- 실시간 전략 (`on_tick`, `on_bar`)과 백테스트 전략의 **인터페이스 호환성** 미정의
- Section 8.3에서 v5.0 LLM 백테스팅 언급되나, 현재 버전 계획 없음

---

### 3.7 [LOW] LLM External API 목록 불완전

**위치**: Section 8.2 External Data Integration (Line 470-481)

**문서 내용**:
| 소스 | 설명 |
|------|------|
| News API (Benzinga, etc) | "etc" 불명확 |
| SEC EDGAR Filings | 구체적 구현 방법 없음 |
| Social Sentiment | 데이터 소스 미정 (Twitter/X? Reddit?) |

**권장 수정**: 구체적인 API 공급자 및 엔드포인트 목록 추가

---

## 4. 데이터 흐름 관련 공백

### 4.1 [HIGH] Scanning → Watchlist → Ignition 흐름 상세화 필요

**현재 문서 흐름**:
```
[Strategy Scanning] → [Watchlist 50] → [Intraday Trigger] → [Entry]
```

**상세화 필요 사항**:

| 단계 | 누락된 정의 |
|------|-------------|
| Scanning → Watchlist | 스캔 주기 (시작 시 1회? 주기적?), 결과 저장 위치 |
| Watchlist → Tier 1 | 정확히 동일한 개념인지, 분리된 개념인지 |
| Tier 1 → Tier 2 승격 | 누가 승격을 트리거하는지 (IgnitionMonitor? Scanner?) |
| Tier 2 → Entry | 자동 진입 조건의 완전한 체크리스트 |

---

### 4.2 [MEDIUM] TickDispatcher의 역할 불명확

**위치**: Section 3.1.1 실시간 데이터 파이프라인 다이어그램 (Line 101-120)

**문서 내용**:
```
[TickBroadcaster] ───────▶ [IgnitionMonitor]
```

**문제점**: 
- `TickDispatcher`가 다이어그램에 없음
- KI에 따르면 `TickDispatcher`는 내부 모듈(TrailingStop, TradingEngine 등)에 분배하는 역할
- `TickBroadcaster`와 `TickDispatcher`의 역할 분담이 문서에서 혼란스러움

**권장 수정**: 두 컴포넌트의 책임 범위를 명확히 구분하여 다이어그램 업데이트

---

## 5. 버전 불일치 및 기타 문제

### 5.1 [LOW] GUI Chart 설명 불일치

**위치**: Section 7.1 Layout (Line 374-380)

**문서 내용**:
```
| **Center** | Lightweight Charts (VWAP, Stop 라인, 매매 마커) |
```

**실제 구현**: `PyQtGraph` 기반 차트 (Section 7.2에서 정확히 기술됨)

**권장 수정**: "Lightweight Charts" → "PyQtGraph Charts"로 통일

---

### 5.2 [LOW] chart_widget.py의 Legacy 상태 미설명

**위치**: Section 12.1 프로젝트 구조 (Line 718)

**문서 내용**:
```
│   │   ├── chart_widget.py           # (Legacy) TradingView 차트
```

**공백**: Legacy 모듈이 언제 제거될 예정인지, 현재 시스템에 영향을 주는지 불명확

---

## 6. 권장 조치 요약

| 우선순위 | 항목 | 조치 |
|----------|------|------|
| 🔴 CRITICAL | TradingEngine 정의 | Class Diagram 수정 + 구현 계획 섹션 추가 |
| 🔴 HIGH | Tier 2 → Entry 흐름 | 명확한 트리거 조건 및 흐름도 추가 |
| 🟠 HIGH | Buy Pressure 계산 | 데이터 소스 및 계산 로직 재정의 |
| 🟠 HIGH | 마켓 시간 관리 | 새 섹션 추가 (Market Hours, Holidays, Timezone) |
| 🟡 MEDIUM | 섹션 번호 중복 | 3.2 → 3.2/3.3으로 재번호화 |
| 🟡 MEDIUM | 장애 복구 시나리오 | 새 섹션 추가 (System Reliability의 하위 섹션) |
| 🟢 LOW | 목차 추가 | 문서 상단에 ToC 삽입 |
| 🟢 LOW | Layout 표의 차트 명칭 | "Lightweight Charts" → "PyQtGraph Charts" |

---

## 📎 참고 자료

- **기존 분석**: [logical_gap_analysis.md](file:///C:/Users/USER/.gemini/antigravity/knowledge/sigma9_core_engine/artifacts/research/logical_gap_analysis.md) (KI: sigma9_core_engine)
- **원본 문서**: [masterplan.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/masterplan.md)
