# RealtimeScanner 코드 비대화 분석

**파일**: `backend/core/realtime_scanner.py`  
**현재 라인 수**: 760줄 (제한: 500줄)  
**분석일**: 2026-01-10

---

## 1. 메서드별 라인 수 분석

| 메서드 | 라인 범위 | 라인 수 | 비고 |
|--------|----------|---------|------|
| `__init__` | 69-120 | 51 | 초기화 |
| `start` | 126-163 | 37 | |
| `stop` | 165-200 | 35 | |
| `get_stats` | 202-212 | 10 | |
| `get_known_tickers` | 214-216 | 2 | |
| `_polling_loop` | 222-239 | 17 | |
| `_poll_gainers` | 241-284 | 43 | |
| **`_handle_new_gainer`** | 286-421 | **135** | ⚠️ 가장 큰 메서드 |
| **`_fetch_and_store_daily_bars`** | 427-497 | **70** | ⚠️ 데이터 레이어 책임 |
| **`_periodic_watchlist_broadcast`** | 503-628 | **125** | ⚠️ 브로드캐스트 + Score 계산 |
| **`recalculate_all_scores`** | 634-726 | **92** | ⚠️ Score 재계산 |
| `_periodic_score_recalculation` | 728-749 | 21 | |
| Properties | 751-759 | 8 | |
| **imports + docs** | 1-68 | 68 | 헤더 |

**총 17개 메서드** (클래스 제한 30개 이하 ✅)

---

## 2. 핵심 문제점

### 2.1 Single Responsibility 위반

현재 `RealtimeScanner`가 담당하는 책임:

| # | 책임 | 관련 메서드 | 분리 가능 여부 |
|---|------|-------------|---------------|
| 1 | Gainers API 폴링 | `_poll_gainers` | Core 유지 |
| 2 | 신규 종목 처리 | `_handle_new_gainer` | Core 유지 |
| 3 | **일봉 데이터 Fetch** | `_fetch_and_store_daily_bars` | ⚠️ DataRepository로 이동 |
| 4 | **Score 계산** | `_handle_new_gainer` 내부 | ⚠️ ScoringStrategy로 위임 |
| 5 | **Watchlist 저장** | `_handle_new_gainer` 내부 | ⚠️ WatchlistStore로 위임 |
| 6 | **WebSocket 브로드캐스트** | `_periodic_watchlist_broadcast` | ⚠️ Broadcaster로 분리 |
| 7 | **Score 재계산** | `recalculate_all_scores` | ⚠️ ScoreManager로 분리 |

---

### 2.2 비대 메서드 상세 분석

#### `_handle_new_gainer` (135줄)
```
- 역할: 신규 급등 종목 처리
- 문제: 여러 책임 혼재
  - DataRepository에서 일봉 조회 (L329-330)
  - ScoringStrategy로 score_v3 계산 (L336-347)
  - Watchlist 항목 생성 (L355-371)
  - WatchlistStore에 저장 (L374-393)
  - WebSocket 브로드캐스트 (L397-410)
  - IgnitionMonitor 등록 (L413-421)
```

#### `_periodic_watchlist_broadcast` (125줄)
```
- 역할: 1초마다 Watchlist GUI 브로드캐스트
- 문제: 브로드캐스트 + Score 계산 + Hydration 혼재
  - 가격 Hydration (L543-556)
  - Score V3 실시간 계산 (L558-609)
  - 파일 저장 (L612-616)
  - WebSocket 전송 (L619-625)
```

#### `_fetch_and_store_daily_bars` (70줄)
```
- 역할: Massive API → DB 저장
- 문제: DataRepository 책임
  - 이미 DataRepository.get_daily_bars(auto_fill=True) 존재
  - 중복 구현, 제거 후 DataRepository 사용 충분
```

---

## 3. 분리 권장 구조

```
RealtimeScanner (Core: ~300줄)
├── _poll_gainers()
├── _handle_new_gainer()  ← 오케스트레이션만
└── start() / stop()

WatchlistBroadcaster (New: ~150줄)
├── broadcast_watchlist()
├── hydrate_prices()
└── periodic_broadcast_loop()

ScoreRecalculationService (New: ~100줄)
├── recalculate_all_scores()
└── periodic_recalculation_loop()

[이미 존재]
├── DataRepository.get_daily_bars(auto_fill=True)
├── ScoringStrategy.calculate_watchlist_score_detailed()
└── WatchlistStore.save_watchlist()
```

---

## 4. 리팩터링 우선순위

| 순위 | 작업 | 예상 감소 | 난이도 |
|------|------|----------|-------|
| 1 | `_fetch_and_store_daily_bars` 제거 → DataRepository 사용 | -70줄 | 낮음 |
| 2 | `_periodic_watchlist_broadcast`에서 Score 계산 분리 | -50줄 | 중간 |
| 3 | `recalculate_all_scores` → ScoreRecalculationService | -92줄 | 중간 |
| 4 | `_handle_new_gainer` 내부 로직 위임 패턴 적용 | -30줄 | 중간 |

**예상 최종 라인 수**: ~500줄

---

## 5. 근본 원인

1. **점진적 기능 추가**: Phase 6, 7, 9 등 단계별로 기능이 추가되면서 비대화
2. **리팩터링 누락**: 신규 기능 추가 시 기존 코드 분리 없이 확장
3. **중복 구현**: DataRepository 존재에도 `_fetch_and_store_daily_bars` 별도 구현
4. **Orchestrator 역할 과다**: Scanner가 모든 후속 처리까지 담당
