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
    stage: str
    last_close: float = 0.0
    change_pct: float = 0.0
    
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
            stage=data.get("stage", ""),
            last_close=data.get("last_close", 0),
            change_pct=data.get("change_pct", 0)
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
        
        logger.info(f"BackendClient initialized: {self._base_url}")
    
    def _set_state(self, state: ConnectionState):
        """상태 변경 및 Signal 발생"""
        if self.state != state:
            self.state = state
            self.state_changed.emit(state)
            logger.debug(f"State changed: {state.value}")
    
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
        
        Note: 실제 스캔은 서버에서 수행됨.
              여기서는 스케줄러 트리거만 요청.
        """
        self.log_message.emit(f"🔍 Requesting scan for {strategy_name}...")
        
        # TODO: 서버에 스캔 트리거 API 호출
        # 현재는 Watchlist 새로고침으로 대체
        await self.refresh_watchlist()
    
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
