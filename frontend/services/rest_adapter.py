"""
Sigma9 REST API Adapter
========================
HTTP 기반 Backend REST API 클라이언트.

📌 사용법:
    from frontend.services.rest_adapter import RestAdapter
    
    adapter = RestAdapter("http://localhost:8000")
    status = await adapter.get_status()
    await adapter.control_engine("start")

📌 지원 엔드포인트:
    - GET  /api/status
    - POST /api/control
    - GET  /api/watchlist
    - GET  /api/positions
    - POST /api/kill-switch
    - GET  /api/strategies
    - POST /api/strategies/{name}/reload
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from loguru import logger

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("⚠️ httpx not installed. Run: pip install httpx")


@dataclass
class ServerStatus:
    """서버 상태 데이터"""
    server: str = "unknown"
    engine: str = "unknown"
    ibkr: str = "unknown"
    scheduler: str = "unknown"
    uptime_seconds: float = 0
    active_positions: int = 0
    active_orders: int = 0


class RestAdapter:
    """
    REST API 클라이언트
    
    📌 기능:
        - 서버 상태 조회
        - 엔진 제어 (start/stop/kill)
        - Watchlist/Positions 조회
        - 전략 관리
    
    📌 에러 처리:
        - 연결 실패 시 None 또는 빈 리스트 반환
        - 타임아웃 처리
        - JSON 파싱 에러 처리
    """
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        REST Adapter 초기화
        
        Args:
            base_url: 서버 기본 URL (e.g., "http://localhost:8000")
            timeout: 요청 타임아웃 (초)
        """
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required. Run: pip install httpx")
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.debug(f"RestAdapter initialized: {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """AsyncClient 싱글톤 반환"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
        return self._client
    
    async def close(self):
        """클라이언트 종료"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    # ─────────────────────────────────────────────────────────────
    # Health & Status
    # ─────────────────────────────────────────────────────────────
    
    async def health_check(self) -> bool:
        """
        서버 헬스체크
        
        Returns:
            bool: 서버 정상 여부
        """
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    async def get_status(self) -> Optional[ServerStatus]:
        """
        서버 상태 조회
        
        Returns:
            ServerStatus: 서버 상태 객체 (실패 시 None)
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/status")
            
            if response.status_code == 200:
                data = response.json()
                return ServerStatus(
                    server=data.get("server", "unknown"),
                    engine=data.get("engine", "unknown"),
                    ibkr=data.get("ibkr", "unknown"),
                    scheduler=data.get("scheduler", "unknown"),
                    uptime_seconds=data.get("uptime_seconds", 0),
                    active_positions=data.get("active_positions", 0),
                    active_orders=data.get("active_orders", 0)
                )
            else:
                logger.warning(f"get_status failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"get_status error: {e}")
            return None
    
    # ─────────────────────────────────────────────────────────────
    # Engine Control
    # ─────────────────────────────────────────────────────────────
    
    async def control_engine(self, command: str) -> Dict[str, Any]:
        """
        엔진 제어
        
        Args:
            command: "start" | "stop" | "kill"
        
        Returns:
            dict: 응답 데이터 {"status": "accepted", "command": "...", "message": "..."}
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/control",
                json={"command": command}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"control_engine error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def start_engine(self) -> Dict[str, Any]:
        """엔진 시작"""
        return await self.control_engine("start")
    
    async def stop_engine(self) -> Dict[str, Any]:
        """엔진 정지"""
        return await self.control_engine("stop")
    
    async def kill_switch(self) -> Dict[str, Any]:
        """
        긴급 정지 (Kill Switch)
        
        모든 주문 취소 + 포지션 청산
        """
        try:
            client = await self._get_client()
            response = await client.post("/api/kill-switch")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"kill_switch error: {e}")
            return {"status": "error", "message": str(e)}
    
    # ─────────────────────────────────────────────────────────────
    # Watchlist & Positions
    # ─────────────────────────────────────────────────────────────
    
    async def get_watchlist(self) -> List[Dict[str, Any]]:
        """
        Watchlist 조회
        
        Returns:
            list: Watchlist 항목 리스트
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/watchlist")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"get_watchlist failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"get_watchlist error: {e}")
            return []
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        포지션 조회
        
        Returns:
            list: 포지션 항목 리스트
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/positions")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"get_positions failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"get_positions error: {e}")
            return []
    
    # ─────────────────────────────────────────────────────────────
    # Strategy Management
    # ─────────────────────────────────────────────────────────────
    
    async def get_strategies(self) -> List[Dict[str, Any]]:
        """
        전략 목록 조회
        
        Returns:
            list: 전략 정보 리스트
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/strategies")
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            logger.error(f"get_strategies error: {e}")
            return []
    
    async def reload_strategy(self, name: str) -> Dict[str, Any]:
        """
        전략 리로드
        
        Args:
            name: 전략 이름
        
        Returns:
            dict: 응답 데이터
        """
        try:
            client = await self._get_client()
            response = await client.post(f"/api/strategies/{name}/reload")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"reload_strategy error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def run_scanner(self, strategy_name: str = "seismograph") -> Dict[str, Any]:
        """
        Scanner 실행 요청
        
        Args:
            strategy_name: 전략 이름
        
        Returns:
            dict: 응답 데이터 {"status": "success", "item_count": ...}
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/scanner/run",
                params={"strategy_name": strategy_name}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"run_scanner error: {e}")
            return {"status": "error", "message": str(e)}
    
    # ─────────────────────────────────────────────────────────────
    # Scheduler Control (Backend Tab용)
    # ─────────────────────────────────────────────────────────────
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """
        스케줄러 상태 조회
        
        Returns:
            dict: 스케줄러 상태 및 설정
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/scheduler/status")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            logger.debug(f"get_scheduler_status error: {e}")
            return {}
    
    async def update_scheduler_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        스케줄러 설정 업데이트
        
        Args:
            config: 스케줄러 설정 딕셔너리
        
        Returns:
            dict: 응답 데이터
        """
        try:
            client = await self._get_client()
            response = await client.post("/api/scheduler/config", json=config)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"update_scheduler_config error: {e}")
            return {"status": "error", "message": str(e)}
