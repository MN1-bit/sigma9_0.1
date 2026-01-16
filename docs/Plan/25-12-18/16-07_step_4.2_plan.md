# Step 4.2: Frontend Integration (Client Adapter) 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 4 (Intelligence & Refinement)  
> **목표**: Backend 직접 import 방식 → HTTP/WebSocket 통신 방식으로 전환

---

## 1. 배경 및 목적

### 📌 현재 문제점

현재 `BackendClient`는 다음과 같이 **직접 Python import** 방식으로 Backend 모듈을 사용:

```python
# frontend/services/backend_client.py
from backend.broker.ibkr_connector import IBKRConnector
from backend.core.scanner import Scanner, run_scan
from backend.data.database import MarketDB
```

**문제점**:
- GUI와 Backend가 동일 Python 프로세스에서 실행되어야 함
- AWS 배포 시 GUI(로컬) ↔ Backend(AWS) 분리 불가능
- Step 4.1에서 구축한 REST API/WebSocket이 활용되지 않음

### 🎯 목표

1. `BackendClient`를 `RestAdapter` + `WsAdapter`로 교체
2. Settings Dialog를 탭 구조로 개편 (Connection, Backend, Theme)
3. GUI가 원격 서버와 통신하도록 검증

---

## 2. 요구사항 (development_steps.md)

| Step | Description |
|------|-------------|
| 4.2.1 | BackendClient Refactor: `RestAdapter` + `WsAdapter` |
| 4.2.2 | State Sync: 연결 시 초기 상태 동기화 |
| 4.2.3 | Settings Dialog Restructure: 3개 탭 (Connection, Backend, Theme) |
| 4.2.4 | Verify Decoupling: localhost 원격 서버 테스트 |
| 4.2.5 | Tabbed Right Panel: Oracle 탭 추가 |

### 4.2.3 Settings Dialog 서브스탭 상세

| Sub-step | Description | 세부 항목 |
|----------|-------------|----------|
| **4.2.3.1** | Create `QTabWidget` structure | 3개 탭: Connection, Backend, Theme |
| **4.2.3.2** | **Theme Tab** | Window Opacity, Acrylic Alpha, Particle Opacity, Tint Color, Background Effect (기존 항목 마이그레이션) |
| **4.2.3.3** | **Connection Tab** | Server Host/Port, Auto-connect toggle, Reconnect interval, Timeout settings |
| **4.2.3.4** | **Backend Tab** | Market Open Scan toggle, Scan offset minutes, Daily Data Update toggle, Update time picker |

---

## 3. Proposed Changes

### 3.1 BackendClient Refactor (4.2.1)

#### [NEW] `frontend/services/rest_adapter.py`

HTTP 기반 REST API 클라이언트.

```python
class RestAdapter:
    """REST API 클라이언트"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url  # e.g., "http://localhost:8000/api"
        self.client = httpx.AsyncClient()
    
    async def get_status(self) -> dict:
        """GET /api/status"""
        ...
    
    async def control_engine(self, command: str) -> dict:
        """POST /api/control"""
        ...
    
    async def get_watchlist(self) -> list:
        """GET /api/watchlist"""
        ...
    
    async def kill_switch(self) -> dict:
        """POST /api/kill-switch"""
        ...
```

---

#### [NEW] `frontend/services/ws_adapter.py`

WebSocket 기반 실시간 스트리밍 클라이언트.

```python
class WsAdapter(QObject):
    """WebSocket 클라이언트"""
    
    # Signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    tick_received = pyqtSignal(dict)
    trade_received = pyqtSignal(dict)
    watchlist_updated = pyqtSignal(list)
    log_received = pyqtSignal(str)
    
    def __init__(self, ws_url: str):
        self.ws_url = ws_url  # e.g., "ws://localhost:8000/ws/feed"
    
    async def connect(self):
        """WebSocket 연결"""
        ...
    
    async def disconnect(self):
        """연결 해제"""
        ...
    
    def _handle_message(self, message: str):
        """메시지 파싱 및 Signal 발생"""
        # LOG:xxx → log_received.emit(xxx)
        # TICK:xxx → tick_received.emit(json.loads(xxx))
        ...
```

---

#### [MODIFY] `frontend/services/backend_client.py`

