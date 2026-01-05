# 01-002: Score 계산 고도화

**작성일**: 2026-01-06  
**우선순위**: 🟢 Low (01-001 해결 후)  
**상태**: ✅ 구현 완료


---

## 개요

현재 Watchlist Score는 **step 함수** (100, 80, 70, 50, 30, 10)로 계산됨.
이를 **연속적인 가중합 기반 수식**으로 고도화하여 더 dynamic한 점수 산출 필요.

---

## 현재 로직

**파일**: `backend/strategies/seismograph.py` - `calculate_watchlist_score()`

```python
def calculate_watchlist_score(self, ticker: str, bars: list) -> tuple:
    has_tight_range = self._detect_tight_range(bars)
    has_obv_divergence = self._detect_obv_divergence(bars)
    has_accumulation_bar = self._detect_accumulation_bar(bars)
    has_volume_dryout = self._detect_volume_dryout(bars)
    
    # Step 함수 방식 (이산적)
    if has_tight_range and has_obv_divergence:
        return 100.0, "Stage 4+ (VCP)"
    elif has_tight_range:
        return 80.0, "Stage 4 (Tight Range)"
    elif has_accumulation_bar and has_obv_divergence:
        return 70.0, "Stage 3+ (Accumulation)"
    elif has_accumulation_bar:
        return 50.0, "Stage 3 (Accumulation Bar)"
    elif has_obv_divergence:
        return 30.0, "Stage 2 (OBV Divergence)"
    elif has_volume_dryout:
        return 10.0, "Stage 1 (Volume Dry-out)"
    else:
        return 0.0, "No Signal"
```

### 문제점

1. **이산적 점수**: 79점과 80점 사이의 구분이 없음
2. **신호 강도 무시**: 모든 Tight Range가 동일한 80점
3. **시간 정보 미반영**: 최근 신호와 오래된 신호가 동일 가중치
4. **조합 단순화**: 복합 신호의 시너지 미반영

---

## 제안: 가중합 기반 연속 점수

### 1. 개별 신호 정규화 (0~1)

각 신호를 Boolean이 아닌 **강도(intensity)**로 계산:

```python
def _calculate_signal_intensity(self, bars: list) -> dict:
    """개별 신호 강도 계산 (0.0 ~ 1.0)"""
    
    # 1. Tight Range 강도
    #    ATR_5 / ATR_20 비율이 낮을수록 강함
    atr_ratio = self._calc_atr_ratio(bars, 5, 20)
    tight_range_intensity = max(0, 1 - (atr_ratio / 0.5))  # 50% 이하면 1.0
    
    # 2. OBV Divergence 강도
    #    가격 기울기 vs OBV 기울기 차이
    price_slope = self._calc_slope(bars, 'close', 10)
    obv_slope = self._calc_slope(bars, 'obv', 10)
    divergence_intensity = max(0, min(1, (obv_slope - price_slope) / 0.02))
    
    # 3. Accumulation Bar 강도
    #    Volume Spike 배수 (3x → 0.5, 5x → 1.0)
    volume_ratio = self._calc_volume_ratio(bars)
    accum_bar_intensity = min(1, (volume_ratio - 2) / 3)  # 2~5배 → 0~1
    
    # 4. Volume Dry-out 강도
    #    최근 3일 vs 20일 평균 비율
    dryout_ratio = self._calc_dryout_ratio(bars)
    dryout_intensity = max(0, 1 - (dryout_ratio / 0.4))  # 40% 이하면 1.0
    
    return {
        "tight_range": tight_range_intensity,
        "obv_divergence": divergence_intensity,
        "accumulation_bar": accum_bar_intensity,
        "volume_dryout": dryout_intensity,
    }
```

### 2. 가중합 점수 계산

```python
def calculate_accumulation_score(self, bars: list) -> float:
    """Accumulation Score 계산 (0~100)"""
    
    intensities = self._calculate_signal_intensity(bars)
    
    # 가중치 (Masterplan 기준)
    WEIGHTS = {
        "tight_range": 0.30,      # VCP 패턴 (30%)
        "obv_divergence": 0.35,   # 스마트 머니 (35%)
        "accumulation_bar": 0.25, # 매집 완료 (25%)
        "volume_dryout": 0.10,    # 준비 단계 (10%)
    }
    
    # 가중합
    raw_score = sum(
        intensities[signal] * weight 
        for signal, weight in WEIGHTS.items()
    )
    
    return raw_score * 100  # 0~100 스케일
```

