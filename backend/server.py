# ============================================================================
# Sigma9 Backend Server - FastAPI 메인 진입점
# ============================================================================
# 이 파일은 AWS EC2에서 실행될 백엔드 서버의 진입점입니다.
# 
# 📌 역할:
#   - FastAPI 애플리케이션 인스턴스 생성
#   - API 라우터 등록 (REST + WebSocket)
#   - 미들웨어 설정 (CORS, 인증, 로깅 등)
#   - 서버 시작 시 초기화 로직 (IBKR 연결, 전략 로드 등)
#
# 🔗 관련 파일:
#   - api/routes.py: REST API 엔드포인트 정의
#   - api/websocket.py: WebSocket 핸들러
#   - core/engine.py: 트레이딩 엔진
#
# TODO (Step 5.x):
#   - [ ] FastAPI App 인스턴스 생성
#   - [ ] 라우터 등록
#   - [ ] 미들웨어 설정
#   - [ ] lifespan 이벤트 핸들러 (startup/shutdown)
# ============================================================================

"""
Sigma9 Backend Server

이 모듈은 Sigma9 트레이딩 시스템의 백엔드 서버 진입점입니다.
FastAPI를 사용하여 REST API와 WebSocket 서비스를 제공합니다.

Example:
    서버 실행 방법:
    $ uvicorn backend.server:app --host 0.0.0.0 --port 8000
"""

# TODO: 구현 예정 (Step 5.x)
# from fastapi import FastAPI
# from api.routes import router as api_router
# from api.websocket import router as ws_router

if __name__ == "__main__":
    # 개발 모드에서 직접 실행 시
    # uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
    print("Sigma9 Backend Server - Step 1.1 Skeleton")
    print("실제 구현은 Step 5.x에서 진행됩니다.")
