
import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from backend.broker.ibkr_connector import IBKRConnector
from backend.core.scanner import Scanner, run_scan
from backend.data.database import MarketDB

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STARTING = "starting" # Engine starting
    RUNNING = "running"   # Engine running
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class WatchlistItem:
    ticker: str
    score: float
    stage: str
    last_close: float = 0.0
    change_pct: float = 0.0
    
    def to_display_string(self) -> str:
        sign = "+" if self.change_pct >= 0 else ""
        return f"{self.ticker:6s} {sign}{self.change_pct:.1f}%  [{self.score:.0f}]"

class ScannerWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, db_path="data/market_data.db"):
        super().__init__()
        self.db_path = db_path

    def run(self):
        try:
            watchlist_data = asyncio.run(run_scan(self.db_path))
            items = []
            for item in watchlist_data:
                items.append(WatchlistItem(
                    ticker=item['ticker'],
                    score=item['score'],
                    stage=item['stage'],
                    last_close=item.get('last_close', 0.0),
                    change_pct=0.0 # TODO: Calculate change
                ))
            self.finished.emit(items)
        except Exception as e:
            self.error.emit(str(e))

class BackendClient(QObject):
    """
    Backend 서비스 통합 클라이언트
    """
    _instance = None
    
    # Signals
    connected = pyqtSignal(bool)
    state_changed = pyqtSignal(ConnectionState)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    watchlist_updated = pyqtSignal(list)
    
    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = BackendClient()
        return cls._instance

    def __init__(self, parent=None):
        if BackendClient._instance and hasattr(BackendClient._instance, '_initialized'):
            return
            
        super().__init__(parent)
        self._initialized = True
        
        # IBKR Connector
        self.ibkr = IBKRConnector()
        self.ibkr.connected.connect(self._on_ibkr_connected)
        self.ibkr.error.connect(self.error_occurred.emit)
        self.ibkr.log_message.connect(self.log_message.emit)
        
        self.scanner_worker = None
        self.state = ConnectionState.DISCONNECTED

    def _set_state(self, state: ConnectionState):
        self.state = state
        self.state_changed.emit(state)

    def _on_ibkr_connected(self, is_connected: bool):
        self.connected.emit(is_connected)
        if is_connected:
            self._set_state(ConnectionState.CONNECTED)
        else:
            self._set_state(ConnectionState.DISCONNECTED)

    def connect(self) -> bool:
        """Backend 연결"""
        if self.state == ConnectionState.CONNECTED:
            return True
        
        self._set_state(ConnectionState.CONNECTING)
        if not self.ibkr.isRunning():
            self.ibkr.start()
        return True
            
    def disconnect(self):
        self.ibkr.stop()
        self._set_state(ConnectionState.DISCONNECTED)
        
    def start_engine(self):
        """Trading Engine 시작 (Placeholder)"""
        if self.state != ConnectionState.CONNECTED:
            self.log_message.emit("⚠️ Cannot start engine: Not connected")
            return
            
        self._set_state(ConnectionState.RUNNING)
        self.log_message.emit("🚀 Trading Engine Started (Simulation Mode)")
        
    def stop_engine(self):
        """Trading Engine 정지"""
        if self.state == ConnectionState.RUNNING:
            self._set_state(ConnectionState.CONNECTED)
            self.log_message.emit("⏹ Trading Engine Stopped")
            
    def kill_switch(self):
        """긴급 종료"""
        self.stop_engine()
        self.disconnect()
        self.log_message.emit("⚡ KILL SWITCH EXECUTED: All systems stopped.")

    def run_scanner(self, strategy_name: str = "seismograph"):
        """Scanner 시작 (이름 변경: start_scanner -> run_scanner)"""
        if self.scanner_worker and self.scanner_worker.isRunning():
            self.log_message.emit("⚠️ Scanner is already running.")
            return

        self.log_message.emit(f"🚀 Starting Scanner for {strategy_name}...")
        
        self.scanner_worker = ScannerWorker()
        self.scanner_worker.finished.connect(self._on_scanner_finished)
        self.scanner_worker.error.connect(self._on_scanner_error)
        self.scanner_worker.start()
        
    def _on_scanner_finished(self, items: list):
        self.log_message.emit(f"✅ Scanner finished: Found {len(items)} items")
        self.watchlist_updated.emit(items)
        
    def _on_scanner_error(self, error: str):
        self.log_message.emit(f"❌ Scanner failed: {error}")
        self.error_occurred.emit(error)

    def is_connected(self) -> bool:
        return self.ibkr.is_connected()
