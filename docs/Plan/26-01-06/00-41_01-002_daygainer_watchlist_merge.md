# Issue Report: Day Gainer 워치리스트 편입 실패

**작성일**: 2026-01-06  
**버전**: v1.0  
**우선순위**: 🔴 Critical  
**상태**: ✅ 수정 완료

---

## 문제 설명

### 증상
- Day Gainer로 탐지된 종목이 기존 50개 Watchlist에 **추가되지 않고 대체**됨
- 최초 등장 후 다음 갱신에서 **사라짐** (깜빡임)
- 결과적으로 Day Gainer 종목이 Watchlist에 **영구 편입되지 않음**

### 기대 동작
1. RealtimeScanner가 새 급등 종목 탐지
2. 기존 50개 Watchlist에 **병합(Merge)** 되어 51개가 됨
3. GUI에서 병합된 전체 Watchlist 표시

---

## Root Cause 분석

### 🔴 핵심 문제: 브로드캐스트 시 잘못된 데이터 사용

`backend/core/realtime_scanner.py` L278:
```python
# 현재 코드 (문제)
await self.ws_manager.broadcast_watchlist(self._watchlist)  # ❌ 내부 리스트만!
```

### 🔴 추가 발견: Scanner 재실행 시 덮어쓰기

`backend/api/routes.py` L477:
```python
# 문제: 전체 덮어쓰기
store.save(watchlist)  # ❌ Day Gainer 삭제됨
```

**문제점**:
- `self._watchlist`는 **RealtimeScanner가 탐지한 종목만** 포함
- 병합된 전체 Watchlist(`current`)가 아님
- GUI는 이 리스트를 받아 **전체 Watchlist를 대체**함

### 데이터 흐름 비교

| 단계 | 기대 동작 | 실제 동작 |
|------|----------|----------|
| 1. Scanner 탐지 | SMXT 탐지 | ✅ 정상 |
| 2. 파일 병합 | 50개 + SMXT = 51개 | ✅ 수정됨 (merge_watchlist) |
| 3. 브로드캐스트 | `current` (51개) 전송 | 🔴 `self._watchlist` (1개만) 전송 |
| 4. GUI 표시 | 51개 표시 | 1개만 표시 후 덮어쓰기 |

---

## 해결 방안

### 수정 대상
`backend/core/realtime_scanner.py` L278

### 수정 내용
```python
# Before (문제)
await self.ws_manager.broadcast_watchlist(self._watchlist)

# After (수정)
await self.ws_manager.broadcast_watchlist(current)  # 병합된 전체 리스트 사용
```

### 전체 코드 컨텍스트
```python
# [Issue 6.2 Fix] 기존 Watchlist와 병합 (덮어쓰기 대신)
try:
    from backend.data.watchlist_store import load_watchlist, save_watchlist
    current = load_watchlist()  # 기존 Watchlist 로드
    
    # 중복 체크 후 추가
    existing_tickers = {w.get("ticker") for w in current}
    if ticker not in existing_tickers:
        current.append(watchlist_item)
        save_watchlist(current)
        self._watchlist = current  # 동기화
    else:
        self._watchlist = current
except Exception as e:
    logger.warning(f"⚠️ Watchlist 저장 실패: {e}")
    self._watchlist.append(watchlist_item)
    current = self._watchlist  # fallback

# 3. WebSocket 브로드캐스트 (전체 Watchlist)
if self.ws_manager:
    try:
        await self.ws_manager.broadcast_watchlist(current)  # ✅ 병합된 리스트
        logger.debug(f"📤 Watchlist 브로드캐스트: {len(current)}개")
    except Exception as e:
        logger.warning(f"⚠️ WebSocket 브로드캐스트 실패: {e}")
```

---

## 영향 범위 (수정 완료)

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/realtime_scanner.py` | L275-282: 브로드캐스트 로직 및 로그 수정 |
| `backend/api/routes.py` | L474-479: Scanner 결과 **병합 저장**으로 변경 |

### `routes.py` 추가 수정

```python
# Before (문제)
store.save(watchlist)

# After (수정)
from backend.data.watchlist_store import merge_watchlist
merged = merge_watchlist(watchlist, update_existing=True)
logger.info(f"✅ Scanner 완료: {len(watchlist)}개 스캔, {len(merged)}개 총 Watchlist")
```

---

## 검증 계획

### 테스트 시나리오
1. 서버 시작 → Watchlist에 기존 50개 종목 로드 확인
2. RealtimeScanner 실행 → 새 급등 종목 탐지
3. GUI 확인 → **51개** 종목이 표시되는지 확인
4. **Scanner 재실행** → **51개 유지** 확인 (덮어쓰기 안됨)
5. 1분 대기 → 종목이 **사라지지 않는지** 확인

### 검증 로그
- `[INFO] ✅ Watchlist 병합 완료: +1 추가`
- `[INFO] 📤 Watchlist 브로드캐스트: 51개 (전체)`
- `[INFO] ✅ Scanner 완료: 50개 스캔, 51개 총 Watchlist`

---

## 참고

- 관련 이슈: `01-001_realtime_scanner_integration.md`
- 수정 이력: `docs/devlog/01-002_daygainer_merge_fix.md`
