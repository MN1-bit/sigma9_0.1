# Step 4.A.3: Z-Score Indicator 구현 계획

> **버전**: 1.0  
> **작성일**: 2026-01-02  
> **선행 조건**: Step 4.A.2 완료  
> **참조 파일**: 
> - `frontend/gui/dashboard.py` (Tier2Item dataclass, Tier 2 테이블)
> - `backend/core/technical_analysis.py` (지표 계산 모듈)

---

## 📋 목표

Tier 2 Hot Zone의 **zenV** (Normalized Volume)와 **zenP** (Normalized Price) 지표를 계산하여 GUI에 표시.  
매집 패턴 탐지 강화: **높은 거래량 + 낮은 가격 변동** = 잠재적 축적(Accumulation) 신호

---

## 📊 Z-Score 개념

### Z-Score 공식
```
Z = (X - μ) / σ
```
- **X**: 현재 값
- **μ**: 평균 (20일 기준)
- **σ**: 표준편차 (20일 기준)

### zenV (Volume Z-Score)
- **의미**: 현재 거래량이 평균 대비 얼마나 높은가?
- **계산**: `zenV = (today_volume - avg_20d_volume) / std_20d_volume`
- **해석**:
  - zenV > 2.0: 비정상적으로 높은 거래량 🔥
  - zenV > 1.0: 평균 이상 거래량
  - zenV < -1.0: 평균 이하 거래량

### zenP (Price Z-Score)
- **의미**: 현재 가격 변동이 평균 대비 얼마나 큰가?
- **계산**: `zenP = (today_change - avg_20d_change) / std_20d_change`
- **해석**:
  - zenP > 2.0: 비정상적으로 큰 가격 변동
  - zenP ≈ 0: 평균적인 변동
  - zenP < -1.0: 평균 이하 변동

### 매집 신호 조합
| zenV | zenP | 해석 |
|------|------|------|
| High (>2) | Low (<1) | 🔥 **매집 가능성** - 큰 거래량, 작은 가격 변동 |
| High (>2) | High (>2) | 📈 모멘텀 상승 |
| Low (<0) | High (>2) | ⚠️ 급등 후 거래량 감소 |
| Low (<0) | Low (<0) | 💤 관심 없음 |

---

## 🎯 구현 범위

| # | 서브스텝 | 설명 |
|---|----------|------|
| 4.A.3.1 | zenV 계산 | 20일 기준 Volume Z-Score 계산 |
| 4.A.3.2 | zenP 계산 | 20일 기준 Price Change Z-Score 계산 |
| 4.A.3.3 | GUI 표시 | Tier 2 테이블에 zenV/zenP 컬럼 업데이트 |

---

## 📝 상세 구현 계획

### 1. Backend Z-Score 계산 모듈 (4.A.3.1 + 4.A.3.2)

> 파일: `backend/core/zscore_calculator.py` (신규)

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class ZScoreResult:
    zenV: float  # Volume Z-Score
    zenP: float  # Price Z-Score
    
class ZScoreCalculator:
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
    
    def calculate(self, ticker: str, daily_bars: list[dict]) -> ZScoreResult:
        """
        20일 일봉 데이터로 Z-Score 계산
        
        Args:
            ticker: 종목 코드
            daily_bars: [{date, open, high, low, close, volume}, ...]
        
        Returns:
            ZScoreResult(zenV, zenP)
        """
        if len(daily_bars) < self.lookback:
            return ZScoreResult(0.0, 0.0)
        
        recent = daily_bars[-self.lookback:]
        
        # Volume Z-Score
        volumes = [bar['volume'] for bar in recent]
        avg_vol = np.mean(volumes[:-1])  # 어제까지 평균
        std_vol = np.std(volumes[:-1])
        today_vol = volumes[-1]
        zenV = (today_vol - avg_vol) / std_vol if std_vol > 0 else 0.0
        
        # Price Change Z-Score
        changes = []
        for i in range(1, len(recent)):
            pct = (recent[i]['close'] - recent[i-1]['close']) / recent[i-1]['close'] * 100
            changes.append(abs(pct))
        
        avg_chg = np.mean(changes[:-1])
        std_chg = np.std(changes[:-1])
        today_chg = changes[-1] if changes else 0
        zenP = (today_chg - avg_chg) / std_chg if std_chg > 0 else 0.0
        
        return ZScoreResult(round(zenV, 2), round(zenP, 2))
