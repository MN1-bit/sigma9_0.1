# Issue 5 수정 완료 리포트: IgnitionMonitor 자동 시작/종료

**완료일시**: 2026-01-03 06:56:11 (KST)

---

## 문제 설명

IgnitionMonitor(Ignition Score 계산)가 서버 시작 시 자동으로 시작되지 않고, 종료 시 자동으로 종료되지 않았습니다.

---

## 원인 분석

### 이전 상태
```python
# server.py (Startup)
app_state.ignition_monitor = initialize_ignition_monitor(strategy, ws_manager)
# ❌ start() 호출 없음 - 인스턴스만 생성되고 폴링 루프는 시작 안됨

# server.py (Shutdown)
# ❌ IgnitionMonitor.stop() 호출 없음
```

### 문제
1. **시작**: 인스턴스만 생성되고 `start()` 메서드가 호출되지 않아 1초 폴링 루프가 시작되지 않음
2. **종료**: `stop()` 메서드가 호출되지 않아 비동기 태스크가 정리되지 않음

---

## 해결 방안

### 1. 서버 시작 시 자동 시작

**파일**: `backend/server.py` (Line 297-309 추가)

```python
# 7. IgnitionMonitor 자동 시작 [Bugfix: Ignition Score 자동 계산]
if app_state.ignition_monitor:
    try:
        from backend.data.watchlist_store import load_watchlist
        watchlist = load_watchlist()
        if watchlist:
            await app_state.ignition_monitor.start(watchlist)
            logger.info(f"✅ IgnitionMonitor started with {len(watchlist)} tickers")
        else:
            logger.info("ℹ️ IgnitionMonitor: No watchlist, will start when scanner runs")
    except Exception as e:
        logger.warning(f"⚠️ IgnitionMonitor auto-start skipped: {e}")
```

### 2. 서버 종료 시 자동 종료

**파일**: `backend/server.py` (Line 318-326 추가)

```python
# IgnitionMonitor 종료 [Bugfix: Ignition Score 자동 종료]
if app_state.ignition_monitor:
    try:
        await app_state.ignition_monitor.stop()
        logger.info("✅ IgnitionMonitor stopped")
    except Exception as e:
        logger.error(f"❌ IgnitionMonitor shutdown error: {e}")
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `backend/server.py` | Startup 시 auto-start, Shutdown 시 auto-stop 추가 |

---

## 동작 방식

### 서버 시작 시
```
Server Startup
    ↓
IgnitionMonitor 인스턴스 생성 (Line 152-161)
    ↓
... (Daily Sync 등) ...
    ↓
Watchlist 로드 (watchlist_store.json)
    ↓
watchlist 있음?
    ↓ Yes
ignition_monitor.start(watchlist)
    ↓
1초 폴링 루프 시작 → Ignition Score 계산 시작 ✅
```

### 서버 종료 시
```
Server Shutdown (Ctrl+C)
    ↓
ignition_monitor.stop()
    ↓
폴링 태스크 취소, 리소스 정리
    ↓
Scheduler 종료
    ↓
IBKR 연결 해제
    ↓
종료 ✅
```

---

## 검증 방법

1. 서버 시작 후 로그 확인:
   ```
   ✅ IgnitionMonitor started with X tickers
   ```

2. 서버 종료 시 로그 확인:
   ```
   🛑 Server Shutting Down...
   ✅ IgnitionMonitor stopped
   ```

3. GUI에서 Ignition Score가 실시간으로 표시되는지 확인

---

## 상태

✅ **완료**
