# 02-001: Score Calculation Enhancement (v2 가중합 시스템)

**작성일**: 2026-01-06  
**상태**: ✅ 구현 완료

---

## 개요

기존 step 함수 기반 점수 시스템(10, 30, 50, 70, 80, 100)을 보완하여  
**연속적인 0~100 점수**를 반환하는 v2 가중합 시스템을 추가했습니다.

---

## 변경 내용

### 수정 파일
- `backend/strategies/seismograph.py`

### 추가된 메서드

| 메서드 | 설명 | LOC |
|--------|------|-----|
| `calculate_watchlist_score_v2()` | v2 연속 점수 계산 (가중합) | ~25 |
| `_calculate_signal_intensities()` | 4개 신호 강도 계산 래퍼 | ~15 |
| `_calc_tight_range_intensity()` | ATR 비율 기반 강도 (0~1) | ~30 |
| `_calc_obv_divergence_intensity()` | 가격/OBV 기울기 차이 기반 | ~40 |
| `_calc_accumulation_bar_intensity()` | 거래량 배수 기반 강도 | ~30 |
| `_calc_volume_dryout_intensity()` | 거래량 감소 비율 기반 | ~25 |

### 수정된 메서드

| 메서드 | 변경 내용 |
|--------|----------|
| `calculate_watchlist_score_detailed()` | `score_v2` 및 `intensities` 필드 추가 |

---

## 점수 계산 수식

$$
Score_{v2} = 100 \times \sum_{i} w_i \cdot I_i
$$

| 신호 | 가중치 ($w_i$) | 강도 범위 ($I_i$) |
|------|----------------|-------------------|
| Tight Range | 0.30 | ATR_5/ATR_20 비율 기반 |
| OBV Divergence | 0.35 | 가격↓ + OBV↑ 차이 |
| Accumulation Bar | 0.25 | 거래량 배수 (2x~5x) |
| Volume Dry-out | 0.10 | 최근/평균 거래량 비율 |

---

## 강도 계산 예시

### Tight Range Intensity
```
ATR_5 / ATR_20 = 0.25 → intensity = (0.7 - 0.25) / 0.4 = 1.0
ATR_5 / ATR_20 = 0.50 → intensity = (0.7 - 0.50) / 0.4 = 0.5
ATR_5 / ATR_20 = 0.70 → intensity = 0.0
```

### Accumulation Bar Intensity
```
Volume = 2x 평균 → intensity = 0.0
Volume = 3x 평균 → intensity = 0.33
Volume = 5x 평균 → intensity = 1.0
```

---

## 호환성

- **v1 (step 함수)**: `calculate_watchlist_score()` - 기존 로직 유지
- **v2 (가중합)**: `calculate_watchlist_score_v2()` - 신규 추가
- `calculate_watchlist_score_detailed()`: 둘 다 반환 (`score`, `score_v2`, `intensities`)

---

## 검증

### 단위 테스트 (수동)
```python
from backend.strategies.seismograph import SeismographStrategy
import pandas as pd

strategy = SeismographStrategy()

# 샘플 데이터로 테스트
data = pd.DataFrame({
    'open': [10] * 20,
    'high': [11] * 20,
    'low': [9] * 20,
    'close': [10.5] * 20,
    'volume': [100000] * 20,
})

result = strategy.calculate_watchlist_score_detailed("TEST", data)
print(f"v1 score: {result['score']}")
print(f"v2 score: {result['score_v2']}")
print(f"intensities: {result['intensities']}")
```

---

## 관련 문서

- **계획서**: `docs/Plan/bugfix/02-001_score_calculation_enhancement.md`
- **참고**: `docs/strategy/seismograph_strategy_guide.md`

---

## Phase 3: 설정 기반 v1/v2 전환 (추가 구현)

### 변경 파일
| 파일 | 변경 내용 |
|------|----------|
| `frontend/config/settings.yaml` | `score_version: "v2"` 기본값 추가 |
| `frontend/gui/watchlist_model.py` | v1/v2 동적 선택 로직 추가 |
| `backend/core/scanner.py` | `score_v2` 필드 추가 |
| `backend/core/realtime_scanner.py` | Day Gainer에 `score_v2` 필드 추가 |

### 설정 방법
```yaml
# settings.yaml
score_version: "v2"  # "v1" (step) 또는 "v2" (가중합)
```

### 표시 형식
- **v2**: 소수점 1자리 (예: `67.5`)
- **v1**: 정수 (예: `80`)

---

## Phase 3 버그 수정 (추가)

### 문제 1: Score 표시 안됨 (⚠️)
**원인**: 저장된 watchlist에 `score_v2` 필드가 없어서 0 반환

**수정**: `watchlist_model.py`에 fallback 로직 추가
```python
if use_v2:
    score = data.get("score_v2") or data.get("score", 0) or 0
else:
    score = data.get("score", 0) or 0
```

### 문제 2: 여전히 step 점수만 표시
**원인**: `realtime_scanner.py` 브로드캐스트 시 `score_v2` 미포함

**수정**: hydration 과정에서 `score_v2` 자동 채움 추가
```python
# realtime_scanner.py - _periodic_watchlist_broadcast
if "score_v2" not in item and "score" in item:
    item["score_v2"] = item["score"]
```

### 데이터 흐름 요약

| 소스 | score_v2 계산 |
|------|---------------|
| Daily Scan (`scanner.py`) | ✅ 가중합 연속 점수 |
| Realtime Gainer | 고정값 50 (일봉 없음) |
| 저장된 기존 데이터 | score fallback |

### 추가 변경 파일
| 파일 | 변경 내용 |
|------|----------|
| `watchlist_model.py` | score_v2 fallback 로직 |
| `realtime_scanner.py` | score_v2 hydration 추가 |

---

## 한계 및 향후 개선

1. **Realtime Gainer**: 일봉 데이터 없이 v2 점수 계산 불가 → 고정값 사용
2. **기존 데이터**: 새 스캔 전까지 v1 점수로 fallback
3. **향후**: ignition 계산처럼 실시간 v2 점수 재계산 고려 가능