```

---

### 2. API 엔드포인트 추가

> 파일: `backend/api/routes.py`

```python
@router.get("/api/zscore/{ticker}")
async def get_zscore(ticker: str):
    """종목의 Z-Score 계산"""
    # DB에서 20일 일봉 조회
    bars = await get_daily_bars(ticker, days=20)
    
    calculator = ZScoreCalculator()
    result = calculator.calculate(ticker, bars)
    
    return {"ticker": ticker, "zenV": result.zenV, "zenP": result.zenP}
```

---

### 3. Frontend Tier 2 업데이트 (4.A.3.3)

> 파일: `frontend/gui/dashboard.py`

**수정 1**: `_promote_to_tier2()`에서 Z-Score API 호출

```python
def _promote_to_tier2(self, ticker: str, ignition_score: float = 0.0):
    # ... 기존 로직 ...
    
    # Z-Score 비동기 조회
    def fetch_zscore():
        resp = requests.get(f"http://{host}:{port}/api/zscore/{ticker}")
        data = resp.json()
        self._tier2_cache[ticker].zenV = data.get("zenV", 0.0)
        self._tier2_cache[ticker].zenP = data.get("zenP", 0.0)
        # GUI 업데이트
        QTimer.singleShot(0, lambda: self._update_tier2_row(ticker))
    
    threading.Thread(target=fetch_zscore, daemon=True).start()
```

**수정 2**: zenV/zenP 컬럼 색상 표시

```python
def _set_tier2_row(self, row: int, item: Tier2Item):
    # ... 기존 로직 ...
    
    # zenV (컬러 코딩)
    zenV_item = QTableWidgetItem(f"{item.zenV:.1f}")
    if item.zenV >= 2.0:
        zenV_item.setForeground(QColor("#ff9800"))  # Orange (High)
    elif item.zenV >= 1.0:
        zenV_item.setForeground(QColor("#4caf50"))  # Green
    else:
        zenV_item.setForeground(QColor("#9e9e9e"))  # Gray
    self.tier2_table.setItem(row, 3, zenV_item)
    
    # zenP도 동일한 패턴
```

---

## ✅ 완료 조건

1. [ ] zenV 계산 로직 구현 및 테스트
2. [ ] zenP 계산 로직 구현 및 테스트  
3. [ ] `/api/zscore/{ticker}` 엔드포인트 동작
4. [ ] Tier 2 테이블에 zenV/zenP 실제 값 표시
5. [ ] 색상 코딩 (High/Normal/Low 구분)
6. [ ] 문법 오류 없음 (py_compile)

---

## ⚠️ 주의사항

### 데이터 의존성
- Z-Score 계산에 **최소 20일** 일봉 데이터 필요
- DB에 데이터 없으면 zenV=0, zenP=0 반환

### 성능 고려
- Tier 2 승격 시 1회만 계산 (매 틱마다 계산 X)
- 필요시 매 1분마다 갱신 가능 (옵션)

### prev_close 필드 추가
- Tier2Item에 `prev_close` 필드 추가 시 실시간 change_pct 계산 가능
- 현재 Step에서 함께 처리 권장

---

## ⏱️ 예상 시간

| 작업 | 시간 |
|------|------|
| ZScoreCalculator 모듈 | 20분 |
| API 엔드포인트 | 10분 |
| Frontend 통합 | 20분 |
| 색상 코딩 | 10분 |
| 테스트 | 15분 |
| **총계** | **75분** |
