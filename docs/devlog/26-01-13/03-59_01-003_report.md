# Devlog 01-003: Watchlist Data Refresh Fix (완료)

**작성일**: 2026-01-06  
**작업자**: AI Assistant  
**이슈**: `docs/Plan/bugfix/01-003_watchlist_data_refresh.md`  
**상태**: ✅ 구현 완료

---

## 문제 요약

Watchlist Refresh 시 `dollar_volume`, `score`, `ignition` 값이 일부 종목에서 사라지는 문제.
특히 Day Gainer로 추가된 종목에서 발생.

---

## 해결 방안

### Phase 1: Backend 주기적 브로드캐스트

**파일**: `backend/core/realtime_scanner.py`

1. `_latest_prices` 딕셔너리 추가 (ticker → (price, volume) 캐시)
2. `_periodic_watchlist_broadcast()` 메서드 구현 (1초 간격)
3. Watchlist 데이터 Hydration: 실시간 가격으로 `dollar_volume` 재계산
4. 태스크 생명주기 관리 (`start()`, `stop()`)

### Phase 2: Frontend 경고 표시

**파일**: `frontend/gui/dashboard.py`

`_update_watchlist_panel()` 메서드에 **Transparency Protocol** 적용:

| 필드 | 조건 | 표시 |
|------|------|------|
| Dollar Volume | `<= 0` | ⚠️ + ToolTip |
| Score | `<= 0` | ⚠️ + ToolTip |
| Ignition | 모니터링 활성화 + 데이터 없음 | ⚠️ + ToolTip |

---

## 핵심 원칙

> **"Transparency Over Fallback"**
> 
> 데이터 누락 시 캐시된 값으로 대체하지 않고, 사용자에게 명시적으로 경고하여  
> 데이터 품질 문제를 인지할 수 있도록 함.

---

## 변경된 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/realtime_scanner.py` | 주기적 브로드캐스트 + 가격 캐시 추가 |
| `frontend/gui/dashboard.py` | 경고 아이콘 표시 로직 추가 |

---

## 검증 계획

1. GUI 시작 → Watchlist 50개 로드
2. Day Gainer 탐지 → 51개 표시
3. **1초 대기** → 모든 컬럼에 값 표시되는지 확인
4. 10초 관찰 → 값이 사라지지 않는지 확인
5. 데이터 누락 시 ⚠️ 아이콘 + ToolTip 표시 확인

---

## 관련 문서

- Phase 1 상세: `docs/devlog/01-003_phase1_backend_broadcast.md`
- Phase 2 상세: `docs/devlog/01-003_phase2_frontend_warning.md`
- 원본 이슈: `docs/Plan/bugfix/01-003_watchlist_data_refresh.md`

---

## Phase 3: WatchlistItem 필드 누락 수정 (2026-01-06 01:05)

### 근본 원인

Phase 1, 2 구현 후에도 데이터가 표시되지 않음.

**원인**: `frontend/services/backend_client.py`의 `WatchlistItem` dataclass에 
`dollar_volume`, `price`, `volume` 필드가 **정의되지 않음**.

백엔드에서 보낸 데이터가 `from_dict()` 메서드에서 무시되어 항상 0이 됨.

### 해결

`WatchlistItem` dataclass에 누락된 필드 추가:

```python
@dataclass
class WatchlistItem:
    ticker: str
    score: float
    stage: str
    last_close: float = 0.0
    change_pct: float = 0.0
    avg_volume: float = 0.0
    # [Issue 01-003] 추가 필드
    dollar_volume: float = 0.0
    price: float = 0.0
    volume: float = 0.0
    stage_number: int = 0
    source: str = ""
```

### 변경된 파일

| 파일 | 변경 내용 |
|------|----------|
| `frontend/services/backend_client.py` | WatchlistItem에 `dollar_volume`, `price`, `volume`, `stage_number`, `source` 필드 추가 |

