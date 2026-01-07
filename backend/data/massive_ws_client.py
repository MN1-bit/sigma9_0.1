# ============================================================================
# Massive WebSocket Client - 실시간 스트리밍 클라이언트
# ============================================================================
# 📌 이 파일의 역할:
#   - Massive.com (구 Massive.com) WebSocket 연결 관리
#   - AM (Aggregate Minute) 채널: 1분봉 실시간 수신
#   - T (Trades) 채널: 틱 데이터 실시간 수신 (선택)
#
# 📖 API 문서: https://massive.com/docs/websocket/quickstart
#
# 📖 Data Flow:
#   Massive WebSocket (wss://socket.massive.com/stocks)
#       ↓ AM/T messages
#   MassiveWebSocketClient
#       ↓ on_bar / on_tick callbacks
#   TickBroadcaster → GUI
# ============================================================================

"""
Massive WebSocket Client

Massive.com의 실시간 주식 데이터를 WebSocket으로 수신합니다.

Channels:
    - AM.{ticker}: Aggregate Minute (1분봉)
    - T.{ticker}: Trades (개별 체결)

Example:
    >>> client = MassiveWebSocketClient(api_key="YOUR_KEY")
    >>> await client.connect()
    >>> await client.subscribe(["AAPL", "NVDA"], channel="AM")
    >>> async for bar in client.listen():
    ...     print(f"{bar['sym']}: ${bar['c']}")
"""

import os
import json
import asyncio
from typing import List, Optional, Callable, AsyncIterator, Any
from datetime import datetime
from enum import Enum

from loguru import logger

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("⚠️ websockets not installed. Run: pip install websockets")


class Channel(str, Enum):
    """Massive WebSocket 채널"""
    AM = "AM"  # Aggregate Minute (1분봉)
    T = "T"    # Trades (체결)
    A = "A"    # Aggregate Second (1초봉)
    Q = "Q"    # Quotes (호가)


