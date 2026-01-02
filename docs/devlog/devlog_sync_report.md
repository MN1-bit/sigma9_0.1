# 📋 Devlog → 상위 문서 업데이트 필요 사항

> **분석 일자**: 2026-01-02  
> **분석 대상**: `docs/devlog/` 내 35개 파일  
> **대상 문서**: `development_steps.md`, `masterplan.md`

---

## 요약

| 문서 | 업데이트 필요 항목 수 |
|------|---------------------|
| `development_steps.md` | 12 |
| `masterplan.md` | 5 |

---

## 1. development_steps.md 업데이트 필요 사항

### 1.1 [CRITICAL] Phase 4.A.0 체크리스트 불일치

**현재 상태** (Lines 173-177):
```markdown
#### Phase 4.A.0: 실시간 데이터 파이프라인 (선행 필수)
- [ ] 4.A.0.1: IBKR Tick 스트리밍 → WebSocket 브로드캐스트
- [ ] 4.A.0.2: Intraday Bar 데이터 API (1m, 5m)
- [ ] 4.A.0.3: Chart 실시간 업데이트 (Tick → Candlestick)
- [ ] 4.A.0.4: Watchlist 종목 Tick 구독 관리
```

**실제 완료 사항 (devlog 기반)**:

| Devlog | 작업 내용 | 완료 여부 |
|--------|----------|----------|
| `step_4.a.0_report.md` | Massive WebSocket 통합, IBKR 시세 대체 | ✅ |
| `step_4.a.0.b.1_report.md` | TickDispatcher 생성 | ✅ |
| `step_4.a.0.b.2_report.md` | 전략 모듈 연결 (Seismograph on_tick) | ✅ |
| `step_4.a.0.b.3_report.md` | TradingEngine 연결 - **SKIP** | ⏭️ |
| `step_4.a.0.b.4_report.md` | TrailingStop 연결 | ✅ |
| `step_4.a.0.b.5_report.md` | Tier 2 GUI 연결 (tick_received) | ✅ |
| `step_4.a.0.b.6_report.md` | 구독 자동화 (sync_tick_subscriptions) | ✅ |
| `step_4.a.0.c_report.md` | 버그 수정 (listen() 루프, 초기 구독) | ✅ |

**권장 수정**:
```markdown
#### Phase 4.A.0: 실시간 데이터 파이프라인 ✅ COMPLETED
> 📝 IBKR Tick → **Massive WebSocket (AM/T 채널)**으로 전환

- [x] 4.A.0.1: Massive WebSocket 클라이언트 (`massive_ws_client.py`)
- [x] 4.A.0.2: TickBroadcaster → GUI WebSocket 브릿지
- [x] 4.A.0.3: Chart 실시간 업데이트 (`update_realtime_bar()`)
- [x] 4.A.0.4: SubscriptionManager 구독 동기화

#### Phase 4.A.0.b: Tick Dispatcher Integration ✅ COMPLETED
- [x] 4.A.0.b.1: TickDispatcher 생성
- [x] 4.A.0.b.2: Strategy (Seismograph) on_tick 연결
- [x] 4.A.0.b.3: TradingEngine 연결 ⏭️ SKIP (Phase 5에서 구현)
- [x] 4.A.0.b.4: TrailingStop on_price_update 연결
- [x] 4.A.0.b.5: Tier 2 GUI tick_received 연결
- [x] 4.A.0.b.6: T 채널 자동 구독 (sync_tick_subscriptions)

#### Phase 4.A.0.c: Pipeline 버그 수정 ✅ COMPLETED
- [x] P0: listen() 루프 추가
- [x] P1: 초기 구독 트리거
- [x] P2: 문자열/필드 수정
```

---

### 1.2 [HIGH] Step 4.2.6 누락

**Devlog 내용** (`step_4.2_report.md` Line 17-18):
> 4.2.5 Right Panel Oracle | ✅ 완료

**현재 development_steps.md** (Line 154-156):
```markdown
- [x] 4.2.5: **Right Panel Oracle Section**: Trading + Oracle sections
- [x] 4.2.6: **Local Server Launch**: Add "Start/Shutdown Local Server" buttons
```

**상태**: 4.2.6이 이미 있지만, devlog에는 명시적 리포트가 없음. **확인 필요**.

---

### 1.3 [MEDIUM] 데이터 소스 변경 미반영

**Devlog 내용** (`step_2.7_report.md` Line 19-20):
> **base_url** 변경: `api.polygon.io` → `api.massive.com`

**Devlog 내용** (`step_4.a.0_report.md` Line 10-13):
> Massive.com (구 Polygon.io)은 REST API뿐만 아니라 **WebSocket 스트리밍**을 지원
> IBKR의 틱 구독 기능을 Massive WebSocket으로 완전 대체함.

