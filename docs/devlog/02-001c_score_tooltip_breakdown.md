# 02-001c: Score V2 툴팁 계산 요소 표시

**작업 상태**: ✅ 완료
**시작일**: 2026-01-06
**완료일**: 2026-01-06
**관련 Plan**: `docs/Plan/bugfix/02-001c_score_tooltip_breakdown.md`

---

## 작업 목표

Watchlist의 Score 컬럼에 마우스를 올렸을 때, 계산에 사용된 4가지 신호 강도를 툴팁으로 표시

### 표시할 신호
- **Tight Range** (VCP 패턴) - 30%
- **OBV Divergence** (스마트 머니) - 35%
- **Accumulation Bar** (매집 완료) - 25%
- **Volume Dryout** (준비 단계) - 10%

---

## 작업 로그

### Phase 1: 코드 분석 (2026-01-06 04:58)

#### 분석 결과

1. **`backend/strategies/seismograph.py`**
   - `calculate_watchlist_score_detailed()` (702~743줄)에서 이미 `intensities` dict 반환
   - ✅ **수정 불필요**

2. **`backend/core/realtime_scanner.py`**
   - `_handle_new_gainer()`, `_periodic_watchlist_broadcast()`, `recalculate_all_scores()` 
   - ⚠️ **수정 필요**: 3곳에서 `intensities` 추가 필요

3. **`frontend/gui/watchlist_model.py`**
   - ⚠️ **수정 필요**: `_build_score_tooltip()` 메서드 추가

---

### Phase 2: 백엔드 수정 (2026-01-06 05:00)

**파일**: `backend/core/realtime_scanner.py`

수정 완료:
1. `_handle_new_gainer()` - `intensities` 변수 선언 및 watchlist_item에 추가
2. `_periodic_watchlist_broadcast()` - result에서 `intensities` 추출하여 item에 추가
3. `recalculate_all_scores()` - result에서 `intensities` 추출하여 item에 추가

---

### Phase 3: 프론트엔드 수정 (2026-01-06 05:01)

**파일**: `frontend/gui/watchlist_model.py`

수정 완료:
1. `_build_score_tooltip()` 메서드 추가 - 신호 강도 시각화 툴팁 생성
2. `_set_row_data()` - 모든 Score 케이스에서 `_build_score_tooltip()` 호출

---

### Phase 4: 버그 수정 (2026-01-06 05:20~05:35)

**문제**: GUI에서 `intensities`가 항상 빈 dict `{}`로 표시됨

**디버깅 과정**:
1. `watchlist_current.json` 확인 → `intensities` 데이터 정상 저장됨
2. REST API 응답 확인 → `intensities` 포함되어 반환됨
3. 프론트엔드 데이터 흐름 추적:
   - `rest_adapter.py` → 정상
   - `backend_client.py` → `WatchlistItem.from_dict()` 변환 시 손실 ⚠️
   - `dashboard.py` → `item_data`에 `intensities` 누락 ⚠️

**근본 원인**:
1. `backend_client.py`에서 `WatchlistItem.from_dict()` 변환 시 `intensities` 필드 손실
2. `dashboard.py`의 `_update_watchlist_panel()`에서 `item_data` dict에 `intensities` 미포함

**수정 내용**:

| 파일 | 수정 내용 |
|------|----------|
| `backend/api/routes.py` | Pydantic 모델 대신 raw dict 반환 |
| `frontend/services/backend_client.py` | `WatchlistItem.from_dict()` 변환 제거 (3곳) |
| `frontend/gui/dashboard.py` | `_update_watchlist_panel()`에 `intensities` 추가 |

---

### Phase 5: 검증 완료 (2026-01-06 05:40)

✅ GUI에서 Score 컬럼 툴팁에 4가지 신호 강도 바가 정상 표시됨

---

## 수정 파일 목록

| 파일 | 상태 | 변경 내용 |
|------|------|----------|
| `backend/strategies/seismograph.py` | ✅ 수정 불필요 | 이미 `intensities` 반환 |
| `backend/core/realtime_scanner.py` | ✅ 완료 | `intensities` 3곳 추가 |
| `backend/api/routes.py` | ✅ 완료 | raw dict 반환 (Pydantic 제거) |
| `frontend/services/backend_client.py` | ✅ 완료 | `WatchlistItem.from_dict()` 변환 제거 |
| `frontend/gui/dashboard.py` | ✅ 완료 | `item_data`에 `intensities` 추가 |
| `frontend/gui/watchlist_model.py` | ✅ 완료 | `_build_score_tooltip()` 추가 |

---

## 후속 작업

- [ ] 툴팁 바 정렬 개선 (라벨 고정폭 적용했으나 폰트 문제로 미완)
