# [02-003] IBKRConnector PyQt6 Decoupling

> **작성일**: 2026-01-17 05:11 ~ 05:27
> **계획서**: [16-36_02-003_ibkr_connector_decoupling.md](file:///D:/Codes/Sigma9-0.1/docs/Plan/26-01-16/16-36_02-003_ibkr_connector_decoupling.md)

---

## 목표

Backend Layer의 `IBKRConnector`에서 PyQt6 의존성을 완전히 제거하여 **레이어 경계 위반 해결**.
Frontend에서만 PyQt6를 사용하도록 분리.

---

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1.0 IBKRConnector 순수 Python 전환 | ✅ | 05:11-05:25 |
| Step 2.0 Frontend Adapter 생성 | ✅ | 05:25-05:28 |
| Step 3.0 GUI 연결 포인트 업데이트 | ✅ (N/A) | 05:28 |
| Step 4.0 검증 | ✅ | 05:28-05:30 |

---

## Step 1.0: IBKRConnector 순수 Python 전환

### 파일: `backend/broker/ibkr_connector.py`

### 1.1 Import 변경

**Before:**
```python
from PyQt6.QtCore import QThread, pyqtSignal
```

**After:**
```python
import threading
import time
from typing import Callable, Optional
```

### 1.2 클래스 상속 제거

**Before:**
```python
class IBKRConnector(QThread):
    # pyqtSignal 정의
    connected = pyqtSignal(bool)
    account_update = pyqtSignal(dict)
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)
    order_placed = pyqtSignal(dict)
    order_filled = pyqtSignal(dict)
    order_cancelled = pyqtSignal(dict)
    order_error = pyqtSignal(str, str)
    positions_update = pyqtSignal(list)
```

**After:**
```python
# Callback 타입 정의
OnConnectedCallback = Callable[[bool], None]
OnAccountUpdateCallback = Callable[[dict], None]
OnErrorCallback = Callable[[str], None]
OnLogMessageCallback = Callable[[str], None]
OnOrderPlacedCallback = Callable[[dict], None]
OnOrderFilledCallback = Callable[[dict], None]
OnOrderCancelledCallback = Callable[[dict], None]
OnOrderErrorCallback = Callable[[str, str], None]
OnPositionsUpdateCallback = Callable[[list], None]

class IBKRConnector:
    # 순수 Python 클래스 (PyQt6 의존성 없음)
```

### 1.3 `__init__` 메서드 변경

**Before:**
```python
def __init__(self, parent=None) -> None:
    super().__init__(parent)
    # ... 기존 초기화
```

**After:**
```python
def __init__(self) -> None:
    # IB 객체
    self.ib: Optional[IB] = None
    
    # 연결 설정
    self.host = os.getenv("IB_HOST", "127.0.0.1")
    self.port = int(os.getenv("IB_PORT", "4002"))
    self.client_id = int(os.getenv("IB_CLIENT_ID", "1"))
    
    # 상태 플래그
    self._is_running: bool = False
    self._is_connected: bool = False
    
    # 스레드 관리 [02-003 신규]
    self._thread: Optional[threading.Thread] = None
    
    # Callback 속성 초기화 [02-003 신규]
    self._on_connected: Optional[OnConnectedCallback] = None
    self._on_account_update: Optional[OnAccountUpdateCallback] = None
    self._on_error: Optional[OnErrorCallback] = None
    self._on_log_message: Optional[OnLogMessageCallback] = None
    self._on_order_placed: Optional[OnOrderPlacedCallback] = None
    self._on_order_filled: Optional[OnOrderFilledCallback] = None
    self._on_order_cancelled: Optional[OnOrderCancelledCallback] = None
    self._on_order_error: Optional[OnOrderErrorCallback] = None
    self._on_positions_update: Optional[OnPositionsUpdateCallback] = None
```

### 1.4 Callback Setter 메서드 추가 (9개)

```python
def set_on_connected(self, callback: OnConnectedCallback) -> None:
    """연결 상태 변경 callback 설정"""
    self._on_connected = callback

def set_on_account_update(self, callback: OnAccountUpdateCallback) -> None:
    """계좌 업데이트 callback 설정"""
    self._on_account_update = callback

def set_on_error(self, callback: OnErrorCallback) -> None:
    """에러 callback 설정"""
    self._on_error = callback

def set_on_log_message(self, callback: OnLogMessageCallback) -> None:
    """로그 메시지 callback 설정"""
    self._on_log_message = callback

def set_on_order_placed(self, callback: OnOrderPlacedCallback) -> None:
    """주문 접수 callback 설정"""
    self._on_order_placed = callback

def set_on_order_filled(self, callback: OnOrderFilledCallback) -> None:
    """주문 체결 callback 설정"""
    self._on_order_filled = callback

def set_on_order_cancelled(self, callback: OnOrderCancelledCallback) -> None:
    """주문 취소 callback 설정"""
    self._on_order_cancelled = callback

def set_on_order_error(self, callback: OnOrderErrorCallback) -> None:
    """주문 에러 callback 설정"""
    self._on_order_error = callback

def set_on_positions_update(self, callback: OnPositionsUpdateCallback) -> None:
    """포지션 업데이트 callback 설정"""
    self._on_positions_update = callback
```

### 1.5 `_emit_*` 헬퍼 메서드 추가 (9개)

Signal emit 대신 callback을 호출하는 헬퍼 메서드:

```python
def _emit_connected(self, is_connected: bool) -> None:
    """연결 상태 변경 알림 (callback 호출)"""
    if self._on_connected:
        self._on_connected(is_connected)

def _emit_account_update(self, info: dict) -> None:
    """계좌 업데이트 알림"""
    if self._on_account_update:
        self._on_account_update(info)

def _emit_error(self, message: str) -> None:
    """에러 알림"""
    if self._on_error:
        self._on_error(message)

def _emit_log_message(self, message: str) -> None:
    """로그 메시지 알림"""
    if self._on_log_message:
        self._on_log_message(message)

# ... (order_placed, order_filled, order_cancelled, order_error, positions_update 동일 패턴)
```

### 1.6 Signal emit → _emit_* 변환 (전체 파일)

**Before:**
```python
self.log_message.emit("🔌 IBKR 연결 시도 중...")
self.connected.emit(True)
self.error.emit(f"❌ 연결 오류: {str(e)}")
```

**After:**
```python
self._emit_log_message("🔌 IBKR 연결 시도 중...")
self._emit_connected(True)
self._emit_error(f"❌ 연결 오류: {str(e)}")
```

### 1.7 QThread 관련 메서드 변환

**Before (QThread 사용):**
```python
def run(self) -> None:
    """QThread.start() 호출 시 자동 실행"""
    # ...
    QThread.msleep(wait_time * 1000)  # 밀리초
    # ...

def stop(self) -> None:
    self._is_running = False
    self.wait(5000)  # QThread.wait()
```

**After (threading.Thread 사용):**
```python
def start(self) -> None:
    """연결 시작 (백그라운드 스레드에서 실행)"""
    if self._thread and self._thread.is_alive():
        self._emit_log_message("⚠️ 이미 실행 중입니다")
        return
    
    self._thread = threading.Thread(target=self._run, daemon=True)
    self._thread.start()

def _run(self) -> None:
    """스레드 메인 루프 (start() 호출 시 백그라운드에서 실행)"""
    # ...
    time.sleep(wait_time)  # 초 단위
    # ...

def stop(self) -> None:
    self._is_running = False
    self._emit_log_message("⏹ 연결 중지 요청됨...")
    
    if self._thread and self._thread.is_alive():
        self._thread.join(timeout=5.0)
```

### 1.8 `__main__` 테스트 블록 변환

**Before (PyQt6 필요):**
```python
if __name__ == "__main__":
    from PyQt6.QtCore import QCoreApplication, QTimer
    app = QCoreApplication(sys.argv)
    connector = IBKRConnector()
    connector.connected.connect(lambda x: print(...))
    connector.start()
    QTimer.singleShot(15000, shutdown)
    sys.exit(app.exec())
```

**After (순수 Python):**
```python
if __name__ == "__main__":
    def on_connected(is_connected: bool) -> None:
        status = "🟢 연결됨" if is_connected else "🔴 연결 안됨"
        print(f"[연결 상태] {status}")
    
    connector = IBKRConnector()
    connector.set_on_connected(on_connected)
    connector.set_on_log_message(lambda msg: print(f"[로그] {msg}"))
    
    connector.start()
    
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        print("\n[Ctrl+C 감지]")
    finally:
        connector.stop()
```

---

## Step 2.0: Frontend Adapter 생성

### 파일: `frontend/services/ibkr_adapter.py` (신규 ~190줄)

### 핵심 구조

```python
from PyQt6.QtCore import QObject, pyqtSignal

class IBKREventAdapter(QObject):
    """Backend Callback → Frontend PyQt Signal 브릿지"""
    
    # PyQt Signals 정의 (Backend의 callback과 1:1 대응)
    connected = pyqtSignal(bool)
    account_update = pyqtSignal(dict)
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)
    order_placed = pyqtSignal(dict)
    order_filled = pyqtSignal(dict)
    order_cancelled = pyqtSignal(dict)
    order_error = pyqtSignal(str, str)
    positions_update = pyqtSignal(list)
    
    def __init__(self, connector: "IBKRConnector", parent=None):
        super().__init__(parent)
        self._connector = connector
        self._register_callbacks()
    
    def _register_callbacks(self) -> None:
        """IBKRConnector에 callback 등록"""
        self._connector.set_on_connected(self._on_connected)
        self._connector.set_on_account_update(self._on_account_update)
        # ... 나머지 callback 등록
    
    def _on_connected(self, is_connected: bool) -> None:
        """Callback → Signal 변환"""
        self.connected.emit(is_connected)
    
    # 편의 메서드
    def start(self) -> None:
        self._connector.start()
    
    def stop(self) -> None:
        self._connector.stop()
```

### 사용 패턴

```python
# DI Container에서 connector 가져오기
from backend.container import container
connector = container.ibkr_connector()

# Adapter 생성
from frontend.services.ibkr_adapter import IBKREventAdapter
adapter = IBKREventAdapter(connector)

# GUI에서 Signal 연결 (기존 패턴 그대로 유지)
adapter.connected.connect(self._on_connection_changed)
adapter.account_update.connect(self._on_account_update)
adapter.error.connect(self._on_error)

# 연결 시작
adapter.start()
```

---

## Step 3.0: GUI 연결 포인트 업데이트

### 분석 결과

Frontend 코드베이스 검색 결과:
- `dashboard.py`: IBKRConnector 직접 import 없음
- `frontend/` 전체: IBKRConnector 직접 참조 없음
- DI Container (`backend/container.py`)를 통해서만 접근

**결론: 변경 불필요 (N/A)**

---

## Step 4.0: 검증

### 레이어 분리 확인

```powershell
# Backend에서 PyQt6 import 검색
Get-ChildItem -Path backend -Filter *.py -Recurse | Select-String -Pattern "from PyQt6"
# 결과: 0건 ✅
```

### DI 패턴 검증

```powershell
# get_*_instance 싱글톤 패턴 검색
Get-ChildItem -Path backend -Filter *.py -Recurse | Select-String -Pattern "get_.*_instance"
# 결과: container.py 주석에서만 발견 (실제 사용 없음) ✅
```

### Ruff 검증

```bash
ruff check backend/broker/ibkr_connector.py frontend/services/ibkr_adapter.py
# All checks passed! ✅

ruff format backend/broker/ibkr_connector.py frontend/services/ibkr_adapter.py
# 1 file reformatted ✅
```

---

## 롤백 지침

문제 발생 시:
```bash
git revert HEAD
# 또는 특정 커밋
git revert <commit-hash>
```

### 주요 변경점 복원 시 주의사항

1. **IBKRConnector**: `QThread` 상속 복원, `pyqtSignal` 재선언
2. **Signal emit**: `self._emit_*()` → `self.signal.emit()` 복원
3. **Threading**: `threading.Thread` → `QThread` 복원
4. **ibkr_adapter.py**: 삭제 가능 (Frontend에서 직접 사용 없음)

---

## 요약

| 항목 | Before | After |
|------|--------|-------|
| 클래스 상속 | `QThread` | 순수 Python |
| 이벤트 방식 | `pyqtSignal` | Callback 함수 |
| 스레드 관리 | `QThread.start()` | `threading.Thread` |
| Sleep | `QThread.msleep(ms)` | `time.sleep(sec)` |
| Wait | `self.wait(ms)` | `thread.join(timeout)` |
| PyQt6 의존성 | ✅ 있음 | ❌ 없음 |

---

## /IMP-verification 결과

| 항목 | 결과 |
|------|------|
| lint-imports | ⚠️ 미설정 (ruff 대체) |
| PyQt6 import in backend/ | ✅ 0건 |
| get_*_instance 패턴 | ✅ 실사용 0건 |
| ruff check | ✅ All checks passed |
| ruff format | ✅ 적용 완료 |
| _index.md 업데이트 | ✅ ibkr_adapter.py 추가 |
| full_log_history.md | ✅ 항목 추가 |
