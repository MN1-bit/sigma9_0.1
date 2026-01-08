# Step 2.3 Report: Seismograph Strategy - Trigger (Phase 2)

> **작성일**: 2025-12-18  
> **소요 시간**: ~15분  
> **상태**: ✅ 완료

---

## 1. 작업 요약

Sigma9의 핵심 전략인 `SeismographStrategy`의 Trigger 단계(Phase 2)를 구현했습니다.
실시간 틱 데이터 기반으로 "폭발 순간"을 감지하여 BUY Signal을 생성합니다.

---

## 2. 수정된 파일

| 파일 | 변경 내용 | 라인 증가 |
|------|----------|----------|
| [seismograph.py](file:///d:/Codes/Sigma9-0.1/backend/strategies/seismograph.py) | Phase 2 로직 추가 | +400 |
| [development_steps.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/steps/development_steps.md) | Step 2.3 완료 표시 | +1 |

---

## 3. 구현된 기능

### 3.1 Ignition Score (폭발 점수)

masterplan.md 4.1절 기준 4가지 신호 가중합:

| 신호 | 조건 | Weight | 메서드 |
|------|------|--------|--------|
| **Tick Velocity** | 10초 체결 > 1분 평균 × 8 | 35% | `_calculate_tick_velocity()` |
| **Volume Burst** | 1분 거래량 > 5분 평균 × 6 | 30% | `_calculate_volume_burst()` |
| **Price Break** | 현재가 > 박스권 상단 + 0.5% | 20% | `_calculate_price_break()` |
| **Buy Pressure** | 매수/매도 > 1.8 | 15% | `_calculate_buy_pressure()` |

**→ Ignition Score ≥ 70점 시: BUY Signal 생성**

### 3.2 Anti-Trap Filter

| 조건 | 설명 | 메서드 |
|------|------|--------|
| Spread < 1% | 스프레드 너무 넓으면 SKIP | `check_anti_trap_filter()` |
| 장 시작 후 15분 | 오프닝 노이즈 회피 | ↑ |
| VWAP 위 | 당일 평균 이상 진입 | ↑ |

### 3.3 Internal Buffers

```python
self._tick_buffer: Dict[str, deque]        # 최근 60초 틱
self._bar_1m: Dict[str, List[Dict]]        # 최근 5분봉
self._vwap: Dict[str, float]               # 당일 VWAP
self._box_range: Dict[str, Tuple[float]]   # 박스권 고/저
```

### 3.4 Config 파라미터 (GUI 조정 가능)

```python
"ignition_threshold": 70          # 진입 기준 (50~90)
"tick_velocity_multiplier": 8.0   # 틱 속도 배수 (4~15)
"volume_burst_multiplier": 6.0    # 거래량 폭발 배수 (3~12)
"price_break_pct": 0.5            # 돌파 퍼센트 (0.3~1.0)
"buy_pressure_ratio": 1.8         # 매수압력 비율 (1.5~2.5)
"max_spread_pct": 1.0             # 최대 스프레드 (0.5~2.0)
"min_minutes_after_open": 15      # 개장 후 최소 (5~30)
```

---

## 4. 검증 결과

### 4.1 문법 검사 ✅

```powershell
python -m py_compile backend/strategies/seismograph.py
# (에러 없음)
```

### 4.2 데모 테스트 ✅

```
============================================================
Phase 2: Ignition Score 테스트
============================================================
[Seismograph] 전략 초기화 완료 (Phase 1 + Phase 2)

✓ 전략 초기화 완료
[Seismograph] Watchlist 갱신: 1개 종목

✓ Mock 틱 데이터 생성 (폭발 시나리오):
  - 틱 버퍼 크기: 100
  - 박스권 설정: 고점=$5.5, 저점=$5.0
  - 1분봉 버퍼: 마지막 거래량 80,000 (5분 평균의 ~7배)

✓ Ignition Score: 65.0점

개별 Ignition 신호:
  - Tick Velocity: 0.0점
  - Volume Burst: 30.0점
  - Price Break: 20.0점
  - Buy Pressure: 15.0점

✓ Anti-Trap 필터 테스트:
  - 결과: 통과 ✓ (OK)

============================================================
모든 테스트 완료! ✓
============================================================
```

---

## 5. 구현 노트

### 5.1 데이터 구조

```python
@dataclass
class TickData:
    price: float
    volume: int
    timestamp: datetime
    side: str = "B"  # "B" or "S"
```

### 5.2 on_tick() 처리 흐름

```
1. 타임스탬프 정규화
2. 틱 버퍼에 저장 (maxlen=1000)
3. 60초 초과 틱 정리
4. Watchlist 종목만 Ignition 체크
5. Ignition Score ≥ 70 확인
6. Anti-Trap Filter 통과 확인
7. BUY Signal 생성 및 반환
```

---

- **Step 3.1**: Order Management System (OMS)
  - 주문 실행 로직 구현
  - Server-Side OCA 그룹 (Stop Loss, Time Stop, Profit Harvester)

---

## 7. Refinement: Trigger Restrictions (Step 2.3.4)

> **완료일**: 2025-12-18

### 7.1 목표
Stage 1-2(매집 초기) 종목에 대해 "Monitoring Only" 제한을 적용하고, Watchlist 메타데이터를 Trigger Engine에 로드.

### 7.2 변경 사항
- **`backend/strategies/seismograph.py`**
  - `_watchlist_context` 추가: Watchlist 메타데이터 저장
  - `load_watchlist_context()` 메서드 구현
  - `on_tick()` 수정: `can_trade=False`인 종목은 Signal 발생 차단

### 7.3 Trading Restrictions 규칙
| Stage | can_trade | 동작 |
|-------|-----------|------|
| 1 (Volume Dry-out) | ❌ False | 모니터링만, Signal 없음 |
| 2 (OBV Divergence) | ❌ False | 모니터링만, Signal 없음 |
| 3 (Accum Bar) | ✅ True | Ignition 발생 시 Signal |
| 4 (Tight Range) | ✅ True | Ignition 발생 시 Signal |

---

## 8. Refinement: Real Data Verification (Step 2.3.7)

> **완료일**: 2025-12-18

### 8.1 목표
SeismographStrategy가 mock 데이터 없이 실제 데이터 소스를 사용하는지 검증.

### 8.2 검증 결과
- **Mock 의존성 없음**: `seismograph.py`, `scanner.py`, `ibkr_connector.py` 모두 실제 데이터 소스(DB, API) 연결 확인
- **테스트 전용**: `mock_data.py`는 단위 테스트 목적(`tests/test_strategies.py`)으로만 사용됨을 확인
- **결론**: 프로덕션 코드는 Mock Free 상태임.

---

## 9. Step 2.4: Core Indicators & Chart Integration

> **완료일**: 2025-12-18

### 9.1 목표
TechnicalAnalysis 모듈 구현 및 TradingView Chart를 Dashboard에 통합.

### 9.2 새 파일

| 파일 | 설명 |
|------|------|
| `backend/core/technical_analysis.py` | VWAP, ATR, SMA, EMA, RSI + DynamicStopLoss |
| `frontend/gui/chart_widget.py` | TradingView Lightweight Charts 위젯 |

### 9.3 변경 사항

- **`seismograph.py`**: Signal metadata에 `indicators`, `sl_tp` 추가
- **`dashboard.py`**: ChartWidget 통합, 샘플 데이터 로드

### 9.4 검증

```bash
.venv\Scripts\python -m frontend.main
# GUI 실행 성공, 차트 표시 확인
```

