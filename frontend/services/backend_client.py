"""
Sigma9 Backend Client (Refactored)
===================================
HTTP/WebSocket 기반 Backend 통신 클라이언트.

📌 변경사항 (Step 4.2):
    - 기존: 직접 Python import (IBKRConnector, Scanner 등)
    - 변경: RestAdapter + WsAdapter 사용

📌 사용법:
    from frontend.services.backend_client import BackendClient
    
    client = BackendClient.instance()
    await client.connect()
    await client.start_engine()
"""

import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from loguru import logger

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    PYQT_AVAILABLE = True
except ImportError:
    try:
        from PySide6.QtCore import QObject, Signal as pyqtSignal
        PYQT_AVAILABLE = True
    except ImportError:
        PYQT_AVAILABLE = False

from frontend.services.rest_adapter import RestAdapter, ServerStatus
from frontend.services.ws_adapter import WsAdapter


class ConnectionState(Enum):
    """연결 상태"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STARTING = "starting"   # Engine starting
    RUNNING = "running"     # Engine running
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class WatchlistItem:
    """Watchlist 항목"""
    ticker: str
    score: float
    score_v2: float = 0.0  # [02-001] v2 연속 점수
    stage: str = ""
    last_close: float = 0.0
    change_pct: float = 0.0
    avg_volume: float = 0.0  # [4.A.4] DolVol 계산용
    # [Issue 01-003] 추가 필드
    dollar_volume: float = 0.0
    price: float = 0.0
    volume: float = 0.0
    stage_number: int = 0
    source: str = ""
    
    def to_display_string(self) -> str:
        """표시용 문자열 생성"""
        sign = "+" if self.change_pct >= 0 else ""
        return f"{self.ticker:6s} {sign}{self.change_pct:.1f}%  [{self.score:.0f}]"
    
    @classmethod
    def from_dict(cls, data: dict) -> "WatchlistItem":
        """딕셔너리에서 생성"""
        return cls(
            ticker=data.get("ticker", ""),
            score=data.get("score", 0),
            score_v2=data.get("score_v2", 0.0),  # [02-001] v2 점수 파싱
            stage=data.get("stage", ""),
            last_close=data.get("last_close", 0),
            change_pct=data.get("change_pct", 0),
            avg_volume=data.get("avg_volume", 0),
            # [Issue 01-003] 추가 필드 파싱
            dollar_volume=data.get("dollar_volume", 0),
            price=data.get("price", 0),
            volume=data.get("volume", 0),
            stage_number=data.get("stage_number", 0),
            source=data.get("source", ""),
        )


class BackendClient(QObject):
    """
    Backend 서비스 통합 클라이언트 (리팩토링됨)
    
    📌 기능:
        - 서버 연결/해제 (HTTP + WebSocket)
        - 엔진 제어 (start/stop/kill)
        - 실시간 데이터 수신 (WebSocket)
        - 초기 상태 동기화
    
    📌 Signals:
        - connected(bool): 연결 상태 변경
        - state_changed(ConnectionState): 상태 변경
        - error_occurred(str): 에러 발생
        - log_message(str): 로그 메시지
        - watchlist_updated(list): Watchlist 업데이트
        - positions_updated(list): 포지션 업데이트
    """
    
    _instance = None
    
    # Signals
    connected = pyqtSignal(bool)
    state_changed = pyqtSignal(object)  # ConnectionState
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    watchlist_updated = pyqtSignal(list)
    positions_updated = pyqtSignal(list)
    ignition_updated = pyqtSignal(dict)  # {"ticker": str, "score": float, "passed_filter": bool}
    bar_received = pyqtSignal(dict)  # Phase 4.A.0: {"ticker": str, "timeframe": str, "bar": dict}
    tick_received = pyqtSignal(dict)  # Phase 4.A.0.b: {"ticker": str, "price": float, "volume": int}
    
    @classmethod
    def instance(cls):
        """싱글톤 인스턴스 반환"""
        if not cls._instance:
            cls._instance = BackendClient()
        return cls._instance
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        parent=None
    ):
        """
        BackendClient 초기화
        
        Args:
            host: 서버 호스트
            port: 서버 포트
            parent: Qt 부모 객체
        """
        if BackendClient._instance and hasattr(BackendClient._instance, '_initialized'):
            return
        
        super().__init__(parent)
        self._initialized = True
        
        self.host = host
        self.port = port
        self.state = ConnectionState.DISCONNECTED
        
        # Adapters
        self._base_url = f"http://{host}:{port}"
        self._ws_url = f"ws://{host}:{port}/ws/feed"
        
        self.rest = RestAdapter(self._base_url)
        self.ws = WsAdapter(self._ws_url)
        
        # WebSocket Signal 연결
        self.ws.connected.connect(self._on_ws_connected)
        self.ws.disconnected.connect(self._on_ws_disconnected)
        self.ws.log_received.connect(self.log_message.emit)
        self.ws.watchlist_updated.connect(self._on_watchlist_updated)
        self.ws.status_changed.connect(self._on_status_changed)
        self.ws.error_occurred.connect(self.error_occurred.emit)
        
        # Ignition 시그널 연결 (존재하는 경우)
        if hasattr(self.ws, 'ignition_updated'):
            self.ws.ignition_updated.connect(self.ignition_updated.emit)
        
        # Phase 4.A.0: Bar 시그널 연결 (실시간 차트용)
        if hasattr(self.ws, 'bar_received'):
            self.ws.bar_received.connect(self.bar_received.emit)
        
        # Phase 4.A.0.b: Tick 시그널 연결 (실시간 가격 표시)
        if hasattr(self.ws, 'tick_received'):
            self.ws.tick_received.connect(self.tick_received.emit)
        
        logger.info(f"BackendClient initialized: {self._base_url}")
    
    def set_server(self, host: str, port: int):
        """
        서버 주소 변경 (로컬/AWS 전환용)
        
        Args:
            host: 새 서버 호스트 (예: "localhost" 또는 "ec2-xxx.amazonaws.com")
            port: 새 서버 포트
        """
        self.host = host
        self.port = port
        self._base_url = f"http://{host}:{port}"
        self._ws_url = f"ws://{host}:{port}/ws/feed"
        
        # Adapters 재생성
        self.rest = RestAdapter(self._base_url)
        self.ws = WsAdapter(self._ws_url)
        
        # WebSocket Signal 재연결
        self.ws.connected.connect(self._on_ws_connected)
        self.ws.disconnected.connect(self._on_ws_disconnected)
        self.ws.log_received.connect(self.log_message.emit)
        self.ws.watchlist_updated.connect(self._on_watchlist_updated)
        self.ws.status_changed.connect(self._on_status_changed)
        self.ws.error_occurred.connect(self.error_occurred.emit)
        
        self.log_message.emit(f"🔄 Server changed to: {self._base_url}")
        logger.info(f"Server changed to: {self._base_url}")
    
    def _set_state(self, state: ConnectionState):
        """상태 변경 및 Signal 발생"""
        if self.state != state:
            self.state = state
            self.state_changed.emit(state)
            logger.debug(f"State changed: {state.value}")
    
    # ─────────────────────────────────────────────────────────────
    # Background Event Loop (영구 이벤트 루프)
    # ─────────────────────────────────────────────────────────────
    
    _bg_loop = None
    _bg_thread = None
    
    @classmethod
    def _get_event_loop(cls):
        """
        백그라운드 스레드에서 실행되는 영구 이벤트 루프 반환
        
        매번 새 루프를 생성/종료하면 httpx.AsyncClient에서 문제가 발생하므로
        하나의 영구 루프를 백그라운드 스레드에서 유지합니다.
        """
        import threading
        import asyncio
        
        if cls._bg_loop is None or not cls._bg_loop.is_running():
            cls._bg_loop = asyncio.new_event_loop()
            
            def run_loop():
                asyncio.set_event_loop(cls._bg_loop)
                cls._bg_loop.run_forever()
            
            cls._bg_thread = threading.Thread(target=run_loop, daemon=True)
            cls._bg_thread.start()
        
        return cls._bg_loop
    
    def _run_async(self, coro):
        """
        코루틴을 백그라운드 이벤트 루프에서 실행하고 결과를 동기적으로 대기
        """
        import asyncio
        loop = self._get_event_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=30)  # 30초 타임아웃
    
    # ─────────────────────────────────────────────────────────────
    # Synchronous Wrappers (PyQt 호출용)
    # ─────────────────────────────────────────────────────────────
    
    def connect_sync(self) -> bool:
        """
        동기 연결 메서드 (PyQt 콜백에서 사용)
        """
        try:
            # 이미 연결된 경우
            if self.state in (ConnectionState.CONNECTED, ConnectionState.RUNNING):
                return True
            
            return self._run_async(self.connect())
        except Exception as e:
            logger.error(f"connect_sync failed: {e}")
            self.log_message.emit(f"❌ Connection failed: {e}")
            self._set_state(ConnectionState.ERROR)
            return False
    
    def disconnect_sync(self):
        """동기 연결 해제 메서드"""
        try:
            self._run_async(self.disconnect())
        except Exception as e:
            logger.error(f"disconnect_sync failed: {e}")
    
    def start_engine_sync(self):
        """동기 엔진 시작"""
        try:
            self._run_async(self.start_engine())
        except Exception as e:
            logger.error(f"start_engine_sync failed: {e}")
            self.log_message.emit(f"❌ Engine start failed: {e}")
    
    def stop_engine_sync(self):
        """동기 엔진 정지"""
        try:
            self._run_async(self.stop_engine())
        except Exception as e:
            logger.error(f"stop_engine_sync failed: {e}")
    
    def kill_switch_sync(self):
        """동기 킬 스위치"""
        try:
            self._run_async(self.kill_switch())
        except Exception as e:
            logger.error(f"kill_switch_sync failed: {e}")
            self.log_message.emit(f"❌ Kill switch failed: {e}")
    
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
    
    # ─────────────────────────────────────────────────────────────
    # Connection Management
    # ─────────────────────────────────────────────────────────────
    
    async def connect(self) -> bool:
        """
        서버 연결
        
        1. REST API 헬스체크
        2. WebSocket 연결
        3. 초기 상태 동기화
        
        Returns:
            bool: 연결 성공 여부
        """
        if self.state == ConnectionState.CONNECTED or self.state == ConnectionState.RUNNING:
            return True
        
        self._set_state(ConnectionState.CONNECTING)
        self.log_message.emit(f"🔌 Connecting to {self._base_url}...")
        
        try:
            # 1. REST API 헬스체크
            if not await self.rest.health_check():
                self.log_message.emit("❌ Server health check failed")
                self._set_state(ConnectionState.ERROR)
                return False
            
            # 2. WebSocket 연결
            if not await self.ws.connect():
                self.log_message.emit("❌ WebSocket connection failed")
                self._set_state(ConnectionState.ERROR)
                return False
            
            # 3. 초기 상태 동기화
            await self.sync_initial_state()
            
            self._set_state(ConnectionState.CONNECTED)
            self.connected.emit(True)
            self.log_message.emit("✅ Connected to server")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._set_state(ConnectionState.ERROR)
            self.error_occurred.emit(str(e))
            return False
    
    async def disconnect(self):
        """서버 연결 해제"""
        await self.ws.disconnect()
        await self.rest.close()
        self._set_state(ConnectionState.DISCONNECTED)
        self.connected.emit(False)
        self.log_message.emit("📡 Disconnected from server")
    
    def is_connected(self) -> bool:
        """연결 상태 반환"""
        return self.state in (ConnectionState.CONNECTED, ConnectionState.RUNNING)
    
    # ─────────────────────────────────────────────────────────────
    # State Sync
    # ─────────────────────────────────────────────────────────────
    
    async def sync_initial_state(self):
        """
        연결 후 초기 상태 동기화
        
        서버에서 현재 상태, Watchlist, 포지션을 가져와서
        GUI에 반영합니다.
        """
        self.log_message.emit("🔄 Syncing initial state...")
        
        try:
            # 1. 서버 상태 조회
            status = await self.rest.get_status()
            if status:
                self._update_state_from_server(status)
            
            # 2. Watchlist 조회
            watchlist_data = await self.rest.get_watchlist()
            if watchlist_data:
                items = [WatchlistItem.from_dict(item) for item in watchlist_data]
                self.watchlist_updated.emit(items)
                self.log_message.emit(f"📋 Watchlist loaded: {len(items)} items")
            
            # 3. 포지션 조회
            positions = await self.rest.get_positions()
            if positions:
                self.positions_updated.emit(positions)
                self.log_message.emit(f"📊 Positions loaded: {len(positions)} items")
            
        except Exception as e:
            logger.error(f"State sync failed: {e}")
            self.log_message.emit(f"⚠️ State sync partial failure: {e}")
    
    def _update_state_from_server(self, status: ServerStatus):
        """서버 상태를 클라이언트 상태에 반영"""
        if status.engine == "running":
            self._set_state(ConnectionState.RUNNING)
        elif status.engine == "stopped" and self.state != ConnectionState.RUNNING:
            self._set_state(ConnectionState.CONNECTED)
    
    # ─────────────────────────────────────────────────────────────
    # Engine Control
    # ─────────────────────────────────────────────────────────────
    
    async def start_engine(self):
        """Trading Engine 시작"""
        if self.state != ConnectionState.CONNECTED:
            self.log_message.emit("⚠️ Cannot start engine: Not connected")
            return
        
        self._set_state(ConnectionState.STARTING)
        self.log_message.emit("🚀 Starting Trading Engine...")
        
        result = await self.rest.start_engine()
        
        if result.get("status") == "accepted":
            self._set_state(ConnectionState.RUNNING)
            self.log_message.emit("✅ Trading Engine Started")
        else:
            self._set_state(ConnectionState.CONNECTED)
            msg = result.get("message", "Unknown error")
            self.log_message.emit(f"❌ Engine start failed: {msg}")
    
    async def stop_engine(self):
        """Trading Engine 정지"""
        if self.state != ConnectionState.RUNNING:
            self.log_message.emit("⚠️ Engine is not running")
            return
        
        self._set_state(ConnectionState.STOPPING)
        self.log_message.emit("⏹ Stopping Trading Engine...")
        
        result = await self.rest.stop_engine()
        
        if result.get("status") == "accepted":
            self._set_state(ConnectionState.CONNECTED)
            self.log_message.emit("✅ Trading Engine Stopped")
        else:
            msg = result.get("message", "Unknown error")
            self.log_message.emit(f"❌ Engine stop failed: {msg}")
    
    async def kill_switch(self):
        """
        긴급 정지 (Kill Switch)
        
        모든 주문 취소 + 모든 포지션 청산 + 엔진 정지
        """
        self.log_message.emit("⚡ KILL SWITCH ACTIVATED!")
        
        result = await self.rest.kill_switch()
        
        if result.get("status") == "accepted":
            self._set_state(ConnectionState.CONNECTED)
            self.log_message.emit("⚡ Kill switch executed: All systems stopped")
        else:
            msg = result.get("message", "Unknown error")
            self.log_message.emit(f"❌ Kill switch failed: {msg}")
            self.error_occurred.emit(f"Kill switch failed: {msg}")
    
    # ─────────────────────────────────────────────────────────────
    # Watchlist / Scanner
    # ─────────────────────────────────────────────────────────────
    
    async def run_scanner(self, strategy_name: str = "seismograph"):
        """
        Scanner 실행 요청
        
        서버의 /api/scanner/run 엔드포인트를 호출하여
        지정된 전략으로 시장 스캔을 실행합니다.
        """
        self.log_message.emit(f"🔍 Running scanner: {strategy_name}...")
        
        result = await self.rest.run_scanner(strategy_name)
        
        if result.get("status") == "success":
            item_count = result.get("item_count", 0)
            self.log_message.emit(f"✅ Scanner complete: {item_count} stocks found")
            
            # Watchlist 새로고침
            await self.refresh_watchlist()
        else:
            msg = result.get("message", "Unknown error")
            self.log_message.emit(f"❌ Scanner failed: {msg}")
    
    async def refresh_watchlist(self):
        """Watchlist 새로고침"""
        watchlist_data = await self.rest.get_watchlist()
        if watchlist_data:
            items = [WatchlistItem.from_dict(item) for item in watchlist_data]
            self.watchlist_updated.emit(items)
            self.log_message.emit(f"📋 Watchlist refreshed: {len(items)} items")
    
    # ─────────────────────────────────────────────────────────────
    # Strategy Management
    # ─────────────────────────────────────────────────────────────
    
    async def get_strategies(self) -> list:
        """전략 목록 조회"""
        return await self.rest.get_strategies()
    
    async def reload_strategy(self, name: str):
        """전략 리로드"""
        self.log_message.emit(f"🔄 Reloading strategy: {name}")
        
        result = await self.rest.reload_strategy(name)
        
        if result.get("status") == "reloaded":
            self.log_message.emit(f"✅ Strategy reloaded: {name}")
        else:
            msg = result.get("message", "Unknown error")
            self.log_message.emit(f"❌ Reload failed: {msg}")
    
    # ─────────────────────────────────────────────────────────────
    # WebSocket Signal Handlers
    # ─────────────────────────────────────────────────────────────
    
    def _on_ws_connected(self):
        """WebSocket 연결 성공"""
        logger.debug("WebSocket connected callback")
    
    def _on_ws_disconnected(self):
        """WebSocket 연결 해제"""
        if self.state not in (ConnectionState.DISCONNECTED, ConnectionState.CONNECTING):
            self._set_state(ConnectionState.DISCONNECTED)
            self.connected.emit(False)
            self.log_message.emit("⚠️ WebSocket disconnected - attempting reconnect...")
    
    def _on_watchlist_updated(self, items: list):
        """Watchlist 업데이트 수신"""
        watchlist = [WatchlistItem.from_dict(item) if isinstance(item, dict) else item for item in items]
        self.watchlist_updated.emit(watchlist)
    
    def _on_status_changed(self, status_data: dict):
        """서버 상태 변경 수신"""
        event = status_data.get("event", "")
        
        if event == "engine_started":
            self._set_state(ConnectionState.RUNNING)
            self.log_message.emit("🚀 Engine started (server notification)")
        elif event == "engine_stopped":
            self._set_state(ConnectionState.CONNECTED)
            self.log_message.emit("⏹ Engine stopped (server notification)")
