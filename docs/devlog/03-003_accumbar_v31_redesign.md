# 03-003 AccumBar V3.1 Redesign Devlog

> **작성일**: 2026-01-06  
> **상태**: ✅ 구현 완료 (GUI 검증 대기)  
> **참고**: `docs/Plan/bugfix/03-003_accumbar_v31_redesign.md`

---

## 변경 이력

### Phase 1: 설정 추가
- [x] `AccumBarConfig` 클래스 추가
- [x] `ACCUMBAR_CONFIG` 상수 정의

### Phase 2: 알고리즘 재작성
- [x] 기존 V3 함수 백업
- [x] V3.1 알고리즘 구현

### Phase 3: 테스트
- [x] 구문 검사 통과
- [ ] GUI 점수 분포 확인

### Phase 4: 문서화
- [x] 최종 결과 기록

---

## 📝 진행 로그

### 2026-01-06 10:00

**분석 완료**:
- 현재 `_calc_accumulation_bar_intensity_v3()` (Lines 895-953) 확인
- 문제: 양봉 + 1.5x 거래량 조건 동시 충족 필요 → 대부분 0.00 반환
- 해결: Base 0.5 + 가감점 구조 도입 예정

### 2026-01-06 10:03

**Phase 1 완료**:
- `score_v3_config.py`에 `AccumBarConfig` 클래스 추가 (Lines 120-155)
- 파라미터: base_score=0.5, adj_bullish=0.15, adj_quiet=0.15, adj_body=0.10, adj_volume=0.10

**Phase 2 완료**:
- `seismograph.py`의 `_calc_accumulation_bar_intensity_v3()` 함수 재작성
- V3.1 알고리즘: Float 기반 동적 기간, 양봉 비율, 조용한 날, Body Ratio Median, 거래량 Median

**Phase 3 구문 검사**:
- `python -m py_compile` 통과 ✅

---

## 🔧 수정 파일

| 파일 | 변경 유형 | 상태 |
|------|----------|------|
| `backend/strategies/score_v3_config.py` | 신규 클래스 추가 | ✅ |
| `backend/strategies/seismograph.py` | 함수 재작성 | ✅ |

---

## ✅ 검증 결과

**구문 검사**: ✅ 통과

**GUI 검증**: GUI를 재시작하여 AccumBar 값이 0.00이 아닌 다양한 값(0.3~0.7)으로 분포되는지 확인 필요

---

## 🐛 버그 수정 (발견 후 즉시 해결)

### [03-003a] Score V3 Intensity Mismatch (2026-01-06 10:15)

**문제**: score_v3 점수와 툴팁에 표시되는 intensities가 불일치
- YMAT: intensities 66,88,40,58 → 총점 67.3 ✅
- CCRC: intensities 56,00,24,00 → **예상 21.6, 실제 66.1** ❌

**원인**: `realtime_scanner.py` Line 310에서 `intensities` (V2)를 사용하여 툴팁 표시, 하지만 `score_v3`는 `intensities_v3`로 계산됨

**수정**: 
```diff
- intensities = result.get("intensities", {})  # V2
+ intensities = result.get("intensities_v3", {})  # V3
```

**영향 파일**: `backend/core/realtime_scanner.py` Line 310

### [03-003b] Scanner V3 Intensities (2026-01-06 10:22)

**문제**: `scanner.py` (초기 스캔)에서도 V2 intensities 사용

**수정**:
```diff
- "intensities": result.get("intensities", {}),  # V2
+ "intensities": result.get("intensities_v3", {}),  # V3
+ "score_v3": result.get("score_v3"),  # 추가
```

**영향 파일**: `backend/core/scanner.py` Line 151

### [03-003c] Signal Intensity Penalty System (2026-01-06 10:27)

**기능**: 4개 신호 중 하나라도 0.1 미만이면 0.7x 페널티 적용 (Boost의 반대 개념)

**추가 파일**:
- `score_v3_config.py`: `SignalPenaltyConfig` (min_intensity=0.1, multiplier=0.7)
- `seismograph.py`: `_calculate_signal_penalty_factor()` 함수 추가
- `calculate_watchlist_score_v3()`: `signal_penalty` 적용

**점수 계산 공식**:
```
Final = Base × Boost × Penalty × SignalPenalty
```

### [03-003d] Dynamic Signal Modifier 통합 (2026-01-06 10:42)

**변경**: Boost (1.3x) + SignalPenalty (0.7x) → **단일 SignalModifier (0.85~1.15)**

**설계 원칙**: 단순 평균 기반, Overfitting 방지
```python
avg = mean(intensities)
modifier = 0.85 + (avg * 0.30)  # 0.85 ~ 1.15
```

**삭제된 코드**:
- `BoostConfig`, `SignalPenaltyConfig` 클래스
- `_calculate_boost_factor()`, `_calculate_signal_penalty_factor()`, `_calculate_penalty_factor()` 함수

**추가된 코드**:
- `SignalModifierConfig` (min_modifier=0.85, max_modifier=1.15)
- `_calculate_signal_modifier()` 함수

**새 점수 계산 공식**:
```
Final = Base × SignalModifier
```
