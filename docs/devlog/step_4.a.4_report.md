# Step 4.A.4 Report: zenV-zenP Divergence 전략 구현

> **작성일**: 2026-01-03
> **상태**: ✅ 완료

---

## 📋 목표

Seismograph 전략에 **Divergence 탐지** 기능 추가:
- 고거래량 + 저변동 = 매집 가능성 → Tier 2 우선 모니터링

---

## ✅ 완료된 작업

### 4.A.4.1: ZScoreCalculator Time-Projection

**파일**: `backend/core/zscore_calculator.py`

- `DailyStats` dataclass 추가 (캐시용)
- `build_cache()`: 장 시작 전 일별 통계 캐시 빌드
- `calculate_projected_zenV()`: 장중 시간 보정 zenV 계산
- `calculate_projected_zenP()`: 장중 zenP 계산
- `get_cached_stats()`: 캐시된 통계 조회

### 4.A.4.2: DivergenceDetector 모듈

**파일**: `backend/core/divergence_detector.py` (신규)

- `DivergenceSignal` dataclass
- `DivergenceDetector` 클래스
  - 조건: `zenV >= 2.0 AND zenP < 0.5`
  - 활성 신호 캐시 관리

### 4.A.4.3: Tier2Item 모델 확장

**파일**: `frontend/gui/dashboard.py`

- `Tier2Item`에 `signal: str` 필드 추가
- "🔥" (Divergence) 또는 "🎯" (Ignition>=70)

### 4.A.4.4: Tier 2 GUI Signal 컬럼

- 테이블 7번째 컬럼 "Sig" 추가
- Z-Score 조회 후 Divergence 탐지 로직 통합
- 색상 코딩: 🔥=#ff5722, 🎯=#e91e63

### 4.A.4.5: Tier 2 Demote 로직

- `_demote_from_tier2()` 메서드 추가
- Ignition < 50 시 강등 가능 (향후 타이머 연동)

---

## 📁 변경된 파일

| 파일 | 변경 유형 |
|------|----------|
| `backend/core/zscore_calculator.py` | 수정 (Time-Projection 추가) |
| `backend/core/divergence_detector.py` | 신규 |
| `frontend/gui/dashboard.py` | 수정 (Signal 컬럼, Demote) |
| `docs/Plan/steps/development_steps.md` | 수정 (4.A.1-4.A.4 완료) |
| `docs/Plan/steps/step_4.a.4_plan.md` | 수정 (v4.0) |

---

## 🧪 검증

```bash
python -m py_compile backend/core/zscore_calculator.py backend/core/divergence_detector.py frontend/gui/dashboard.py
# 문법 오류 없음 ✓
```

---

## 📊 Divergence 해석

| zenV | zenP | Signal | 해석 |
|------|------|--------|------|
| **≥ 2.0** | **< 0.5** | 🔥 | 매집 가능성 (Divergence) |
| ≥ 2.0 | ≥ 1.5 | - | 모멘텀 상승 |
| < 0 | > 2.0 | - | 급등 후 거래량 감소 |

---

## 💡 다음 단계 제안

- Tier 2 Demote 타이머 (5분간 Ignition < 50 유지 시 자동 강등)
- Day Gainers API 통합 (4.A.2.3)
- 실거래 테스트
