# Devlog: Day Gainer Watchlist 병합 수정

**작성일**: 2026-01-06  
**이슈**: 01-002

---

## 📋 문제

Day Gainer로 탐지된 종목이 기존 Watchlist에 **추가되지 않고 대체**됨

## 🔍 Root Cause

`realtime_scanner.py` L278에서 브로드캐스트 시:
- **문제**: Scanner 내부 리스트(`self._watchlist`)만 전송
- **결과**: GUI가 전체 Watchlist를 1~2개 항목으로 대체

```python
# Before: 내부 리스트만 (1~2개)
await self.ws_manager.broadcast_watchlist(self._watchlist)
```

## ✅ 수정

### 1. `realtime_scanner.py` - 브로드캐스트 로직

`self._watchlist`가 `current`(전체 Watchlist)로 동기화된 후 브로드캐스트:

```python
# After: 동기화된 전체 리스트
self._watchlist = current  # 병합 후 동기화
await self.ws_manager.broadcast_watchlist(self._watchlist)
```

### 2. `routes.py` - Scanner 결과 병합 저장

```python
# Before (문제)
store.save(watchlist)

# After (수정)
from backend.data.watchlist_store import merge_watchlist
merged = merge_watchlist(watchlist, update_existing=True)
```

로그 레벨을 `info`로 변경하여 콘솔에서 확인 가능:
```
📤 Watchlist 브로드캐스트: 51개 (전체)
✅ Scanner 완료: 50개 스캔, 51개 총 Watchlist
```

## 📁 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/core/realtime_scanner.py` | L275-282: 브로드캐스트 로직 및 로그 수정 |
| `backend/api/routes.py` | L474-479: Scanner 결과 **병합 저장**으로 변경 |
| `backend/data/watchlist_store.py` | `merge_watchlist()` 함수 추가 |
| `backend/server.py` | L302: Scanner 결과 병합 로직 적용 |
| `frontend/gui/dashboard.py` | L1344-1360, L1462-1488: Watchlist 캐시 및 승격 조건 수정 |

---

## � 작업 이력

### Pass 1: 초기 수정 (실패)
- `realtime_scanner.py`에서 `dollar_volume` 추가, 병합 로직 추가
- `dashboard.py`에서 `_check_tier2_promotion` 추가
- **결과**: Backend 서버 미재시작으로 반영 안됨

### Pass 2: 서버 재시작 후에도 문제 지속
- **발견**: Backend가 48분간 구버전으로 실행 중
- **조치**: 모든 Python 프로세스 종료 후 재시작

### Pass 3: Watchlist 덮어쓰기 경로 분석
- **발견된 덮어쓰기 경로 (3곳)**:
  1. `realtime_scanner.py` L252: ✅ 병합으로 수정됨
  2. `server.py` L320: ✅ 병합으로 수정됨
  3. `routes.py` L477: 🔴 **미수정** (Scanner 재실행 시 덮어쓰기)
- **추가 조치**: `routes.py`에서도 `merge_watchlist()` 사용하도록 수정

### Pass 4: 최종 수정
- `routes.py` L474-479: Scanner 결과 병합 저장으로 변경
- 모든 파일 문법 검증 완료

---

## ✅ 검증 상태

- [x] `realtime_scanner.py` Syntax OK
- [x] `routes.py` Syntax OK
- [x] `watchlist_store.py` Syntax OK
- [x] `dashboard.py` Syntax OK
- [ ] 실제 동작 테스트

---

## �📚 관련 문서

- Issue 문서: `docs/Plan/bugfix/01-002_daygainer_watchlist_merge.md`
- 선행 이슈: `docs/Plan/bugfix/01-001_realtime_scanner_integration.md`