기존 직접 import 제거, `RestAdapter` + `WsAdapter` 사용.

```python
class BackendClient(QObject):
    """리팩토링된 Backend 클라이언트"""
    
    def __init__(self, config: ClientConfig):
        # 기존: IBKRConnector 직접 생성
        # 변경: Adapter 사용
        self.rest = RestAdapter(f"http://{config.server.host}:{config.server.port}/api")
        self.ws = WsAdapter(f"ws://{config.server.host}:{config.server.port}/ws/feed")
        
        # Signal 연결
        self.ws.log_received.connect(self.log_message.emit)
        self.ws.watchlist_updated.connect(self.watchlist_updated.emit)
    
    async def connect(self):
        """서버 연결 (REST 헬스체크 → WebSocket 연결)"""
        status = await self.rest.get_status()
        await self.ws.connect()
        ...
```

---

### 3.2 State Sync (4.2.2)

#### [MODIFY] `frontend/services/backend_client.py`

연결 시 초기 상태 동기화.

```python
async def sync_initial_state(self):
    """연결 후 초기 상태 동기화"""
    # 1. 서버 상태 조회
    status = await self.rest.get_status()
    self._update_state_from_server(status)
    
    # 2. Watchlist 조회
    watchlist = await self.rest.get_watchlist()
    self.watchlist_updated.emit(watchlist)
    
    # 3. 포지션 조회
    positions = await self.rest.get_positions()
    self.positions_updated.emit(positions)
```

---

### 3.3 Settings Dialog Restructure (4.2.3)

#### [MODIFY] `frontend/gui/settings_dialog.py`

기존 단일 레이아웃 → `QTabWidget` 구조로 전환.

**탭 구조:**

| 탭 | 항목 |
|---|------|
| **Connection** | Server Host, Port, Auto-connect, Reconnect interval, Timeout |
| **Backend** | Market Open Scan toggle, Offset minutes, Daily Data Update, Update time |
| **Theme** | Window Opacity, Acrylic Alpha, Particle Opacity, Tint Color, Background Effect |

```python
class SettingsDialog(QDialog):
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # QTabWidget 생성
        self.tab_widget = QTabWidget()
        
        # 탭 추가
        self.tab_widget.addTab(self._create_connection_tab(), "Connection")
        self.tab_widget.addTab(self._create_backend_tab(), "Backend")
        self.tab_widget.addTab(self._create_theme_tab(), "Theme")
        
        layout.addWidget(self.tab_widget)
        layout.addLayout(self._create_button_row())
    
    def _create_connection_tab(self) -> QWidget:
        """Connection 탭 생성"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Server Host
        self.host_edit = QLineEdit(self.settings.get('server_host', 'localhost'))
        layout.addRow("Server Host:", self.host_edit)
        
        # Server Port
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.settings.get('server_port', 8000))
        layout.addRow("Server Port:", self.port_spin)
        
        # Auto-connect
        self.auto_connect_check = QCheckBox("Enable")
        self.auto_connect_check.setChecked(self.settings.get('auto_connect', True))
        layout.addRow("Auto Connect:", self.auto_connect_check)
        
        # Reconnect Interval
        self.reconnect_spin = QSpinBox()
        self.reconnect_spin.setRange(1, 60)
        self.reconnect_spin.setValue(self.settings.get('reconnect_interval', 5))
        layout.addRow("Reconnect Interval (s):", self.reconnect_spin)
        
        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(self.settings.get('timeout', 30))
        layout.addRow("Timeout (s):", self.timeout_spin)
        
        return widget
    
    def _create_backend_tab(self) -> QWidget:
        """Backend 탭 생성"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Market Open Scan
        self.market_scan_check = QCheckBox("Enable")
        self.market_scan_check.setChecked(self.settings.get('market_open_scan', True))
        layout.addRow("Market Open Scan:", self.market_scan_check)
        
        # Scan Offset
        self.scan_offset_spin = QSpinBox()
        self.scan_offset_spin.setRange(0, 60)
        self.scan_offset_spin.setValue(self.settings.get('scan_offset_minutes', 15))
        layout.addRow("Scan Offset (min):", self.scan_offset_spin)
        
        # Daily Data Update
        self.daily_update_check = QCheckBox("Enable")
        self.daily_update_check.setChecked(self.settings.get('daily_data_update', True))
        layout.addRow("Daily Data Update:", self.daily_update_check)
        
        # Update Time
        self.update_time_edit = QTimeEdit()
        self.update_time_edit.setTime(QTime(16, 30))
        layout.addRow("Update Time (ET):", self.update_time_edit)
        
        return widget
    
    def _create_theme_tab(self) -> QWidget:
        """Theme 탭 생성 - 기존 설정 항목 이동"""
        # 기존 _init_ui 코드 마이그레이션
        ...
```

