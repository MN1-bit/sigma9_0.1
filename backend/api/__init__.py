# ============================================================================
# Backend API Package
# ============================================================================
# 이 패키지는 REST API 및 WebSocket 엔드포인트를 담당합니다.
#
# 📦 포함 모듈:
#   - routes.py: REST API 라우터
#   - websocket.py: WebSocket 핸들러
#
# 📌 REST API 엔드포인트:
#   GET  /api/watchlist          - Watchlist 조회
#   GET  /api/positions          - 현재 포지션
#   POST /api/kill-switch        - 긴급 정지
#   POST /api/order              - 수동 주문
#   GET  /api/strategies         - 전략 목록
#   POST /api/strategies/{name}  - 전략 로드/리로드
#
# 📌 WebSocket 엔드포인트:
#   WS /ws/market                - 실시간 시장 데이터
#   WS /ws/trade                 - 거래 이벤트 스트림
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
