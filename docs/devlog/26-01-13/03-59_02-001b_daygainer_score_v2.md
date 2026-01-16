# 02-001b Day Gainer Score V2 구현 로그

**시작**: 2026-01-06 03:40  
**완료**: 2026-01-06 03:44  
**상태**: ✅ 구현 완료

---

## 작업 체크리스트

- [x] RealtimeScanner 초기화에 `db` 파라미터 추가
- [x] `_fetch_and_store_daily_bars()` 헬퍼 메서드 추가
- [x] `_handle_new_gainer()` 수정 (DB 조회 → API fetch → score 계산)
- [x] 서버 초기화에서 DB 주입 (`server.py`)
- [ ] 테스트 및 검증

---

## 작업 로그

### [03:40] 작업 시작
- 02-001b bugfix 계획 문서 기반 구현 시작
- Massive API fetch + DB 삽입 로직 포함

### [03:41] `__init__` 수정 완료
- `db: Optional[Any] = None` 파라미터 추가
- `self.db`, `self.strategy` 필드 추가
- SeismographStrategy lazy 초기화 (db 있을 때만)

### [03:42] `_handle_new_gainer()` 수정 완료
- DB에서 일봉 조회 → API fetch → score_v2 계산 로직 추가
- score=None일 경우 GUI에서 ⚠️ 표시되도록 변경

### [03:43] `_fetch_and_store_daily_bars()` 추가 완료
- Massive API에서 특정 종목 일봉 fetch
- 최근 10거래일만 가져와 DB에 삽입
- API 부하 최소화

### [03:44] `server.py` 수정 완료
- `initialize_realtime_scanner()` 호출 시 `db=app_state.db` 주입

### [03:51] Phase 6: score_v2 실시간 계산 추가
- `_periodic_watchlist_broadcast()`에서 score_v2 없는 항목 실시간 계산
- DB에서 일봉 조회 → score_v2 계산 → 저장소 영구 반영
- 중복 계산 방지를 위한 `_score_v2_calculated` 캐시 구현

### [04:03] Phase 7: 이중 이모지 시스템 작업 시작
- 🆕(신규/IPO)와 ⚠️(오류) 구분
- 일봉 5일 미만 → score_v2=-1 → 🆕 표시

### [04:05] Phase 7: 백엔드 수정 완료
- `realtime_scanner.py`: `_periodic_watchlist_broadcast()`에 Phase 7 분기 추가
- 일봉 5일 미만 시 `score_v2 = -1`, `stage = "신규/IPO (데이터 부족)"`

### [04:06] Phase 7: 프론트엔드 수정 완료
- `watchlist_model.py`: score_v2 표시 로직에 분기 추가
- `score_v2 == -1` → "🆕" 표시 + 툴팁 "신규/IPO 종목"
- `score_v2 is None or 0` → "⚠️" 표시 + 툴팁 "score_v2 계산 실패"

### [04:11] Phase 8: 0점 전용 이모지 도입
- 원인: BVC, TMDE, VRME 등 DB에 일봉 있지만 매집 신호 탐지 안됨 → `score_v2=0`
- 해결: `score_v2 == 0` → "➖" 표시 + 툴팁 "매집 신호 없음"
- Warrant(W 접미사) 종목 등에 적용

### [04:30] Phase 9: Score 재계산 시스템 (백엔드)
- `recalculate_all_scores()`: 순차 재계산 (100ms 딜레이/종목)
- `_periodic_score_recalculation()`: 1시간마다 자동 재계산
- start/stop에 재계산 태스크 연동
- API 엔드포인트: `POST /api/watchlist/recalculate`
- `get_scanner_instance()` 함수 추가

### [04:38] Phase 9: Score 재계산 시스템 (프론트엔드)
- Tier 1 Watchlist 패널에 "Score V2 Refresh" 버튼 추가 (🔄)
- "Score V2: --:--" Last Updated 라벨 추가
- 버튼 클릭 시 API 호출 → 완료 시 타임스탬프 업데이트
- 툴팁: "Score V2 재계산 (Watchlist 전체 아님)"

---

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/realtime_scanner.py` | Phase 6/7/8 + Phase 9 (순차 재계산, 1시간 자동) |
| `backend/api/routes.py` | `/watchlist/recalculate` API 추가 |
| `backend/server.py` | DB 주입 |
| `frontend/gui/watchlist_model.py` | 🆕/➖/⚠️ 분기 처리 |
| `frontend/gui/dashboard.py` | Score V2 Refresh 버튼 + Last Updated 라벨 |

---

## 다음 작업

- [ ] 프론트엔드: Refresh 버튼 + Last Updated 라벨 추가
