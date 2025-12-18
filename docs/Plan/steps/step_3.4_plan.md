# Step 3.4: GUI Control Panel 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 3 (Execution & Management)  
> **목표**: 트레이딩 컨트롤 패널 UI 및 Scanner 자동화

---

## 1. 배경 및 목적

`masterplan.md` Section 14에 정의된 **Control Panel**을 구현합니다.

**주요 변경:**
- ~~IBKR 연결~~ → **Backend 연결** (WebSocket/REST)
- GUI 실행 시 **자동 연결**
- 전략 선택 시 **Scanner 자동 실행**
- Scanner 결과 → **Watchlist 자동 업데이트**

---

## 2. 요구사항

### 2.1 기존 (development_steps.md)

| Step | Description |
|------|-------------|
| 3.4.1 | Connect/Disconnect button |
| 3.4.2 | Boot/Shutdown Engine buttons |
| 3.4.3 | Strategy Reload button |
| 3.4.4 | Connection status indicator (🔴🟡🟠🟢) |
| 3.4.5 | Loading overlay for async operations |

### 2.2 추가 요구사항 (신규)

| Step | Description |
|------|-------------|
| 3.4.6 | GUI 시작 시 Backend 자동 연결 |
| 3.4.7 | 전략 선택/변경 시 Scanner 자동 실행 |
| 3.4.8 | Scanner 결과 → Watchlist 자동 업데이트 |

---

## 3. 현재 문제점

### 문제 1: Scanner 미실행
- 전략을 `seismograph`로 변경해도 Scanner가 자동으로 시작하지 않음
- 수동으로 Scanner를 실행해야 함

### 문제 2: Watchlist 미갱신
- Scanner가 실행되더라도 결과가 Watchlist 패널에 반영되지 않음
- GUI와 Scanner 간의 Signal 연결 누락

---

## 4. Proposed Changes

### 4.1 Backend Connection

#### [NEW] [backend_client.py](file:///d:/Codes/Sigma9-0.1/frontend/services/backend_client.py)

```python
class BackendClient:
    """Backend WebSocket/REST 클라이언트"""
    
    def __init__(self, host, port):
        self.ws = None
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Backend 연결 (GUI 시작 시 자동 호출)"""
        ...
    
    async def disconnect(self):
        """연결 해제"""
        ...
```

### 4.2 Auto-Connect on Startup

#### [MODIFY] [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py)

```python
def __init__(self):
    ...
    # GUI 시작 시 자동 연결
    QTimer.singleShot(500, self._auto_connect_backend)

def _auto_connect_backend(self):
    """Backend 자동 연결"""
    self.backend_client.connect()
```

### 4.3 Scanner Auto-Start

#### [MODIFY] [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py)

```python
def on_strategy_changed(self, strategy_name: str):
    """전략 변경 시 Scanner 자동 시작"""
    self.strategy_loader.load_strategy(strategy_name)
    self.scanner.start(strategy_name)  # ← 추가
```

### 4.4 Watchlist Auto-Update

#### [MODIFY] Scanner ↔ Watchlist Signal 연결

```python
# Scanner Signal 연결
self.scanner.watchlist_updated.connect(self.watchlist_panel.update_items)
```

### 4.5 Control Panel Widget

#### [NEW] [control_panel.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/control_panel.py)

| Widget | Action |
|--------|--------|
| `ConnectButton` | Backend 연결/해제 |
| `StartBotButton` | Trading Engine 시작 |
| `StopBotButton` | Trading Engine 중지 |
| `KillSwitchButton` | 긴급 청산 |
| `StatusIndicator` | 🔴🟡🟠🟢 |

**상태 인디케이터:**

| Color | State |
|-------|-------|
| 🔴 | Disconnected |
| 🟡 | Connecting... |
| 🟠 | Connected (Engine Off) |
| 🟢 | Running (Active) |

---

## 5. Verification Plan

```powershell
# 테스트 실행
pytest tests/test_control_panel.py -v

# GUI 실행 후 확인 항목:
# 1. 자동 Backend 연결
# 2. 전략 선택 시 Scanner 시작
# 3. Watchlist 자동 업데이트
```

---

## 5.5 Bugfix: Scanner Import Error

### 문제

```
[ERROR] Scanner module not found: cannot import name 'ScannerOrchestrator' 
from 'backend.core.scanner'
```

### 원인

- `backend_client.py`에서 `ScannerOrchestrator`를 import하려고 했으나
- 실제 클래스 이름은 `Scanner`임

### 해결

#### [MODIFY] [backend_client.py](file:///d:/Codes/Sigma9-0.1/frontend/services/backend_client.py)

```python
# Before
from backend.core.scanner import ScannerOrchestrator

# After
from backend.core.scanner import Scanner
```

---

## 6. 다음 단계

- **Phase 4**: Intelligence & Refinement
