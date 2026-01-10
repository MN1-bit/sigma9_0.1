"""
Sigma9 WebSocket Manager
=========================
실시간 데이터 스트리밍을 위한 WebSocket 연결 관리자.

📌 메시지 타입:
    - LOG:xxx       - 서버 로그
    - TICK:xxx      - 틱 데이터 (JSON)
    - TRADE:xxx     - 거래 이벤트 (JSON)
    - WATCHLIST:xxx - Watchlist 업데이트 (JSON)
    - STATUS:xxx    - 상태 변경 (JSON)
    - IGNITION:xxx  - Ignition Score 업데이트 (JSON)
"""

import json
from typing import List, Dict, Any, Optional
from enum import Enum
from fastapi import WebSocket
from loguru import logger


class MessageType(str, Enum):
    """WebSocket 메시지 타입"""

    LOG = "LOG"
    TICK = "TICK"
    BAR = "BAR"  # Phase 4.A.0: 실시간 OHLCV 바 업데이트
    TRADE = "TRADE"
    WATCHLIST = "WATCHLIST"
    STATUS = "STATUS"
    IGNITION = "IGNITION"  # Phase 2: 실시간 Ignition Score
    ERROR = "ERROR"
    PONG = "PONG"


class ConnectionManager:
    """
    WebSocket 연결 관리자

    📌 기능:
        - 다중 클라이언트 연결 관리
        - 타입별 메시지 브로드캐스트
        - 연결 상태 추적
    """

    def __init__(self):
        # 활성 연결 목록
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        새 클라이언트 연결 수락

        Args:
            websocket: FastAPI WebSocket 인스턴스
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"📡 Client connected. Total connections: {len(self.active_connections)}"
        )

        # 연결 성공 알림
        await self._send_to_client(
            websocket,
            MessageType.STATUS,
            {"event": "connected", "message": "Connected to Sigma9 Trading Engine"},
        )

    def disconnect(self, websocket: WebSocket):
        """
        클라이언트 연결 해제

        Args:
            websocket: 해제할 WebSocket 인스턴스
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"📡 Client disconnected. Total connections: {len(self.active_connections)}"
            )

    @property
    def connection_count(self) -> int:
        """현재 연결된 클라이언트 수"""
        return len(self.active_connections)

    # ─────────────────────────────────────────────────────────────
    # 개별 클라이언트 전송
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _json_serializer(obj):
        """
        [08-001] 커스텀 JSON 직렬화 (numpy 타입 처리)

        numpy.int64, numpy.float64, numpy.bool_ 등은 기본 json.dumps에서
        처리되지 않아 "Object of type X is not JSON serializable" 오류 발생.
        """
        import numpy as np

        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return str(obj)

    async def _send_to_client(
        self, websocket: WebSocket, msg_type: MessageType, data: Any
    ):
        """단일 클라이언트에게 메시지 전송"""
        try:
            if isinstance(data, dict):
                message = f"{msg_type.value}:{json.dumps(data, default=self._json_serializer)}"
            else:
                message = f"{msg_type.value}:{data}"
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")

    # ─────────────────────────────────────────────────────────────
    # 브로드캐스트 메서드
    # ─────────────────────────────────────────────────────────────

    async def broadcast(self, message: str):
        """
        모든 클라이언트에게 원시 메시지 브로드캐스트

        Args:
            message: 전송할 메시지 문자열
        """
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.append(connection)

        # 끊긴 연결 제거
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_typed(self, msg_type: MessageType, data: Any):
        """
        타입이 지정된 메시지를 모든 클라이언트에게 브로드캐스트

        Args:
            msg_type: 메시지 타입 (LOG, TICK, TRADE 등)
            data: 전송할 데이터 (dict 또는 str)
        """
        import time
        from datetime import datetime, timezone

        if isinstance(data, dict):
            # [08-001] 모든 메시지에 시간 정보 자동 추가 (latency 계산용)
            data["_server_time_utc"] = datetime.now(timezone.utc).isoformat()
            data["_sent_at"] = int(time.time() * 1000)  # Unix ms

            # numpy 타입 처리를 위한 커스텀 인코더
            message = (
                f"{msg_type.value}:{json.dumps(data, default=self._json_serializer)}"
            )
        else:
            message = f"{msg_type.value}:{data}"

        await self.broadcast(message)

    async def broadcast_log(self, log_entry: str):
        """
        로그 메시지 브로드캐스트

        Args:
            log_entry: 로그 문자열
        """
        await self.broadcast_typed(MessageType.LOG, log_entry)

    async def broadcast_tick(
        self, ticker: str, price: float, volume: int, timestamp: str
    ):
        """
        틱 데이터 브로드캐스트

        Args:
            ticker: 종목 코드
            price: 현재가
            volume: 거래량
            timestamp: 타임스탬프
        """
        await self.broadcast_typed(
            MessageType.TICK,
            {
                "ticker": ticker,
                "price": price,
                "volume": volume,
                "timestamp": timestamp,
            },
        )

    async def broadcast_trade(self, event: str, order_id: str, ticker: str, **details):
        """
        거래 이벤트 브로드캐스트

        Args:
            event: 이벤트 타입 (FILL, CANCEL, REJECT 등)
            order_id: 주문 ID
            ticker: 종목 코드
            **details: 추가 정보
        """
        await self.broadcast_typed(
            MessageType.TRADE,
            {"event": event, "order_id": order_id, "ticker": ticker, **details},
        )

    async def broadcast_watchlist(
        self,
        items: List[Dict[str, Any]],
        event_time_ms: Optional[int] = None,
        event_latency_ms: Optional[int] = None,  # [08-001] 직접 계산된 E 레이턴시
    ):
        """
        Watchlist 업데이트 브로드캐스트

        Args:
            items: Watchlist 항목 리스트
            event_time_ms: (선택) 이벤트 타임스탬프 (직접 전달 시 항목 순회 생략)
            event_latency_ms: (선택) 직접 계산된 E 레이턴시 (ms)
        """
        data = {"count": len(items), "items": items}

        # [08-001] event_latency_ms가 있으면 직접 사용 (가장 정확)
        if event_latency_ms is not None:
            data["_event_latency_ms"] = event_latency_ms

        # event_time_ms는 호환성을 위해 유지 (fallback)
        if event_time_ms:
            data["_event_time"] = event_time_ms

        await self.broadcast_typed(MessageType.WATCHLIST, data)

    async def broadcast_status(self, event: str, **data):
        """
        상태 변경 브로드캐스트

        Args:
            event: 상태 이벤트 (engine_started, ibkr_connected 등)
            **data: 추가 데이터
        """
        await self.broadcast_typed(MessageType.STATUS, {"event": event, **data})

    async def broadcast_bar(self, ticker: str, timeframe: str, bar: dict):
        """
        실시간 바(캔들) 데이터 브로드캐스트 (Phase 4.A.0)

        TickAggregator에서 생성된 완성된 바를 GUI에 푸시합니다.

        Args:
            ticker: 종목 코드
            timeframe: 타임프레임 ("1m", "5m" 등)
            bar: OHLCV 바 데이터 {time, open, high, low, close, volume}
        """
        await self.broadcast_typed(
            MessageType.BAR, {"ticker": ticker, "timeframe": timeframe, "bar": bar}
        )

    async def broadcast_ignition(
        self, ticker: str, score: float, passed_filter: bool = True, reason: str = ""
    ):
        """
        Ignition Score 업데이트 브로드캐스트 (Phase 2)

        실시간 틱 데이터 기반 Ignition Score를 GUI에 푸시합니다.
        Score ≥ 70 이면 진입 신호로 간주됩니다.

        Args:
            ticker: 종목 코드
            score: Ignition Score (0~100)
            passed_filter: Anti-Trap 필터 통과 여부
            reason: 필터 미통과 시 사유
        """
        from datetime import datetime

        await self.broadcast_typed(
            MessageType.IGNITION,
            {
                "ticker": ticker,
                "score": round(score, 1),
                "passed_filter": passed_filter,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            },
        )


# 싱글톤 인스턴스
manager = ConnectionManager()
