# Step 4.A.3 Report: Z-Score Indicator 구현

> **작성일**: 2026-01-02  
> **상태**: ✅ 완료  
> **선행 조건**: Step 4.A.2 (Tier 2 Hot Zone) 완료

---

## 📋 목표

Tier 2 Hot Zone에 **zenV** (Volume Z-Score)와 **zenP** (Price Z-Score) 지표를 계산하여 표시.
매집 패턴 탐지 강화: **높은 거래량 + 낮은 가격 변동** = 잠재적 축적(Accumulation) 신호

---

## ✅ 완료된 작업

### 4.A.3.1 ZScoreCalculator 모듈 생성

**파일**: `backend/core/zscore_calculator.py` (신규)

- `ZScoreResult` dataclass 정의 (zenV, zenP 필드)
- `ZScoreCalculator.calculate()` 메서드 구현
  - 20일 lookback 기간 기준
  - zenV: 거래량 Z-Score (당일 거래량이 평균 대비 몇 표준편차인지)
  - zenP: 가격 변동 Z-Score (당일 가격 변동이 평균 대비 몇 표준편차인지)
- `calculate_batch()` 메서드로 다중 종목 일괄 계산 지원

---

### 4.A.3.2 API 엔드포인트 추가

**파일**: `backend/api/routes.py`

- `GET /api/zscore/{ticker}` 엔드포인트 추가 (라인 976-1041)
- MarketDB에서 25일 일봉 데이터 조회 (여유분 포함)
- ZScoreCalculator로 zenV/zenP 계산 후 반환

**응답 예시**:
```json
{
  "ticker": "AAPL",
  "zenV": 2.35,
  "zenP": 0.45,
  "data_available": true,
  "bars_used": 25,
  "timestamp": "2026-01-02T10:45:00Z"
}
```

---

### 4.A.3.3 Frontend Tier 2 업데이트

**파일**: `frontend/gui/dashboard.py`

**수정 1**: `_promote_to_tier2()` 메서드 (라인 1467-1492)
- Tier 2 승격 시 비동기로 Z-Score API 호출
- 결과를 `_tier2_cache`에 저장 후 GUI 자동 갱신

**수정 2**: `_set_tier2_row()` 메서드 (라인 1535-1557)
- zenV/zenP 컬럼에 색상 코딩 적용:
  - **≥ 2.0**: 🟠 Orange (비정상적으로 높음)
  - **≥ 1.0**: 🟢 Green (평균 이상)
  - **< 1.0**: ⚪ Gray (평균 이하)

---

## 📊 Z-Score 해석 표

| zenV | zenP | 해석 |
|------|------|------|
| High (>2) | Low (<1) | 🔥 **매집 가능성** - 큰 거래량, 작은 가격 변동 |
| High (>2) | High (>2) | 📈 모멘텀 상승 |
| Low (<0) | High (>2) | ⚠️ 급등 후 거래량 감소 |
| Low (<0) | Low (<0) | 💤 관심 없음 |

---

## 🧪 검증

```bash
python -m py_compile backend/core/zscore_calculator.py backend/api/routes.py frontend/gui/dashboard.py
# 문법 오류 없음 ✓
```

---

## 📁 변경된 파일

| 파일 | 변경 유형 |
|------|----------|
| `backend/core/zscore_calculator.py` | 신규 |
| `backend/api/routes.py` | 수정 |
| `frontend/gui/dashboard.py` | 수정 |