### 3. 시간 decay 적용 (Optional)

최근 신호일수록 높은 가중치:

```python
def _apply_time_decay(self, intensity: float, days_ago: int) -> float:
    """시간 decay 적용 (반감기 5일)"""
    HALF_LIFE = 5
    decay_factor = 0.5 ** (days_ago / HALF_LIFE)
    return intensity * decay_factor
```

---

## 기대 효과

| 현재 | 개선 후 |
|------|---------|
| 80점 or 0점 | 0~100 연속 분포 |
| 강도 무시 | 신호 강도 반영 |
| 시간 무시 | 최근 신호 우선 |
| 단순 조합 | 가중합 시너지 |

---

## 구현 계획

### Phase 1: 신호 강도 함수

| 작업 | 파일 | 예상 LOC |
|------|------|----------|
| `_calculate_signal_intensity()` 추가 | `seismograph.py` | ~40 |
| `_calc_atr_ratio()` 헬퍼 | `seismograph.py` | ~10 |
| `_calc_slope()` 헬퍼 | `seismograph.py` | ~10 |

### Phase 2: 가중합 점수

| 작업 | 파일 | 예상 LOC |
|------|------|----------|
| `calculate_accumulation_score_v2()` | `seismograph.py` | ~20 |
| 기존 함수와 병행 테스트 | - | - |

### Phase 3: 통합 및 마이그레이션

| 작업 | 파일 |
|------|------|
| `calculate_watchlist_score()` 교체 | `seismograph.py` |
| GUI Score 컬럼 포맷 조정 | `dashboard.py` |

---

## 수식 요약

$$
Score = 100 \times \sum_{i} w_i \cdot I_i(bars) \cdot D_i(t)
$$

| 기호 | 의미 |
|------|------|
| $w_i$ | 신호 가중치 (tight_range=0.30, obv=0.35, ...) |
| $I_i$ | 신호 강도 (0.0 ~ 1.0) |
| $D_i$ | 시간 decay (0.5^{days/5}) |

---

## 관련 파일

- **수정 대상**: `backend/strategies/seismograph.py`
- **참고**: `docs/strategy/seismograph_strategy_guide.md`
- **의존**: 01-001 (Realtime Scanner 통합) 완료 후 진행

---

## Phase 3: 설정 기반 v1/v2 전환 (추가)

> **결정**: v2를 기본값으로 설정하고, settings.yaml에서 v1/v2 전환 가능하게 구현

### 3.1 설정 파일 수정

**파일**: `frontend/config/settings.yaml`

```yaml
# Score 계산 버전
score_version: "v2"  # "v1" (step) 또는 "v2" (weighted)
```

### 3.2 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `frontend/config/settings.yaml` | `score_version: "v2"` 기본값 추가 |
| `frontend/gui/watchlist_model.py` | v2 score 표시 로직 추가 |
| `backend/core/scanner.py` | `score_v2` 필드 전송 확인 |

### 3.3 구현 상세

#### watchlist_model.py 수정

```python
def _set_row_data(self, row: int, data: dict):
    # Score (설정에 따라 v1 또는 v2 사용)
    from ..config.loader import load_settings
    settings = load_settings()
    use_v2 = settings.get("score_version", "v2") == "v2"
    
    score = data.get("score_v2", 0) if use_v2 else data.get("score", 0)
    # ... 기존 로직
```

### 3.4 데이터 흐름

```
[Scanner] → calculate_watchlist_score_detailed()
           → {score: 80, score_v2: 67.5}
           → WebSocket broadcast

[Frontend] → settings.yaml: score_version = "v2"
           → watchlist_model.update_item()
           → score_v2 값(67.5) 표시
```

---

## Phase 4: Day Gainer 실시간 v2 Score 계산 (추가)

> **목표**: Realtime Gainer도 DB의 일봉 데이터를 활용하여 진짜 v2 점수 계산

### 4.1 현재 문제

