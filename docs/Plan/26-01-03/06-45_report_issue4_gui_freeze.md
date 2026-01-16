# Issue 4 수정 완료 리포트: Scanner 실행 시 GUI 프리즈

**완료일시**: 2026-01-03 06:44:39 (KST)

---

## 문제 설명

Scanner가 실행될 때 GUI가 프리즈되는 현상이 발생했습니다. 사용자가 전략을 선택하거나 Watchlist가 자동 갱신될 때마다 GUI가 수 초 동안 멈추는 문제였습니다.

---

## 원인 분석

### 근본 원인
`BackendClient.run_scanner_sync()` 메서드가 **동기적으로 결과를 대기**하여 UI 스레드를 블로킹했습니다.

### 문제 코드 (수정 전)
```python
# frontend/services/backend_client.py (Line 293-299)
def run_scanner_sync(self, strategy_name: str = "seismograph"):
    """동기 스캐너 실행"""
    try:
        self._run_async(self.run_scanner(strategy_name))  # ← 최대 30초 블로킹
    except Exception as e:
        logger.error(f"run_scanner_sync failed: {e}")
        self.log_message.emit(f"❌ Scanner failed: {e}")
```

### `_run_async` 내부 로직
```python
def _run_async(self, coro):
    loop = self._get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)  # ← 여기서 30초까지 UI 스레드 블로킹!
```

### 호출 지점 (3곳)
1. **`_auto_connect_backend()`** (line 211): GUI 시작 시 자동 연결 후 Scanner 실행
2. **`_refresh_watchlist()`** (line 773): 1분 주기 자동 갱신
3. **`_run_scanner_for_strategy()`** (line 1283): 전략 변경 시 Scanner 실행

---

## 해결 방안

### 수정 내용
`run_scanner_sync()`를 **Fire-and-Forget 패턴**으로 변경하여 비동기 스레드에서 실행하고, 결과를 기다리지 않습니다.

### 수정된 코드
```python
# frontend/services/backend_client.py (Line 293-311)
def run_scanner_sync(self, strategy_name: str = "seismograph"):
    """
    비동기 스캐너 실행 (Non-blocking)
    
    ⚠️ [BUGFIX] GUI 프리즈 해결:
    이전: future.result()로 동기 대기 → UI 블로킹
    이후: fire-and-forget 패턴으로 백그라운드 실행 → UI 반응성 유지
    
    결과는 watchlist_updated 시그널을 통해 전달됩니다.
    """
    import asyncio
    try:
        loop = self._get_event_loop()
        # Fire-and-forget: 결과를 기다리지 않음
        asyncio.run_coroutine_threadsafe(self.run_scanner(strategy_name), loop)
        # 결과는 run_scanner() → refresh_watchlist() → watchlist_updated.emit()으로 전달됨
    except Exception as e:
        logger.error(f"run_scanner_sync failed: {e}")
        self.log_message.emit(f"❌ Scanner failed: {e}")
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `frontend/services/backend_client.py` | `run_scanner_sync()` 메서드를 non-blocking 방식으로 변경 |

---

## 동작 방식 변경

### 이전 (블로킹)
```
UI Thread: run_scanner_sync() 호출
    ↓
UI Thread: _run_async() → future.result() 대기 (최대 30초)
    ↓
UI Thread: GUI 프리즈 😱
    ↓
UI Thread: 결과 반환 후 다음 작업 진행
```

### 이후 (Non-blocking)
```
UI Thread: run_scanner_sync() 호출
    ↓
Background Thread: Scanner 실행 (비동기)
    ↓
UI Thread: 즉시 반환 → GUI 반응성 유지 ✅
    ↓
Background Thread: 완료 시 watchlist_updated.emit() 시그널 발생
    ↓
UI Thread: 시그널 핸들러에서 Watchlist 업데이트
```

---

## 검증 방법

1. GUI 실행
2. 전략 선택 시 GUI가 멈추지 않는지 확인
3. 1분 후 자동 갱신 시 GUI가 멈추지 않는지 확인
4. Watchlist가 정상적으로 업데이트되는지 확인

---

## 상태

✅ **완료**
