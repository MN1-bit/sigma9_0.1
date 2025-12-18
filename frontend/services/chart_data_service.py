# ============================================================================
# Chart Data Service - 백엔드 → 차트 데이터 변환
# ============================================================================
# 📌 이 파일의 역할:
#   - MarketDB에서 OHLCV 데이터 조회
#   - TechnicalAnalysis를 사용해 지표 계산
#   - 차트 위젯에 전달할 형식으로 변환
#
# 📖 사용법:
#   >>> service = ChartDataService()
#   >>> data = await service.get_chart_data("AAPL", days=100)
#   >>> chart.set_candlestick_data(data['candles'])
# ============================================================================

"""
Chart Data Service

백엔드의 MarketDB와 TechnicalAnalysis를 연결하여
차트 위젯에 필요한 데이터를 준비합니다.
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime

# 백엔드 모듈 임포트
try:
    from backend.data.database import MarketDB, DailyBar
    from backend.core.technical_analysis import TechnicalAnalysis, DynamicStopLoss
except ImportError:
    # 테스트 환경에서 임포트 실패 시
    MarketDB = None
    TechnicalAnalysis = None


class ChartDataService:
    """
    차트 데이터 서비스
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    이 서비스는 데이터베이스와 차트 사이의 통역사입니다.
    
    1. 데이터베이스에서 주가 데이터를 가져옵니다
    2. 기술적 지표 (VWAP, MA, ATR)를 계산합니다
    3. 차트가 이해할 수 있는 형식으로 변환합니다
    """
    
    def __init__(self, db_path: str = "data/market_data.db"):
        """
        서비스 초기화
        
        Args:
            db_path: MarketDB 경로
        """
        self.db_path = db_path
        self._db: Optional[MarketDB] = None
    
    async def _get_db(self) -> MarketDB:
        """DB 인스턴스 lazy loading"""
        if self._db is None:
            if MarketDB is None:
                raise ImportError("MarketDB를 임포트할 수 없습니다")
            self._db = MarketDB(self.db_path)
            await self._db.initialize()
        return self._db
    
    async def get_chart_data(
        self,
        ticker: str,
        timeframe: str = "1D",  # "1m", "5m", "15m", "1h", "1D"
        days: int = 100,
        calculate_indicators: bool = True
    ) -> Dict:
        """
        차트에 필요한 모든 데이터 조회 및 계산
        
        Args:
            ticker: 종목 심볼 (예: "AAPL")
            timeframe: 타임프레임 ("1m", "5m", "15m", "1h", "1D")
            days: 조회할 일수
            calculate_indicators: 지표 계산 여부
        
        Returns:
            {
                "ticker": str,
                "timeframe": str,
                "candles": [{"time": timestamp, "open": float, ...}, ...],
                "volume": [{"time": timestamp, "volume": int, "is_up": bool}, ...],
                "vwap": [{"time": timestamp, "value": float}, ...],
                "sma_20": [{"time": timestamp, "value": float}, ...],
                "ema_9": [{"time": timestamp, "value": float}, ...],
            }
        """
        # Intraday 타임프레임 처리 (API 호출)
        if timeframe != "1D":
            return await self._get_intraday_data(ticker, timeframe, days)
        
        # Daily 타임프레임 처리 (DB 조회)
        return await self._get_daily_data(ticker, days, calculate_indicators)
    
    async def _get_intraday_data(
        self,
        ticker: str,
        timeframe: str,
        days: int = 2
    ) -> Dict:
        """
        Intraday 차트 데이터 조회 (API 호출)
        
        Args:
            ticker: 종목 심볼
            timeframe: 타임프레임 ("1m", "5m", "15m", "1h")
            days: 조회 일수 (최대 10일)
        """
        import os
        import httpx
        
        # API days 제한 (최대 10일)
        days = min(days, 10)
        
        # 타임프레임 매핑
        tf_map = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}
        multiplier = tf_map.get(timeframe, 5)
        
        # Backend API 호출
        api_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
        url = f"{api_url}/api/chart/intraday/{ticker}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params={
                    "timeframe": multiplier,
                    "days": days
                })
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            print(f"⚠️ Intraday API 호출 실패: {e}")
            return {"ticker": ticker, "timeframe": timeframe, "candles": [], "volume": []}
        
        candles = data.get("candles", [])
        
        # Volume 데이터 생성
        volumes = []
        for i, candle in enumerate(candles):
            is_up = candle.get("close", 0) >= candle.get("open", 0)
            volumes.append({
                "time": candle.get("time"),
                "volume": candle.get("volume", 0),
                "is_up": is_up,
            })
        
        return {
            "ticker": ticker,
            "timeframe": timeframe,
            "candles": candles,
            "volume": volumes,
        }
    
    async def _get_daily_data(
        self,
        ticker: str,
        days: int = 100,
        calculate_indicators: bool = True
    ) -> Dict:
        """
        Daily 차트 데이터 조회 (DB 조회)
        """
        db = await self._get_db()
        
        # 1. DB에서 일봉 데이터 조회
        bars = await db.get_daily_bars(ticker, days=days)
        
        if not bars:
            return {"ticker": ticker, "timeframe": "1D", "candles": [], "volume": []}
        
        # 날짜 오름차순 정렬 (DB는 내림차순으로 반환)
        bars = list(reversed(bars))
        
        # 2. 캔들스틱 데이터 변환
        candles = self._bars_to_candles(bars)
        volumes = self._bars_to_volumes(bars)
        
        result = {
            "ticker": ticker,
            "timeframe": "1D",
            "candles": candles,
            "volume": volumes,
        }
        
        # 3. 지표 계산
        if calculate_indicators and TechnicalAnalysis:
            closes = [b.close for b in bars]
            highs = [b.high for b in bars]
            lows = [b.low for b in bars]
            bar_volumes = [b.volume for b in bars]
            
            # VWAP (DB에 이미 있으면 사용, 없으면 계산)
            if bars[0].vwap:
                result["vwap"] = [
                    {"time": self._date_to_timestamp(b.date), "value": b.vwap}
                    for b in bars if b.vwap
                ]
            else:
                # 간이 VWAP 계산
                result["vwap"] = self._calculate_rolling_vwap(bars)
            
            # SMA 20
            result["sma_20"] = self._calculate_sma_series(bars, period=20)
            
            # EMA 9
            result["ema_9"] = self._calculate_ema_series(bars, period=9)
        
        return result
    
    def _bars_to_candles(self, bars: List[DailyBar]) -> List[Dict]:
        """DailyBar 리스트를 캔들 딕셔너리로 변환"""
        candles = []
        for bar in bars:
            candles.append({
                "time": self._date_to_timestamp(bar.date),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
            })
        return candles
    
    def _bars_to_volumes(self, bars: List[DailyBar]) -> List[Dict]:
        """DailyBar 리스트를 Volume 딕셔너리로 변환"""
        volumes = []
        for bar in bars:
            is_up = bar.close >= bar.open
            volumes.append({
                "time": self._date_to_timestamp(bar.date),
                "volume": bar.volume,
                "is_up": is_up,
            })
        return volumes
    
    def _date_to_timestamp(self, date_str: str) -> float:
        """YYYY-MM-DD 문자열을 Unix timestamp로 변환"""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.timestamp()
    
    def _calculate_rolling_vwap(self, bars: List[DailyBar]) -> List[Dict]:
        """단순 VWAP 계산 (TP * Volume / Cumsum Volume)"""
        result = []
        cumulative_tp_vol = 0
        cumulative_vol = 0
        
        for bar in bars:
            tp = (bar.high + bar.low + bar.close) / 3
            cumulative_tp_vol += tp * bar.volume
            cumulative_vol += bar.volume
            
            vwap = cumulative_tp_vol / cumulative_vol if cumulative_vol > 0 else bar.close
            result.append({
                "time": self._date_to_timestamp(bar.date),
                "value": vwap
            })
        
        return result
    
    def _calculate_sma_series(self, bars: List[DailyBar], period: int = 20) -> List[Dict]:
        """SMA 시계열 계산"""
        result = []
        closes = [b.close for b in bars]
        
        for i in range(len(bars)):
            if i < period - 1:
                continue
            sma = sum(closes[i - period + 1:i + 1]) / period
            result.append({
                "time": self._date_to_timestamp(bars[i].date),
                "value": sma
            })
        
        return result
    
    def _calculate_ema_series(self, bars: List[DailyBar], period: int = 9) -> List[Dict]:
        """EMA 시계열 계산"""
        result = []
        closes = [b.close for b in bars]
        
        if len(closes) < period:
            return result
        
        # 첫 EMA는 SMA로 시작
        ema = sum(closes[:period]) / period
        multiplier = 2 / (period + 1)
        
        for i in range(period - 1, len(bars)):
            if i == period - 1:
                ema = sum(closes[:period]) / period
            else:
                ema = (closes[i] - ema) * multiplier + ema
            
            result.append({
                "time": self._date_to_timestamp(bars[i].date),
                "value": ema
            })
        
        return result
    
    async def close(self):
        """리소스 정리"""
        if self._db:
            await self._db.close()
            self._db = None


# ═══════════════════════════════════════════════════════════════════════════
# 동기 래퍼 (GUI용)
# ═══════════════════════════════════════════════════════════════════════════

def get_chart_data_sync(
    ticker: str, 
    timeframe: str = "1D",  # Step 2.7: timeframe 지원
    days: int = 100, 
    db_path: str = "data/market_data.db"
) -> Dict:
    """
    동기 방식으로 차트 데이터 조회 (GUI에서 간단히 사용)
    
    Args:
        ticker: 종목 심볼
        timeframe: 타임프레임 ("1m", "5m", "15m", "1h", "1D")
        days: 조회 일수 (Intraday는 자동으로 5일로 제한됨)
        db_path: DB 파일 경로
    
    Note:
        이 함수는 새 이벤트 루프를 생성하므로 이미 실행 중인 루프가 있으면
        asyncio.run_coroutine_threadsafe를 사용하세요.
    """
    # Intraday는 days 제한 (API 제한)
    if timeframe != "1D":
        days = min(days, 5)  # 최대 5일
    
    async def _fetch():
        service = ChartDataService(db_path)
        try:
            return await service.get_chart_data(ticker, timeframe=timeframe, days=days)
        finally:
            await service.close()
    
    return asyncio.run(_fetch())

