# Step 4.A.4: zenV-zenP Divergence 전략 (Seismograph 확장)

> **목표**: Seismograph 전략의 매집 탐지 기능 강화
> **철학**: 거래량은 폭발하는데 가격은 조용하면 → 누군가 조용히 모으는 중

---

## 1. 개요

### 1.1 현재 Seismograph 구조

```
Universe Filter → Accumulation Score → Watchlist → Ignition Detection → Signal
```

### 1.2 4.A.4에서 추가할 것

기존 Ignition Detection **앞에** Divergence 탐지 단계 추가:

```
Watchlist → [NEW] Divergence Detection → Tier 2 승격 → Ignition → Signal
```

**Divergence = zenV 높음 + zenP 낮음** (고거래량 + 저변동 = 매집 가능성)

---

## 2. Z-Score 계산

### 2.1 기준 데이터
- **20일 일봉 기반** (기존 `ZScoreCalculator` 유지)
- 장중 실시간 업데이트를 위해 **Time-Projection** 적용

### 2.2 Time-Projected zenV

```python
def calculate_projected_zenV(
    current_volume: int,      # 오늘 현재까지 거래량
    avg_daily: float,         # 20일 평균 일거래량
    std_daily: float,         # 20일 거래량 표준편차
    elapsed_ratio: float      # 장 경과 비율 (0.0 ~ 1.0)
) -> float:
    """
    장중 실시간 zenV 계산.
    
    예: 오전 10시 (경과 8%), 거래량 200만주
        평균 일거래량 1000만주
        → expected = 1000만 × 0.08 = 80만
        → zenV = (200만 - 80만) / (std × √0.08)
        → 거래량이 기대치의 2.5배 → 강한 양의 신호
    """
    expected = avg_daily * elapsed_ratio
    adjusted_std = std_daily * sqrt(elapsed_ratio) if elapsed_ratio > 0 else 0
    
    if adjusted_std <= 0:
        return 0.0
    
    return (current_volume - expected) / adjusted_std
```

### 2.3 zenP (가격 변동)

```python
# 기존 로직 유지: 당일 가격 변동률의 Z-Score
zenP = (today_change_pct - avg_change) / std_change
```

---

## 3. Divergence 탐지 조건

### 3.1 Scout 신호 (매집 가능성)

```python
# 강한 Divergence
if zenV >= 2.0 and zenP < 0.5:
    signal = "🔥 DIVERGENCE"  # Scout 단계
```

### 3.2 해석표

| zenV | zenP | 해석 |
|------|------|------|
| **≥ 2.0** | **< 0.5** | 🔥 매집 가능성 (Divergence) |
| ≥ 2.0 | ≥ 1.5 | 📈 모멘텀 상승 |
| < 0 | > 2.0 | ⚠️ 급등 후 거래량 감소 |
| < 0 | < 0 | 💤 관심 없음 |

---

## 4. 구현 항목

### 4.1 Backend

| 파일 | 변경 |
|------|------|
| `backend/core/zscore_calculator.py` | `calculate_projected_zenV()` 메서드 추가 |
| `backend/core/divergence_detector.py` | **신규** - Divergence 탐지 로직 |
| `backend/api/routes.py` | `/api/divergence/{ticker}` 엔드포인트 |

### 4.2 Frontend

| 파일 | 변경 |
|------|------|
| `frontend/gui/dashboard.py` | Tier 2 테이블에 Signal 컬럼 추가 (🔥/🎯) |

### 4.3 Tier 2 Demote 로직 (추가)

- Ignition < 50 지속 5분 → Tier 2에서 강등
- 장 마감 시 전체 정리

---

## 5. 개발 순서

| # | 태스크 |
|---|--------|
| 1 | `ZScoreCalculator`에 `calculate_projected_zenV()` 추가 |
| 2 | `DivergenceDetector` 모듈 생성 |
| 3 | Tier 2 Demote 로직 추가 |
| 4 | GUI Signal 컬럼 추가 |
| 5 | 테스트 |

---

## 6. 검증

```bash
# 문법 검증
python -m py_compile backend/core/zscore_calculator.py
python -m py_compile backend/core/divergence_detector.py

# 수동 테스트
# 1. GUI 실행 후 Tier 2에 종목 승격되는지 확인
# 2. 고거래량+저변동 종목에 🔥 표시되는지 확인
```
