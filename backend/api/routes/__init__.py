# ═══════════════════════════════════════════════════════════════════════════
# Sigma9 REST API Routes - Main Router Aggregator
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     모든 도메인별 라우터를 조합하여 단일 APIRouter로 제공.
#     server.py에서 이 파일의 router를 import하여 앱에 포함합니다.
#
# 📌 구조:
#     routes/
#     ├── __init__.py     # 라우터 조합 (이 파일)
#     ├── models.py       # Pydantic 요청/응답 모델
#     ├── common.py       # 공용 유틸리티 (타임스탬프, 엔진 상태)
#     ├── status.py       # /status, /engine/status
#     ├── control.py      # /control, /kill-switch, /engine/*
#     ├── watchlist.py    # /watchlist/*
#     ├── position.py     # /positions
#     ├── strategy.py     # /strategies/*
#     ├── scanner.py      # /scanner/*, /gainers/*
#     ├── ignition.py     # /ignition/*
#     ├── chart.py        # /chart/*
#     ├── llm.py          # /oracle/*
#     ├── tier2.py        # /tier2/*
#     ├── zscore.py       # /zscore/*
#     └── sync.py         # /sync/*
#
# 📌 사용법:
#     from backend.api.routes import router
#     app.include_router(router, prefix="/api")
#
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter

# 모델 re-export (하위 호환성 유지)
from .models import (
    AnalysisRequest,
    ControlRequest,
    ControlResponse,
    EngineCommand,
    PositionItem,
    ServerStatus,
    StrategyInfo,
    Tier2PromoteRequest,
    WatchlistItem,
)

# 도메인별 라우터 import
from .status import router as status_router
from .control import router as control_router
from .watchlist import router as watchlist_router
from .position import router as position_router
from .strategy import router as strategy_router
from .scanner import router as scanner_router
from .ignition import router as ignition_router
from .chart import router as chart_router
from .llm import router as llm_router
from .tier2 import router as tier2_router
from .zscore import router as zscore_router
from .sync import router as sync_router

# 메인 라우터 생성
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# 라우터 조합
# ─────────────────────────────────────────────────────────────────────────────

# Status & Control (기본)
router.include_router(status_router, tags=["Status"])
router.include_router(control_router, tags=["Control"])

# Watchlist & Position
router.include_router(watchlist_router, tags=["Watchlist"])
router.include_router(position_router, tags=["Position"])

# Strategy
router.include_router(strategy_router, tags=["Strategy"])

# Scanner & Gainers
router.include_router(scanner_router, tags=["Scanner"])

# Ignition (실시간 모니터링)
router.include_router(ignition_router, tags=["Ignition"])

# Chart
router.include_router(chart_router, tags=["Chart"])

# LLM / Oracle
router.include_router(llm_router, tags=["LLM"])

# Tier 2 (Hot Zone)
router.include_router(tier2_router, tags=["Tier2"])

# Z-Score
router.include_router(zscore_router, tags=["ZScore"])

# Data Sync
router.include_router(sync_router, tags=["Sync"])


__all__ = [
    "router",
    # Models
    "EngineCommand",
    "ControlRequest",
    "ControlResponse",
    "ServerStatus",
    "WatchlistItem",
    "PositionItem",
    "StrategyInfo",
    "AnalysisRequest",
    "Tier2PromoteRequest",
]