| 데이터 소스 | 현재 score | 원인 |
|-------------|-----------|------|
| Daily Scan | ✅ 연속 v2 | `scanner.py`가 일봉 데이터로 계산 |
| Realtime Gainer | ❌ 고정값 50 | 일봉 데이터 접근 없음 |

### 4.2 해결 방안

**DB 활용 가능**: `MarketDB.get_daily_bars(ticker, days=20)`로 5년치 일봉 데이터 조회 가능

```python
# RealtimeScanner에 MarketDB 주입
class RealtimeScanner:
    def __init__(self, polygon_client, ws_manager, db: MarketDB, ...):
        self.db = db
        self.strategy = SeismographStrategy()
```

### 4.3 구현 계획

#### 4.3.1 RealtimeScanner 수정

**파일**: `backend/core/realtime_scanner.py`

```python
async def _handle_new_gainer(self, item: Dict[str, Any]):
    ticker = item["ticker"]
    
    # [Phase 4] DB에서 일봉 데이터 조회 → v2 점수 계산
    if self.db:
        try:
            bars = await self.db.get_daily_bars(ticker, days=20)
            if bars and len(bars) >= 5:
                data = [bar.to_dict() for bar in reversed(bars)]
                result = self.strategy.calculate_watchlist_score_detailed(ticker, data)
                score = result["score"]
                score_v2 = result["score_v2"]
                stage = result["stage"]
                stage_number = result["stage_number"]
                signals = result["signals"]
                can_trade = result["can_trade"]
            else:
                # DB에 일봉 없으면 기본값
                score, score_v2, stage, stage_number = 50.0, 50.0, "Gainer", 3
                signals, can_trade = {}, True
        except Exception as e:
            logger.warning(f"⚠️ {ticker} v2 score 계산 실패: {e}")
            score, score_v2 = 50.0, 50.0
```

#### 4.3.2 초기화 수정

**파일**: `backend/core/realtime_scanner.py`

```diff
 def __init__(
     self,
     polygon_client: Any,
     ws_manager: Any,
+    db: Optional[Any] = None,
     ignition_monitor: Optional[Any] = None,
     poll_interval: float = 1.0
 ):
     self.polygon_client = polygon_client
     self.ws_manager = ws_manager
+    self.db = db
+    self.strategy = SeismographStrategy() if db else None
```

**파일**: `backend/core/realtime_scanner.py` - `initialize_realtime_scanner()`

```diff
 def initialize_realtime_scanner(
     polygon_client: Any,
     ws_manager: Any,
+    db: Optional[Any] = None,
     ignition_monitor: Optional[Any] = None,
     poll_interval: float = 1.0
 ) -> RealtimeScanner:
     ...
     _scanner_instance = RealtimeScanner(
         polygon_client=polygon_client,
         ws_manager=ws_manager,
+        db=db,
         ignition_monitor=ignition_monitor,
         poll_interval=poll_interval
     )
```

#### 4.3.3 백엔드 메인에서 DB 주입

**파일**: `backend/api/main.py` 또는 스캐너 초기화 위치

```python
from backend.data.database import MarketDB
from backend.core.realtime_scanner import initialize_realtime_scanner

db = MarketDB("data/market_data.db")
await db.initialize()

scanner = initialize_realtime_scanner(
    polygon_client=polygon_client,
    ws_manager=ws_manager,
    db=db,  # [Phase 4] DB 주입
)
```

### 4.4 예상 결과

| 상황 | 수정 전 | 수정 후 |
|------|--------|--------|
| SMXT +40% 급등 탐지 | score=50 (고정) | score_v2=67.5 (DB 기반) |
| DB에 일봉 없는 종목 | score=50 | score=50 (fallback) |
| 일봉 5일 이상 있는 종목 | score=50 | v2 가중합 점수 |

### 4.5 수정 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `realtime_scanner.py` | `db` 파라미터 추가, `_handle_new_gainer` 수정 |
| `backend/api/main.py` (또는 서버 초기화) | MarketDB 인스턴스 주입 |

### 4.6 검증 계획

1. 백엔드 실행 후 Realtime Gainer 탐지 시 로그 확인
2. GUI에서 Day Gainer의 Score가 소수점(v2) 형식인지 확인
3. DB에 일봉이 없는 종목은 50점 fallback 확인