**권장 수정**: Phase 4.A.0 설명에 아래 내용 추가
```markdown
> 📌 **데이터 소스 전환**: IBKR 실시간 시세 → Massive.com WebSocket (AM/T 채널)
> IBKR는 **주문 실행 전용**으로 역할 축소
```

---

### 1.4 [LOW] gui_* 리포트 미반영

| Devlog | 주요 변경 | 반영 여부 |
|--------|----------|----------|
| `gui_1.1_report.md` | 초기 GUI 구현 | ✅ Step 1.3에 포함 |
| `gui_1.2_report.md` | 추가 GUI 개선 | ❓ 명시적 미반영 |
| `gui_1.3_report.md` | 차트 구현 | ✅ Step 2.4 |
| `gui_1.4_report.md` | 주말 갭 제거 | ❓ Step 2.7.4/5에 추가 필요? |
| `gui_1.5_report.md` | 아이콘/Taskbar 수정 | ❓ 별도 항목 없음 |

**권장**: GUI 관련 리포트는 해당 Step에 이미 포함되어 있거나 부수적 개선이므로 **별도 업데이트 불필요**.

---

## 2. masterplan.md 업데이트 필요 사항

### 2.1 [HIGH] Section 3.1 데이터 소스 설명 업데이트

**현재 상태** (Line 76-77):
```markdown
| **Massive.com** | **Universe Scan + History + Real-time** | `Grouped Daily` → Local DB, **WebSocket** |
| **IBKR** | **주문 실행 전용** | `place_order`, `get_positions` 등 |
```

**상태**: 이미 올바르게 반영되어 있음 ✅

---

### 2.2 [HIGH] TradingEngine 스킵 명시

**Devlog 내용** (`step_4.a.0.b.3_report.md`):
> TradingEngine 클래스가 아직 구현되지 않음.
> Phase 5 (실거래 통합) 단계에서 구현 예정.

**현재 masterplan.md**: Section 6.1 Class Diagram에 `OmniController` 언급 (미구현)

**권장 수정**: Section 6 Architecture에 다음 추가
```markdown
> ⚠️ **v2.0 구현 범위**: `TradingEngine` 및 `OmniController`는 Phase 5에서 구현 예정.  
> 현재는 Strategy Signal → OrderManager 직접 연결 구조.
```

---

### 2.3 [MEDIUM] Section 3.2 번호 중복 (이전 분석에서 발견)

**현재 상태**:
- Line 131: `### 3.2 Universe Filter Logic`
- Line 141: `### 3.2 Accumulation Stage Detection`

**권장**: 3.2 → 3.2 / 3.3으로 재번호화

---

### 2.4 [MEDIUM] 실시간 파이프라인 다이어그램 업데이트

**현재 다이어그램** (Lines 93-120)에 `TickDispatcher`가 누락됨.

**Devlog 내용** (`step_4.a.0.b.1_report.md`):
```
Massive T (틱) → TickBroadcaster._on_tick()
                      │
                      ▼
               TickDispatcher.dispatch()
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
Strategy        TradingEngine     TrailingStop
```

**권장**: Section 3.1.1 다이어그램에 `TickDispatcher` 추가

---

### 2.5 [LOW] 프로젝트 구조 업데이트

**Devlog에서 발견된 신규 파일**:
- `backend/core/tick_dispatcher.py` (4.A.0.b.1)
- `backend/core/ignition_monitor.py` (마스터플랜에 언급되나 위치 미명시)

**현재 masterplan.md** Section 12.1에 `tick_dispatcher.py` 누락

---

## 3. 조치 우선순위

| 순위 | 문서 | 항목 | 조치 |
|------|------|------|------|
| 🔴 1 | `development_steps.md` | Phase 4.A.0 체크리스트 | 완료 표시 + 서브스텝 추가 |
| 🔴 2 | `masterplan.md` | TradingEngine 스킵 명시 | 경고 노트 추가 |
| 🟠 3 | `masterplan.md` | Section 3.2 번호 중복 | 재번호화 |
| 🟠 4 | `masterplan.md` | 파이프라인 다이어그램 | TickDispatcher 추가 |
| 🟡 5 | `development_steps.md` | 데이터 소스 전환 설명 | 주석 추가 |
| 🟢 6 | `masterplan.md` | 프로젝트 구조 | 신규 파일 추가 |

---

## 📎 참고 자료

- [masterplan.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/masterplan.md)
- [development_steps.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/steps/development_steps.md)
- [step_4.a.0_report.md](file:///d:/Codes/Sigma9-0.1/docs/devlog/step_4.a.0_report.md)