---

### 3.4 Right Panel Oracle Tab (4.2.5)

#### [MODIFY] `frontend/gui/dashboard.py`

Right Panel을 `QTabWidget`으로 변경.

```python
def _create_right_panel(self) -> QWidget:
    """Right Panel (탭 구조)"""
    panel = QWidget()
    layout = QVBoxLayout(panel)
    
    # QTabWidget 생성
    self.right_tabs = QTabWidget()
    
    # Trading 탭 (기존)
    self.right_tabs.addTab(self._create_trading_tab(), "Trading")
    
    # Oracle 탭 (신규 - Step 4.4에서 구현)
    self.oracle_placeholder = QLabel("Oracle Panel\n(Coming in Step 4.4)")
    self.oracle_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.right_tabs.addTab(self.oracle_placeholder, "Oracle")
    
    layout.addWidget(self.right_tabs)
    return panel
```

---

## 4. 변경 파일 요약

| 상태 | 파일 | 설명 |
|------|------|------|
| 🆕 NEW | `frontend/services/rest_adapter.py` | REST API 클라이언트 |
| 🆕 NEW | `frontend/services/ws_adapter.py` | WebSocket 클라이언트 |
| ✏️ MODIFY | `frontend/services/backend_client.py` | Adapter 기반으로 리팩토링 |
| ✏️ MODIFY | `frontend/gui/settings_dialog.py` | 탭 구조 개편 |
| ✏️ MODIFY | `frontend/gui/dashboard.py` | Right Panel 탭 추가 |

---

## 5. 의존성 확인

이미 `requirements.txt`에 포함된 패키지 사용:
- `httpx` - REST API 클라이언트
- `websockets` - WebSocket 클라이언트
- `qasync` - PyQt + asyncio 통합

---

## 6. Verification Plan

### 6.1 수동 검증

#### Step 1: 서버 실행

```powershell
# 터미널 1: Backend 서버 시작
cd D:\Codes\Sigma9-0.1
.venv\Scripts\python -m backend
```

#### Step 2: GUI 실행 및 연결 테스트

```powershell
# 터미널 2: GUI 시작
cd D:\Codes\Sigma9-0.1
.venv\Scripts\python -m frontend.main
```

**확인 항목:**
1. GUI 시작 시 서버 자동 연결 (상태 표시기 🟢)
2. Settings Dialog에서 3개 탭 확인 (Connection, Backend, Theme)
3. Engine Start 버튼 클릭 → 서버 API 호출 확인
4. Watchlist 패널에 데이터 표시 확인

#### Step 3: Decoupling 검증

1. 서버 종료 → GUI 상태 표시기 🔴 변경 확인
2. 서버 재시작 → GUI 자동 재연결 확인

---

## 7. 위험 요소 및 대응

| 위험 | 확률 | 대응 |
|------|------|------|
| 기존 GUI 기능 중단 | 중 | 단계적 마이그레이션, 각 단계별 테스트 |
| WebSocket 연결 불안정 | 저 | 자동 재연결 로직 구현 |
| asyncio/Qt 통합 이슈 | 중 | `qasync` 라이브러리 활용 |

---

## 8. 구현 순서

1. **4.2.1**: `RestAdapter` + `WsAdapter` 생성
2. **4.2.2**: `BackendClient` 리팩토링 + State Sync
3. **4.2.3**: Settings Dialog 탭 구조 개편
4. **4.2.4**: 통합 테스트 (GUI ↔ 서버)
5. **4.2.5**: Right Panel Oracle 탭 (Placeholder)

---

> **"Architecture First"**: 기능 추가 전 구조를 바로잡아 기술 부채 방지
