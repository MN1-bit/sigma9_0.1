"""
Sigma9 Backend Server Entry Point
==================================
독립 실행 진입점.

📌 실행 방법:
    python -m backend
    
    또는 환경변수로 설정 오버라이드:
    SIGMA9_SERVER_PORT=9000 python -m backend
"""

import uvicorn
from backend.server import app
from backend.core.config_loader import load_server_config


def main():
    """서버 메인 진입점"""
    # 설정 로드
    config = load_server_config()
    
    print("=" * 60)
    print("    🎯 Sigma9 Trading Engine Server")
    print("=" * 60)
    print(f"    Host: {config.server.host}")
    print(f"    Port: {config.server.port}")
    print(f"    Debug: {config.server.debug}")
    print(f"    Reload: {config.server.reload}")
    print("=" * 60)
    
    # Uvicorn 실행
    uvicorn.run(
        "backend.server:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        workers=config.server.workers if not config.server.reload else 1,
        log_level="info" if config.server.debug else "warning",
    )


if __name__ == "__main__":
    main()
