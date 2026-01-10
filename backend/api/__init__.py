# ============================================================================
# Backend API Package
# ============================================================================
# 이 패키지는 REST API 및 WebSocket 엔드포인트를 담당합니다.
#
# 📦 구조:
#   - routes/           : REST API 라우터 (도메인별 분리)
#     ├── __init__.py   : 라우터 조합
#     ├── models.py     : 공유 Pydantic 모델
#     ├── common.py     : 공용 유틸리티
#     ├── status.py     : /status, /engine/status
#     ├── control.py    : /control, /kill-switch, /engine/*
#     ├── watchlist.py  : /watchlist/*
#     ├── position.py   : /positions
#     ├── strategy.py   : /strategies/*
#     ├── scanner.py    : /scanner/*, /gainers/*
#     ├── ignition.py   : /ignition/*
#     ├── chart.py      : /chart/*
#     ├── llm.py        : /oracle/*
#     ├── tier2.py      : /tier2/*
#     ├── zscore.py     : /zscore/*
#     └── sync.py       : /sync/*
#   - websocket.py      : WebSocket 핸들러
#
# 📌 사용법:
#     from backend.api.routes import router
#     app.include_router(router, prefix="/api")
#
# 📌 [06-001] Refactored:
#     routes.py (1,194줄) → routes/ 디렉터리 (15개 파일)
# ============================================================================

"""
Sigma9 API Package

REST API 및 WebSocket 엔드포인트를 정의하는 패키지입니다.
FastAPI 라우터들이 이 패키지에 위치합니다.
"""

__all__ = [
    # Step 5.x에서 추가 예정
    # "api_router",
    # "ws_router",
]
