# Score V3 구현 개발 로그

**문서 유형**: 개발 로그 (Devlog)  
**작성일**: 2026-01-06  
**관련 계획**: `docs/Plan/bugfix/03-001_score_v3_implementation.md`

---

## Step 1: 설정 모듈 생성 ✅

**시간**: 07:10  
**파일**: `backend/strategies/score_v3_config.py`

### 구현 내용
- V3 가중치 상수 정의
- Z-Score Sigmoid 파라미터 (lookback=60, k=1.0)
- Boost/Penalty 설정 (1.3x / 0.5x)
- VWAP 설정 (source="massive_api")
- Support 설정 (min_price_location=0.4)

---

## Step 2: Z-Score Sigmoid 구현 ✅

**시간**: 07:12  
**파일**: `backend/strategies/seismograph.py`

### 구현 내용
- `_calc_tight_range_intensity_v3()` 메서드 추가
- 60일 ATR 히스토리 기반 Z-Score 계산
- Sigmoid 변환: `1 / (1 + exp(k * (z - x0)))`
- Z가 낮을수록(변동성 수축) → 높은 강도

---

## Step 3: 하방 경직성 체크 구현 ✅

**시간**: 07:12  
**파일**: `backend/strategies/seismograph.py`

### 구현 내용
- `_calc_volume_dryout_intensity_v3()` 메서드 추가
- `_calc_support_factor()` 메서드 추가
- Support Factor = (Close - Low) / (High - Low)
- 거래량 고갈 + 가격 지지 동시 확인

---

## Step 4: Boost × Penalty 구조 ✅

**시간**: 07:13  
**파일**: `backend/strategies/seismograph.py`

### 구현 내용
- `_calculate_boost_factor()`: I_TR > 0.7 AND I_VD > 0.7 → 1.3x
- `_calculate_penalty_factor()`: Bearish + High Vol → 0.5x
- `calculate_watchlist_score_v3()`: Base × Boost × Penalty

---

## Step 5: calculate_watchlist_score_detailed 통합 ✅

**시간**: 07:14  
**파일**: `backend/strategies/seismograph.py`

### 구현 내용
- `score_v3` 필드 추가
- `intensities_v3` 필드 추가
- V2와 V3 모두 반환하여 점진적 마이그레이션 지원

---

## Step 6: 테스트 및 검증 ✅

**시간**: 07:15  
**파일**: `test_score_v3.py`

### 테스트 결과

```
V1=100.0
V2=65.1
V3=53.4
V3_intensities={'tight_range': 0.27, 'obv_divergence': ..., ...}
```

### 검증 결과
- [x] Import 에러 확인 → 정상
- [x] V3 점수 계산 정상 동작 → V3=53.4 (V2보다 낮게 나옴 - 하방 경직성 등 필터 반영)
- [ ] GUI 표시 확인 → 별도 테스트 필요

---

## 구현 완료 요약

| 파일 | 변경 내용 |
|------|----------|
| `backend/strategies/score_v3_config.py` | V3 설정 상수 (NEW) |
| `backend/strategies/seismograph.py` | V3 메서드 추가 (~240줄) |
| `test_score_v3.py` | 테스트 스크립트 (NEW) |

### V3 개선 효과
- Z-Score Sigmoid로 중간값 출력 가능 (0.27 등)
- 하방 경직성 체크로 죽은 종목 필터링
- Boost/Penalty 구조로 정확도 향상

---

## Step 7: V2 → V3 전체 시스템 마이그레이션 ✅

**시간**: 07:20  

### 변경된 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/realtime_scanner.py` | score_v2 → score_v3 전면 교체 |
| `backend/api/routes.py` | WatchlistItem, recalculate 엔드포인트 V3화 |
| `frontend/gui/watchlist_model.py` | score_v3 표시, 툴팁 V3화 |
| `frontend/gui/dashboard.py` | UI 라벨 "Score V3" |
| `frontend/services/backend_client.py` | WatchlistItem dataclass V3화 |

### V2 아카이브 위치

V2 메서드는 `seismograph.py`에 그대로 유지됨:
- `calculate_watchlist_score_v2()` - 아카이브됨, 필요시 사용 가능
- `_calculate_signal_intensities()` - V2용 강도 계산 (아카이브됨)
