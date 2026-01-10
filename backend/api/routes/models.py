# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Models for Routes
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     routes/ 하위 라우터들이 공유하는 Pydantic 요청/응답 모델 정의.
#     모든 라우터가 이 파일에서 모델을 import하여 일관성 유지.
#
# ═══════════════════════════════════════════════════════════════════════════

from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class EngineCommand(str, Enum):
    """
    엔진 제어 명령 Enum.

    Values:
        START: 엔진 시작
        STOP: 엔진 정지
        KILL: 긴급 정지 (모든 주문 취소 + 포지션 청산)
    """

    START = "start"
    STOP = "stop"
    KILL = "kill"


class ControlRequest(BaseModel):
    """엔진 제어 요청"""

    command: EngineCommand = Field(..., description="제어 명령 (start/stop/kill)")


class ControlResponse(BaseModel):
    """엔진 제어 응답"""

    status: str = Field(..., description="요청 처리 상태 (accepted/rejected)")
    command: str = Field(..., description="실행된 명령")
    message: str = Field(..., description="결과 메시지")
    timestamp: str = Field(..., description="처리 시각 (ISO8601)")


class ServerStatus(BaseModel):
    """서버 상태"""

    server: str = Field(default="running", description="서버 상태")
    engine: str = Field(default="stopped", description="엔진 상태 (stopped/running)")
    ibkr: str = Field(default="disconnected", description="IBKR 연결 상태")
    scheduler: str = Field(default="inactive", description="스케줄러 상태")
    uptime_seconds: float = Field(default=0, description="서버 가동 시간 (초)")
    active_positions: int = Field(default=0, description="활성 포지션 수")
    active_orders: int = Field(default=0, description="활성 주문 수")
    timestamp: str = Field(..., description="조회 시각 (ISO8601)")


class WatchlistItem(BaseModel):
    """Watchlist 항목"""

    ticker: str
    score: float
    score_v3: float = 0.0  # [03-001] v3 Pinpoint Score
    stage: str
    last_close: float
    change_pct: float
    avg_volume: float = 0.0  # [4.A.4] DolVol 계산용
    intensities: dict = {}  # [02-001] 신호 강도


class PositionItem(BaseModel):
    """포지션 항목"""

    ticker: str
    quantity: int
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    pnl_pct: float


class StrategyInfo(BaseModel):
    """전략 정보"""

    name: str
    version: str
    description: str
    is_loaded: bool


class AnalysisRequest(BaseModel):
    """LLM 분석 요청"""

    ticker: str
    question: Optional[str] = None
    provider: Optional[str] = "openai"
    model: Optional[str] = None


class Tier2PromoteRequest(BaseModel):
    """Tier 2 승격 요청"""

    tickers: List[str] = Field(..., description="Tier 2로 승격할 종목 목록")


class Tier2CheckRequest(BaseModel):
    """Tier 2 승격 조건 판단 요청"""

    ticker: str = Field(..., description="종목 코드")
    ignition_score: float = Field(..., description="Ignition Score")
    passed_filter: bool = Field(default=True, description="Anti-Trap 필터 통과 여부")
    stage_number: int = Field(default=0, description="Stage 번호")
    acc_score: float = Field(default=0.0, description="Accumulation Score")
    source: str = Field(default="", description="소스 (realtime_gainer 등)")
    zenV: float = Field(default=0.0, description="Z-Score Volume")
    zenP: float = Field(default=0.0, description="Z-Score Price")
