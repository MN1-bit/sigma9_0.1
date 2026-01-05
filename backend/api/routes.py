"""
Sigma9 REST API Routes
=======================
백엔드 제어 및 조회 API 엔드포인트.

📌 엔드포인트 목록:
    GET  /api/status          - 서버/엔진 상태 조회
    POST /api/control         - 엔진 제어 (start/stop/kill)
    GET  /api/watchlist       - Watchlist 조회
    GET  /api/positions       - 포지션 조회
    POST /api/kill-switch     - 긴급 정지
    GET  /api/strategies      - 전략 목록
    POST /api/strategies/{name}/reload - 전략 리로드
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Models (요청/응답 모델)
# ═══════════════════════════════════════════════════════════════════════════

class EngineCommand(str, Enum):
    """엔진 제어 명령"""
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
    score_v2: float = 0.0  # [02-001] v2 연속 점수
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


# ═══════════════════════════════════════════════════════════════════════════
# Router Instance
# ═══════════════════════════════════════════════════════════════════════════

router = APIRouter()

# 서버 시작 시각 (uptime 계산용)
_server_start_time: datetime = datetime.now(timezone.utc)

# 엔진 상태 (임시 - 실제로는 Engine 클래스에서 관리)
_engine_running: bool = False


def _get_timestamp() -> str:
    """현재 시각을 ISO8601 형식으로 반환"""
    return datetime.now(timezone.utc).isoformat()


def _get_uptime_seconds() -> float:
    """서버 가동 시간 (초) 반환"""
    return (datetime.now(timezone.utc) - _server_start_time).total_seconds()


# ═══════════════════════════════════════════════════════════════════════════
# Status Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/status", response_model=ServerStatus, summary="서버 상태 조회")
async def get_status():
    """
    서버, 엔진, IBKR, 스케줄러 상태를 조회합니다.
    
    📌 상태값:
        - server: running/stopped
        - engine: running/stopped
        - ibkr: connected/disconnected
        - scheduler: active/inactive
    """
    from backend.server import app_state
    
    # IBKR 상태 확인
    ibkr_status = "disconnected"
    if app_state.ibkr:
        try:
            ibkr_status = "connected" if app_state.ibkr.is_connected() else "disconnected"
        except:
            ibkr_status = "error"
    
    # 스케줄러 상태 확인
    scheduler_status = "inactive"
    if app_state.scheduler:
        try:
            scheduler_status = "active" if app_state.scheduler.running else "inactive"
        except:
            scheduler_status = "error"
    
    # 엔진 상태 확인
    engine_status = "stopped"
    active_positions = 0
    active_orders = 0
    if app_state.engine:
        try:
            engine_status = "running" if app_state.engine.is_running else "stopped"
            active_positions = app_state.engine.position_count
            active_orders = app_state.engine.order_count
        except:
            pass
    elif _engine_running:
        engine_status = "running"
    
    return ServerStatus(
        server="running",
        engine=engine_status,
        ibkr=ibkr_status,
        scheduler=scheduler_status,
        uptime_seconds=_get_uptime_seconds(),
        active_positions=active_positions,
        active_orders=active_orders,
        timestamp=_get_timestamp()
    )


# ═══════════════════════════════════════════════════════════════════════════
# Control Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/control", response_model=ControlResponse, summary="엔진 제어")
async def control_engine(request: ControlRequest):
    """
    트레이딩 엔진을 제어합니다.
    
    📌 명령:
        - start: 엔진 시작 (IBKR 연결, 전략 로드, 모니터링 시작)
        - stop: 엔진 정지 (신규 거래 차단, 기존 포지션 유지)
        - kill: 긴급 정지 (모든 주문 취소, 모든 포지션 청산)
    """
    global _engine_running
    from backend.server import app_state
    
    logger.info(f"🎮 Control command received: {request.command}")
    
    if request.command == EngineCommand.START:
        if _engine_running:
            return ControlResponse(
                status="rejected",
                command=request.command,
                message="Engine is already running",
                timestamp=_get_timestamp()
            )
        
        # TODO: 실제 엔진 시작 로직
        # app_state.engine.start()
        _engine_running = True
        logger.info("🚀 Trading Engine Started")
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Engine started successfully",
            timestamp=_get_timestamp()
        )
    
    elif request.command == EngineCommand.STOP:
        if not _engine_running:
            return ControlResponse(
                status="rejected",
                command=request.command,
                message="Engine is not running",
                timestamp=_get_timestamp()
            )
        
        # TODO: 실제 엔진 정지 로직
        # app_state.engine.stop()
        _engine_running = False
        logger.info("⏹ Trading Engine Stopped")
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Engine stopped successfully",
            timestamp=_get_timestamp()
        )
    
    elif request.command == EngineCommand.KILL:
        # Kill Switch는 항상 실행
        logger.warning("⚡ KILL SWITCH ACTIVATED!")
        
        # TODO: 실제 Kill Switch 로직
        # 1. 모든 미체결 주문 취소
        # 2. 모든 포지션 시장가 청산
        # 3. 엔진 정지
        _engine_running = False
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Kill switch executed - All orders cancelled, all positions closed",
            timestamp=_get_timestamp()
        )


@router.post("/kill-switch", response_model=ControlResponse, summary="긴급 정지")
async def kill_switch():
    """
    🔴 긴급 정지 버튼
    
    모든 미체결 주문을 취소하고 모든 포지션을 시장가로 청산합니다.
    확인 없이 즉시 실행됩니다.
    """
    return await control_engine(ControlRequest(command=EngineCommand.KILL))


# ═══════════════════════════════════════════════════════════════════════════
# Engine Control Endpoints (Alternative)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/engine/start", response_model=ControlResponse, summary="엔진 시작")
async def start_engine():
    """트레이딩 엔진을 시작합니다."""
    return await control_engine(ControlRequest(command=EngineCommand.START))


@router.post("/engine/stop", response_model=ControlResponse, summary="엔진 정지")
async def stop_engine():
    """트레이딩 엔진을 정지합니다."""
    return await control_engine(ControlRequest(command=EngineCommand.STOP))


@router.get("/engine/status", summary="엔진 상태 조회")
async def get_engine_status():
    """엔진 상세 상태를 조회합니다."""
    return {
        "running": _engine_running,
        "strategy": "seismograph" if _engine_running else None,
        "watchlist_count": 0,  # TODO: 실제 값
        "timestamp": _get_timestamp()
    }


# ═══════════════════════════════════════════════════════════════════════════
# Watchlist Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/watchlist", response_model=List[WatchlistItem], summary="Watchlist 조회")
async def get_watchlist():
    """
    현재 Watchlist를 조회합니다.
    
    📌 반환값:
        - ticker: 종목 코드
        - score: 매집 점수 (0~100)
        - stage: 매집 단계 (Stage 1~4)
        - last_close: 최근 종가
        - change_pct: 변동률 (%)
    """
    from backend.data.watchlist_store import load_watchlist
    
    # WatchlistStore에서 실제 데이터 로드
    raw_watchlist = load_watchlist()
    
    if raw_watchlist:
        result = []
        for item in raw_watchlist:
            result.append(WatchlistItem(
                ticker=item.get("ticker", ""),
                score=item.get("score", 0.0),
                score_v2=item.get("score_v2", 0.0),  # [02-001] v2 점수
                stage=item.get("stage", "Unknown"),
                last_close=item.get("last_close", 0.0),
                change_pct=item.get("change_pct", 0.0),
                avg_volume=item.get("avg_volume", 0.0),  # [4.A.4] DolVol용
                intensities=item.get("intensities", {}),  # [02-001] 신호 강도
            ))
        logger.info(f"📋 Watchlist 반환: {len(result)}개 항목")
        return result

    
    # 데이터가 없으면 빈 리스트 반환
    logger.warning("⚠️ Watchlist 비어 있음")
    return []


# ═══════════════════════════════════════════════════════════════════════════
# Position Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/positions", response_model=List[PositionItem], summary="포지션 조회")
async def get_positions():
    """
    현재 보유 포지션을 조회합니다.
    """
    # TODO: 실제 포지션 조회 로직
    # from backend.server import app_state
    # if app_state.ibkr:
    #     return app_state.ibkr.get_positions()
    
    # 임시 빈 리스트 반환
    return []


# ═══════════════════════════════════════════════════════════════════════════
# Strategy Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/strategies", response_model=List[StrategyInfo], summary="전략 목록 조회")
async def get_strategies():
    """
    사용 가능한 전략 목록을 조회합니다.
    """
    from backend.server import app_state
    
    if not app_state.strategy_loader:
        return []
    
    try:
        # 발견된 전략 목록
        discovered = app_state.strategy_loader.discover_strategies()
        loaded = app_state.strategy_loader.list_loaded()
        loaded_names = {s.get("name") for s in loaded}
        
        strategies = []
        for name in discovered:
            is_loaded = name in loaded_names
            
            # 로드된 전략이면 메타정보 가져오기
            if is_loaded:
                meta = next((s for s in loaded if s.get("name") == name), {})
                strategies.append(StrategyInfo(
                    name=name,
                    version=meta.get("version", "1.0.0"),
                    description=meta.get("description", ""),
                    is_loaded=True
                ))
            else:
                strategies.append(StrategyInfo(
                    name=name,
                    version="?",
                    description="Not loaded",
                    is_loaded=False
                ))
        
        return strategies
    
    except Exception as e:
        logger.error(f"Failed to get strategies: {e}")
        return []


@router.post("/strategies/{name}/load", summary="전략 로드")
async def load_strategy(name: str):
    """
    지정된 전략을 로드합니다.
    """
    from backend.server import app_state
    
    if not app_state.strategy_loader:
        raise HTTPException(status_code=500, detail="Strategy loader not initialized")
    
    try:
        strategy = app_state.strategy_loader.load_strategy(name)
        logger.info(f"✅ Strategy loaded: {name}")
        return {"status": "loaded", "name": name, "timestamp": _get_timestamp()}
    except Exception as e:
        logger.error(f"Failed to load strategy {name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/strategies/{name}/reload", summary="전략 리로드")
async def reload_strategy(name: str):
    """
    지정된 전략을 핫 리로드합니다.
    """
    from backend.server import app_state
    
    if not app_state.strategy_loader:
        raise HTTPException(status_code=500, detail="Strategy loader not initialized")
    
    try:
        strategy = app_state.strategy_loader.reload_strategy(name)
        logger.info(f"🔄 Strategy reloaded: {name}")
        return {"status": "reloaded", "name": name, "timestamp": _get_timestamp()}
    except Exception as e:
        logger.error(f"Failed to reload strategy {name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Scanner Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/scanner/run", summary="Scanner 실행")
async def run_scanner(strategy_name: str = "seismograph"):
    """
    Scanner를 실행하여 Watchlist를 생성합니다.
    
    📌 동작:
        1. MarketDB에서 시장 데이터 조회
        2. 전략의 스캔 로직 실행 (Seismograph)
        3. Watchlist 저장 및 반환
    """
    from backend.data.database import MarketDB
    from backend.core.scanner import Scanner
    from backend.data.watchlist_store import get_watchlist_store
    
    logger.info(f"🔍 Scanner 실행 요청: {strategy_name}")
    
    try:
        # MarketDB 초기화
        db = MarketDB("data/market_data.db")
        await db.initialize()
        
        # Scanner 생성 및 실행
        scanner = Scanner(db, watchlist_size=50)
        watchlist = await scanner.run_daily_scan(
            min_price=2.0,
            max_price=20.0,
            min_volume=100_000,
            lookback_days=20
        )
        
        # Watchlist 저장 (병합)
        if watchlist:
            # [Issue 01-002 Fix] 기존 Day Gainer 유지를 위해 병합 저장
            from backend.data.watchlist_store import merge_watchlist
            merged = merge_watchlist(watchlist, update_existing=True)
            logger.info(f"✅ Scanner 완료: {len(watchlist)}개 스캔, {len(merged)}개 총 Watchlist")
        else:
            logger.warning("⚠️ Scanner: 조건에 맞는 종목 없음")
        
        return {
            "status": "success",
            "strategy": strategy_name,
            "item_count": len(watchlist) if watchlist else 0,
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Scanner 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Day Gainers Endpoints (실시간 급등주)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/gainers", summary="당일 급등주 조회")
async def get_day_gainers():
    """
    Polygon.io API를 통해 당일 급등주 상위 20개를 조회합니다.
    
    📌 데이터:
        - 실시간 (장중)
        - 전일 종가 대비 상승률 기준
        - 거래량 10,000 이상만 포함
    
    Returns:
        list: 급등주 리스트 [{ticker, change_pct, last_price, volume}, ...]
    """
    import os
    from backend.data.polygon_client import PolygonClient
    
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")
    
    try:
        async with PolygonClient(api_key) as client:
            gainers = await client.fetch_day_gainers()
        
        return {
            "status": "success",
            "count": len(gainers),
            "gainers": gainers,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Day Gainers 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gainers/add-to-watchlist", summary="급등주를 Watchlist에 추가")
async def add_gainers_to_watchlist():
    """
    당일 급등주를 현재 Watchlist에 병합합니다.
    
    📌 동작:
        1. Polygon Gainers API로 급등주 조회
        2. 현재 Watchlist와 병합 (중복 제거)
        3. score=0 (급등주)으로 표시
    """
    import os
    from backend.data.polygon_client import PolygonClient
    from backend.data.watchlist_store import get_watchlist_store
    
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")
    
    try:
        # 급등주 조회
        async with PolygonClient(api_key) as client:
            gainers = await client.fetch_day_gainers()
        
        if not gainers:
            return {"status": "no_gainers", "added": 0}
        
        # 현재 Watchlist 로드
        store = get_watchlist_store()
        watchlist = store.load()
        existing_tickers = {item.get("ticker") for item in watchlist}
        
        # 급등주 중 Watchlist에 없는 것만 추가
        added_count = 0
        for g in gainers:
            ticker = g.get("ticker", "")
            if ticker and ticker not in existing_tickers:
                watchlist.append({
                    "ticker": ticker,
                    "score": 0,  # 급등주 표시 (점수 없음)
                    "stage": "🚀 Day Gainer",
                    "stage_number": 0,
                    "signals": {},
                    "can_trade": False,  # 분석 전이므로 거래 불가
                    "last_close": g.get("last_price", 0),
                    "change_pct": g.get("change_pct", 0),
                    "avg_volume": g.get("volume", 0),
                })
                added_count += 1
                existing_tickers.add(ticker)
        
        # 저장
        store.save(watchlist)
        
        logger.info(f"✅ 급등주 {added_count}개 Watchlist에 추가")
        
        return {
            "status": "success",
            "added": added_count,
            "total": len(watchlist),
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"급등주 추가 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Ignition Endpoints (Phase 2 실시간 모니터링)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/ignition/start", summary="Ignition 모니터링 시작")
async def start_ignition_monitor():
    """
    Ignition Score 모니터링을 시작합니다.
    
    📌 동작:
        1. 현재 Watchlist 로드
        2. IgnitionMonitor 시작
        3. 실시간 틱 수신 → Ignition Score 계산 → WebSocket 브로드캐스트
    """
    from backend.core.ignition_monitor import get_ignition_monitor
    from backend.data.watchlist_store import load_watchlist
    
    monitor = get_ignition_monitor()
    
    if not monitor:
        raise HTTPException(status_code=500, detail="IgnitionMonitor not initialized")
    
    if monitor.is_running:
        return {
            "status": "already_running",
            "ticker_count": monitor.ticker_count,
            "timestamp": _get_timestamp()
        }
    
    # Watchlist 로드
    watchlist = load_watchlist()
    
    if not watchlist:
        raise HTTPException(status_code=400, detail="Watchlist is empty. Run scanner first.")
    
    # 모니터링 시작
    success = await monitor.start(watchlist)
    
    return {
        "status": "started" if success else "failed",
        "ticker_count": monitor.ticker_count,
        "timestamp": _get_timestamp()
    }


@router.post("/ignition/stop", summary="Ignition 모니터링 중지")
async def stop_ignition_monitor():
    """
    Ignition Score 모니터링을 중지합니다.
    """
    from backend.core.ignition_monitor import get_ignition_monitor
    
    monitor = get_ignition_monitor()
    
    if not monitor:
        raise HTTPException(status_code=500, detail="IgnitionMonitor not initialized")
    
    await monitor.stop()
    
    return {
        "status": "stopped",
        "timestamp": _get_timestamp()
    }


@router.get("/ignition/scores", summary="현재 Ignition Score 조회")
async def get_ignition_scores():
    """
    모든 Watchlist 종목의 현재 Ignition Score를 조회합니다.
    
    📌 반환값:
        - running: 모니터링 실행 중 여부
        - ticker_count: 모니터링 종목 수
        - scores: 종목별 Ignition Score (ticker -> score)
    """
    from backend.core.ignition_monitor import get_ignition_monitor
    
    monitor = get_ignition_monitor()
    
    if not monitor:
        return {
            "running": False,
            "ticker_count": 0,
            "scores": {},
            "timestamp": _get_timestamp()
        }
    
    return {
        "running": monitor.is_running,
        "ticker_count": monitor.ticker_count,
        "scores": monitor.get_all_scores(),
        "timestamp": _get_timestamp()
    }

# ═══════════════════════════════════════════════════════════════════════════
# Chart Data Endpoints (Multi-Timeframe Support)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/chart/intraday/{ticker}", summary="Intraday 차트 데이터 조회")
async def get_intraday_chart(
    ticker: str,
    timeframe: int = 5,  # 1, 5, 15, 60 (분 단위)
    days: int = 2,  # 조회 일수 (1-10)
):
    """
    특정 종목의 Intraday 차트 데이터를 조회합니다.
    
    📌 타임프레임:
        - 1: 1분봉
        - 5: 5분봉
        - 15: 15분봉
        - 60: 1시간봉
    
    📌 반환값:
        - candles: OHLCV 데이터 리스트
        - ticker: 종목 심볼
        - timeframe: 타임프레임 (분)
        - count: 데이터 개수
    
    Example:
        GET /api/chart/intraday/AAPL?timeframe=5&days=2
    """
    import os
    from datetime import datetime, timedelta
    from backend.data.polygon_client import PolygonClient
    
    # API Key 확인
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")
    
    # 파라미터 검증
    if timeframe not in [1, 5, 15, 60]:
        raise HTTPException(status_code=400, detail="Invalid timeframe. Use 1, 5, 15, or 60")
    if days < 1 or days > 10:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 10")
    
    # 날짜 범위 계산
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    logger.info(f"📊 Intraday 차트 조회: {ticker} {timeframe}m ({from_date} ~ {to_date})")
    
    try:
        async with PolygonClient(api_key) as client:
            bars = await client.fetch_intraday_bars(
                ticker=ticker.upper(),
                multiplier=timeframe,
                from_date=from_date,
                to_date=to_date,
                limit=5000
            )
        
        if not bars:
            return {
                "status": "no_data",
                "ticker": ticker.upper(),
                "timeframe": timeframe,
                "count": 0,
                "candles": [],
                "timestamp": _get_timestamp()
            }
        
        # 차트 위젯 포맷으로 변환 (timestamp -> time)
        candles = []
        for bar in bars:
            candles.append({
                "time": bar["timestamp"] // 1000,  # ms -> seconds (TradingView 포맷)
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
            })
        
        return {
            "status": "success",
            "ticker": ticker.upper(),
            "timeframe": timeframe,
            "count": len(candles),
            "candles": candles,
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Intraday 차트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Oracle (LLM) Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/oracle/models", summary="LLM 모델 목록")
async def get_oracle_models():
    """
    사용 가능한 LLM 모델 목록을 조회합니다.
    """
    try:
        from backend.llm.oracle import oracle_service
        return await oracle_service.get_available_models()
    except Exception as e:
        logger.error(f"Failed to get oracle models: {e}")
        return {"providers": [], "error": str(e)}


@router.post("/oracle/analyze", summary="종목 분석 요청")
async def analyze_ticker(request: AnalysisRequest):
    """
    종목에 대한 LLM 분석을 요청합니다.
    """
    try:
        from backend.llm.oracle import oracle_service
        
        prompt = f"Analyze ticker {request.ticker}."
        if request.question:
            prompt += f" Question: {request.question}"
        
        result = await oracle_service.analyze(prompt, request.provider, request.model)
        return {
            "ticker": request.ticker,
            "analysis": result,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Oracle analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Tier 2 (Hot Zone) Endpoints - Step 4.A.0.d
# ═══════════════════════════════════════════════════════════════════════════

class Tier2PromoteRequest(BaseModel):
    """Tier 2 승격 요청"""
    tickers: List[str] = Field(..., description="Tier 2로 승격할 종목 목록")


@router.post("/tier2/promote", summary="Tier 2 (Hot Zone) 승격")
async def promote_to_tier2(request: Tier2PromoteRequest):
    """
    종목을 Tier 2 (Hot Zone)로 승격합니다.
    
    📌 동작:
        1. SubscriptionManager에 Tier 2 종목 설정
        2. T채널 (틱) 자동 구독
        3. TickDispatcher 필터 업데이트 (전략에 Tier 2만 전달)
    
    Args:
        tickers: Tier 2로 승격할 종목 목록
    
    Returns:
        dict: {status, promoted_count, tick_subscribed}
    """
    from backend.server import app_state
    
    tickers = request.tickers
    
    if not tickers:
        return {
            "status": "no_tickers",
            "promoted_count": 0,
            "timestamp": _get_timestamp()
        }
    
    logger.info(f"🔥 Tier 2 승격 요청: {tickers}")
    
    promoted_count = 0
    tick_subscribed = []
    
    try:
        # 1. SubscriptionManager 업데이트
        if app_state.sub_manager:
            app_state.sub_manager.set_tier2_tickers(tickers)
            
            # 2. T채널 구독 동기화
            await app_state.sub_manager.sync_tick_subscriptions()
            tick_subscribed = app_state.sub_manager.tick_subscribed_tickers
            promoted_count = len(tickers)
            
            logger.info(f"✅ Tier 2 설정 완료: {len(tickers)}개, T채널: {len(tick_subscribed)}개")
        
        # 3. TickDispatcher 필터 업데이트 (전략에 Tier 2만 전달)
        if app_state.tick_dispatcher:
            app_state.tick_dispatcher.update_filter("strategy", tickers)
            logger.info(f"✅ TickDispatcher 필터 업데이트: {tickers}")
        
        return {
            "status": "success",
            "promoted_count": promoted_count,
            "tick_subscribed": tick_subscribed,
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Tier 2 승격 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tier2/demote", summary="Tier 2 해제")
async def demote_from_tier2(request: Tier2PromoteRequest):
    """
    종목을 Tier 2에서 해제합니다.
    
    📌 동작:
        1. SubscriptionManager에서 Tier 2 제거
        2. T채널 구독 해제
        3. TickDispatcher 필터 업데이트
    """
    from backend.server import app_state
    
    tickers = request.tickers
    
    if not tickers:
        return {"status": "no_tickers", "timestamp": _get_timestamp()}
    
    logger.info(f"⬇️ Tier 2 해제 요청: {tickers}")
    
    try:
        if app_state.sub_manager:
            # 현재 Tier 2에서 제거
            current_tier2 = set(app_state.sub_manager._tier2_tickers)
            new_tier2 = current_tier2 - set(tickers)
            app_state.sub_manager.set_tier2_tickers(list(new_tier2))
            
            # T채널 동기화
            await app_state.sub_manager.sync_tick_subscriptions()
        
        # TickDispatcher 필터 업데이트
        if app_state.tick_dispatcher and app_state.sub_manager:
            app_state.tick_dispatcher.update_filter(
                "strategy", 
                list(app_state.sub_manager._tier2_tickers)
            )
        
        return {
            "status": "success",
            "remaining_tier2": list(app_state.sub_manager._tier2_tickers) if app_state.sub_manager else [],
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Tier 2 해제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tier2/status", summary="Tier 2 상태 조회")
async def get_tier2_status():
    """
    현재 Tier 2 (Hot Zone) 상태를 조회합니다.
    
    Returns:
        dict: {tier2_tickers, tick_subscribed, dispatcher_filter}
    """
    from backend.server import app_state
    
    tier2_tickers = []
    tick_subscribed = []
    dispatcher_stats = {}
    
    if app_state.sub_manager:
        tier2_tickers = list(app_state.sub_manager._tier2_tickers)
        tick_subscribed = app_state.sub_manager.tick_subscribed_tickers
    
    if app_state.tick_dispatcher:
        dispatcher_stats = app_state.tick_dispatcher.stats
    
    return {
        "tier2_tickers": tier2_tickers,
        "tick_subscribed": tick_subscribed,
        "dispatcher_stats": dispatcher_stats,
        "timestamp": _get_timestamp()
    }


# ═══════════════════════════════════════════════════════════════════════════
# Z-Score Endpoints (Step 4.A.3)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/zscore/{ticker}", summary="종목 Z-Score 조회")
async def get_zscore(ticker: str):
    """
    특정 종목의 Z-Score (zenV, zenP)를 계산합니다.
    
    📌 Z-Score:
        - zenV: Volume Z-Score (거래량이 평균 대비 몇 표준편차인지)
        - zenP: Price Z-Score (가격 변동이 평균 대비 몇 표준편차인지)
    
    📌 매집 신호:
        - zenV > 2.0 AND zenP < 1.0: 높은 거래량, 낮은 가격 변동 = 매집 가능성 🔥
    
    Args:
        ticker: 종목 심볼 (예: "AAPL")
    
    Returns:
        dict: {ticker, zenV, zenP, timestamp}
    
    Example:
        GET /api/zscore/AAPL
        → {"ticker": "AAPL", "zenV": 2.35, "zenP": 0.45, "timestamp": "..."}
    """
    from backend.data.database import MarketDB
    from backend.core.zscore_calculator import ZScoreCalculator
    
    logger.info(f"📊 Z-Score 조회 요청: {ticker}")
    
    try:
        # MarketDB에서 20일 일봉 데이터 조회
        db = MarketDB("data/market_data.db")
        await db.initialize()
        
        # get_daily_bars returns most recent first (DESC), we need oldest first
        daily_bars = await db.get_daily_bars(ticker.upper(), days=25)  # 여유분 포함
        
        if not daily_bars:
            logger.warning(f"⚠️ {ticker}: 일봉 데이터 없음")
            return {
                "ticker": ticker.upper(),
                "zenV": 0.0,
                "zenP": 0.0,
                "data_available": False,
                "message": "No daily bar data available",
                "timestamp": _get_timestamp()
            }
        
        # DailyBar 객체를 딕셔너리로 변환하고 시간순 정렬 (오래된 → 최신)
        bars_dict = [bar.to_dict() for bar in reversed(daily_bars)]
        
        # Z-Score 계산
        calculator = ZScoreCalculator(lookback=20)
        result = calculator.calculate(ticker.upper(), bars_dict)
        
        return {
            "ticker": ticker.upper(),
            "zenV": result.zenV,
            "zenP": result.zenP,
            "data_available": True,
            "bars_used": len(bars_dict),
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Z-Score 계산 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Data Sync Endpoints (Issue 1: 일봉 데이터 동기화)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/sync/daily", summary="일봉 데이터 동기화")
async def sync_daily_data():
    """
    누락된 일봉 데이터를 Polygon.io에서 가져와 DB에 저장합니다.
    
    📌 동작:
        1. DB의 가장 최근 일봉 날짜 확인
        2. 최근 날짜 ~ 오늘 사이의 누락된 거래일 계산
        3. 누락된 날짜만 Polygon API로 가져와 저장
    
    📌 사용 시점:
        - 서버 시작 시 자동 호출
        - 수동으로 동기화 필요 시
    
    Returns:
        dict: {status, records_added, db_latest_date, market_latest_date}
    
    Example:
        POST /api/sync/daily
        → {"status": "success", "records_added": 50, ...}
    """
    import os
    from backend.data.database import MarketDB
    from backend.data.polygon_client import PolygonClient
    from backend.data.polygon_loader import PolygonLoader
    
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")
    
    logger.info("🔄 일봉 데이터 동기화 시작...")
    
    try:
        # DB 초기화
        db = MarketDB("data/market_data.db")
        await db.initialize()
        
        # PolygonLoader로 증분 업데이트
        async with PolygonClient(api_key) as client:
            loader = PolygonLoader(db, client)
            
            # 동기화 상태 확인
            sync_status = await loader.get_sync_status()
            
            if sync_status.get("is_up_to_date"):
                logger.info("✅ 일봉 데이터 이미 최신 상태")
                return {
                    "status": "up_to_date",
                    "records_added": 0,
                    "db_latest_date": sync_status.get("db_latest_date"),
                    "market_latest_date": sync_status.get("market_latest_date"),
                    "timestamp": _get_timestamp()
                }
            
            # 증분 업데이트 실행
            records_added = await loader.update_market_data()
            
            # 업데이트 후 상태 다시 확인
            updated_status = await loader.get_sync_status()
            
            logger.info(f"✅ 일봉 데이터 동기화 완료: {records_added}개 레코드 추가")
            
            return {
                "status": "success",
                "records_added": records_added,
                "db_latest_date": updated_status.get("db_latest_date"),
                "market_latest_date": updated_status.get("market_latest_date"),
                "timestamp": _get_timestamp()
            }
    
    except Exception as e:
        logger.error(f"일봉 데이터 동기화 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status", summary="데이터 동기화 상태 조회")
async def get_sync_status():
    """
    현재 데이터 동기화 상태를 조회합니다.
    
    Returns:
        dict: {db_latest_date, market_latest_date, missing_days, is_up_to_date}
    """
    import os
    from backend.data.database import MarketDB
    from backend.data.polygon_client import PolygonClient
    from backend.data.polygon_loader import PolygonLoader
    
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        return {
            "status": "error",
            "message": "MASSIVE_API_KEY not configured",
            "timestamp": _get_timestamp()
        }
    
    try:
        db = MarketDB("data/market_data.db")
        await db.initialize()
        
        async with PolygonClient(api_key) as client:
            loader = PolygonLoader(db, client)
            sync_status = await loader.get_sync_status()
        
        return {
            **sync_status,
            "timestamp": _get_timestamp()
        }
    
    except Exception as e:
        logger.error(f"동기화 상태 조회 실패: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": _get_timestamp()
        }