class MassiveWebSocketClient:
    """
    Massive.com 실시간 WebSocket 클라이언트
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    이 클래스는 "실시간 라디오 수신기"와 같습니다.
    
    Massive 서버에 연결하고 원하는 종목을 "구독"하면,
    해당 종목의 1분봉이 완성될 때마다 실시간으로 데이터가 도착합니다.
    
    사용 예:
    1. connect() - 라디오 전원 켜기
    2. subscribe(["AAPL"]) - AAPL 채널 맞추기
    3. listen() - 방송 듣기
    """
    
    # WebSocket 엔드포인트
    WS_REALTIME = "wss://socket.massive.com/stocks"
    WS_DELAYED = "wss://delayed.massive.com/stocks"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        delayed: bool = False,
        reconnect_interval: int = 5
    ):
        """
        MassiveWebSocketClient 초기화
        
        Args:
            api_key: Massive API 키 (None이면 환경변수 사용)
            delayed: True면 15분 지연 데이터 (무료), False면 실시간
            reconnect_interval: 재연결 시도 간격 (초)
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets is required. Run: pip install websockets")
        
        self.api_key = api_key or os.getenv("MASSIVE_API_KEY")
        if not self.api_key:
            raise ValueError("MASSIVE_API_KEY is required")
        
        self.ws_url = self.WS_DELAYED if delayed else self.WS_REALTIME
        self.reconnect_interval = reconnect_interval
        
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._is_connected = False
        self._is_authenticated = False
        self._subscribed_channels: set = set()
        self._should_reconnect = True
        
        # 콜백
        self.on_bar: Optional[Callable[[dict], None]] = None
        self.on_tick: Optional[Callable[[dict], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        logger.info(f"📡 MassiveWSClient initialized: {'Delayed' if delayed else 'Realtime'}")
    
    @property
    def is_connected(self) -> bool:
        """연결 상태"""
        return self._is_connected and self._is_authenticated
    
    # ─────────────────────────────────────────────────────────────────────
    # Connection Management
    # ─────────────────────────────────────────────────────────────────────
    
    async def connect(self) -> bool:
        """
        WebSocket 연결 및 인증
        
        Returns:
            bool: 연결 및 인증 성공 여부
        """
        try:
            logger.info(f"📡 Connecting to {self.ws_url}...")
            
            self._ws = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            self._is_connected = True
            
            # 서버 환영 메시지 수신
            welcome = await self._ws.recv()
            logger.debug(f"📡 Server: {welcome}")
            
            # 인증
            await self._authenticate()
            
            logger.info("✅ Massive WebSocket connected and authenticated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            self._is_connected = False
            return False
    
    async def _authenticate(self):
        """API 키로 인증"""
        auth_msg = json.dumps({
            "action": "auth",
            "params": self.api_key
        })
        await self._ws.send(auth_msg)
        
        # 인증 응답 대기
        response = await self._ws.recv()
        data = json.loads(response)
        
        if isinstance(data, list):
            data = data[0]
        
        if data.get("status") == "auth_success":
            self._is_authenticated = True
            logger.info("✅ Authentication successful")
        else:
            raise ConnectionError(f"Authentication failed: {data}")
    
    async def disconnect(self):
        """연결 해제"""
        self._should_reconnect = False
        self._is_connected = False
        self._is_authenticated = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        logger.info("📡 Massive WebSocket disconnected")
    
    # ─────────────────────────────────────────────────────────────────────
    # Subscription Management
    # ─────────────────────────────────────────────────────────────────────
    
    async def subscribe(self, tickers: List[str], channel: Channel = Channel.AM):
        """
        채널 구독
        
        Args:
            tickers: 종목 심볼 목록 ["AAPL", "NVDA", ...]
            channel: 구독 채널 (AM: 1분봉, T: 틱)
        """
        if not self.is_connected:
            logger.warning("Cannot subscribe: not connected")
            return
        
        # "AM.AAPL,AM.NVDA" 형태로 변환
        params = ",".join([f"{channel.value}.{t}" for t in tickers])
        
        sub_msg = json.dumps({
            "action": "subscribe",
            "params": params
        })
        await self._ws.send(sub_msg)
        
        # 구독 목록 업데이트
        for t in tickers:
            self._subscribed_channels.add(f"{channel.value}.{t}")
        
        logger.info(f"📡 Subscribed: {channel.value} x {len(tickers)} tickers")
    
    async def unsubscribe(self, tickers: List[str], channel: Channel = Channel.AM):
        """
        채널 구독 해제
        
        Args:
            tickers: 종목 심볼 목록
            channel: 해제할 채널
        """
        if not self.is_connected:
            return
        
        params = ",".join([f"{channel.value}.{t}" for t in tickers])
        
        unsub_msg = json.dumps({
            "action": "unsubscribe",
            "params": params
        })
        await self._ws.send(unsub_msg)
        
        for t in tickers:
            self._subscribed_channels.discard(f"{channel.value}.{t}")
        
        logger.info(f"📡 Unsubscribed: {channel.value} x {len(tickers)} tickers")
    
    # ─────────────────────────────────────────────────────────────────────
    # Message Handling
    # ─────────────────────────────────────────────────────────────────────
    
    async def listen(self) -> AsyncIterator[dict]:
        """
        메시지 수신 루프
        
        Yields:
            dict: 수신된 메시지 (AM: 1분봉, T: 틱)
        """
        if not self.is_connected:
            logger.warning("Cannot listen: not connected")
            return
        
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    
                    # 배열로 올 수 있음 (고빈도 데이터)
                    if isinstance(data, list):
                        for item in data:
                            parsed = self._parse_message(item)
                            if parsed:
                                yield parsed
                    else:
                        parsed = self._parse_message(data)
                        if parsed:
                            yield parsed
                            
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON: {message[:100]}")
                    
        except websockets.ConnectionClosed as e:
            logger.warning(f"Connection closed: {e}")
            self._is_connected = False
            
            if self._should_reconnect:
                await self._reconnect()
    
    def _parse_message(self, data: dict) -> Optional[dict]:
        """
        메시지 파싱 및 콜백 호출
        
        Args:
            data: 원시 메시지 데이터
            
        Returns:
            dict | None: 파싱된 데이터 (status 메시지는 None)
        """
        ev = data.get("ev")
        
        if ev == "AM":
            # Aggregate Minute (1분봉)
            bar = {
                "type": "bar",
                "ticker": data.get("sym"),
                "timeframe": "1m",
                "time": data.get("s", 0) / 1000,  # Unix ms → s
                "open": data.get("o"),
                "high": data.get("h"),
                "low": data.get("l"),
                "close": data.get("c"),
                "volume": data.get("v"),
                "vwap": data.get("a"),
                "trades": data.get("n"),
            }
            
            if self.on_bar:
                self.on_bar(bar)
            
            return bar
        
        elif ev == "T":
            # Trade (틱)
            tick = {
                "type": "tick",
                "ticker": data.get("sym"),
                "price": data.get("p"),
                "size": data.get("s"),
                "time": data.get("t", 0) / 1000,
                "conditions": data.get("c"),
            }
            
            if self.on_tick:
                self.on_tick(tick)
            
            return tick
        
        elif ev == "status":
            # 상태 메시지 (구독 확인 등)
            logger.debug(f"Status: {data.get('message')}")
            return None
        
        return None
    
    async def _reconnect(self):
        """자동 재연결"""
        while self._should_reconnect and not self._is_connected:
            logger.info(f"🔄 Reconnecting in {self.reconnect_interval}s...")
            await asyncio.sleep(self.reconnect_interval)
            
            if await self.connect():
                # 이전 구독 복원
                if self._subscribed_channels:
                    tickers_am = [c.split(".")[1] for c in self._subscribed_channels if c.startswith("AM.")]
                    tickers_t = [c.split(".")[1] for c in self._subscribed_channels if c.startswith("T.")]
                    
                    if tickers_am:
                        await self.subscribe(tickers_am, Channel.AM)
                    if tickers_t:
                        await self.subscribe(tickers_t, Channel.T)
                
                break
    
    @property
    def subscribed_tickers(self) -> List[str]:
        """현재 구독 중인 종목 목록"""
        tickers = set()
        for channel in self._subscribed_channels:
            parts = channel.split(".")
            if len(parts) == 2:
                tickers.add(parts[1])
        return list(tickers)
    
    @property
    def stats(self) -> dict:
        """클라이언트 상태"""
        return {
            "connected": self._is_connected,
            "authenticated": self._is_authenticated,
            "subscribed_channels": len(self._subscribed_channels),
            "tickers": self.subscribed_tickers
        }
