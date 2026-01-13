# ============================================================================
# Ticker Info Service - 티커 종합 정보 서비스
# ============================================================================
# [15-001] Ticker Info Viewer 구현
#
# 역할:
#   - Massive API를 통한 13개 카테고리 티커 정보 조회
#   - SQLite 캐싱으로 UX 최적화 (즉시 표시)
#   - 카테고리별 갱신 정책 적용
#
# 갱신 정책:
#   - Static (7일): Profile
#   - Semi-Static (1일): Float, IPO, Ticker Events
#   - Dynamic (1초): Snapshot, Short Interest/Volume (캐시 안함)
#   - Periodic (분기별): Financials, SEC Filings
#   - Real-time: News (캐시 안함)
#
# 원본: scripts/demos/ticker_info_demo.py에서 리팩터링
# ============================================================================

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from loguru import logger

from backend.models.ticker_info import TickerInfo

# .env 로드
load_dotenv()

# Massive API 설정
BASE_URL = "https://api.massive.com"


# =============================================================================
# 갱신 정책 설정
# =============================================================================
# 각 카테고리별 캐시 유효 기간 (초 단위)
REFRESH_POLICY: dict[str, int] = {
    # Static: 7일
    "profile": 7 * 24 * 3600,
    # Semi-Static: 1일
    "float": 24 * 3600,
    "ipo": 24 * 3600,
    "ticker_events": 24 * 3600,
    # Periodic: 90일 (분기)
    "financials": 90 * 24 * 3600,
    "filings": 7 * 24 * 3600,
    "dividends": 7 * 24 * 3600,
    "splits": 30 * 24 * 3600,
    "related": 7 * 24 * 3600,
    # Dynamic/Real-time: 캐시 안함 (0)
    "snapshot": 0,
    "short_interest": 0,
    "short_volume": 0,
    "news": 0,
}


class TickerInfoService:
    """
    티커 종합 정보 서비스.

    Massive API를 통해 13개 카테고리의 티커 정보를 조회하고,
    SQLite에 캐싱하여 빠른 UX를 제공합니다.

    Attributes:
        api_key: Massive API 키
        db_path: SQLite 캐시 DB 경로
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        db_path: str = "data/ticker_info_cache.db",
    ):
        """
        TickerInfoService 초기화.

        Args:
            api_key: Massive API 키 (없으면 환경변수에서 로드)
            db_path: SQLite 캐시 DB 경로
        """
        self.api_key = api_key or os.getenv("MASSIVE_API_KEY", "")
        self.db_path = db_path
        self._client: Optional[httpx.AsyncClient] = None

        # DB 초기화
        self._init_db()

        if not self.api_key:
            logger.warning("MASSIVE_API_KEY 미설정. API 호출이 실패합니다.")

    def _init_db(self) -> None:
        """SQLite 캐시 테이블 생성."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ticker_info_cache (
                    id INTEGER PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    category TEXT NOT NULL,
                    data TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    UNIQUE(ticker, category)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker_category
                ON ticker_info_cache(ticker, category)
            """)
            conn.commit()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 반환 (없으면 생성)."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """HTTP 클라이언트 종료."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # 캐시 로직
    # =========================================================================

    def _get_cached(self, ticker: str, category: str) -> Optional[dict[str, Any]]:
        """
        캐시에서 데이터 조회.

        Returns:
            캐시 데이터 또는 None (만료/미존재)
        """
        ttl = REFRESH_POLICY.get(category, 0)
        if ttl == 0:
            # Dynamic 카테고리는 캐시 안함
            return None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT data, fetched_at FROM ticker_info_cache
                WHERE ticker = ? AND category = ?
                """,
                (ticker.upper(), category),
            )
            row = cursor.fetchone()

        if not row:
            return None

        data_json, fetched_at_str = row
        fetched_at = datetime.fromisoformat(fetched_at_str)

        # TTL 체크
        if datetime.now() - fetched_at > timedelta(seconds=ttl):
            return None  # 만료됨

        try:
            return json.loads(data_json)
        except json.JSONDecodeError:
            return None

    def _set_cached(self, ticker: str, category: str, data: Any) -> None:
        """캐시에 데이터 저장."""
        ttl = REFRESH_POLICY.get(category, 0)
        if ttl == 0:
            # Dynamic 카테고리는 캐시 안함
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ticker_info_cache (ticker, category, data, fetched_at)
                VALUES (?, ?, ?, ?)
                """,
                (ticker.upper(), category, json.dumps(data), datetime.now().isoformat()),
            )
            conn.commit()

    # =========================================================================
    # API 호출 메서드
    # =========================================================================

    async def _api_get(
        self, url: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Massive API GET 요청.

        Args:
            url: API 엔드포인트 URL
            params: 쿼리 파라미터

        Returns:
            API 응답 JSON
        """
        client = await self._ensure_client()
        params = params or {}
        params["apiKey"] = self.api_key

        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            logger.debug(f"API 응답 {resp.status_code}: {url}")
            return {}
        except httpx.HTTPError as e:
            logger.warning(f"API 호출 실패: {e}")
            return {}

    async def _get_profile(self, ticker: str) -> dict[str, Any]:
        """기본 정보 (Ticker Details)."""
        url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
        data = await self._api_get(url)
        return data.get("results", {})

    async def _get_float(self, ticker: str) -> dict[str, Any]:
        """유동성 데이터 (Free Float)."""
        url = f"{BASE_URL}/stocks/vX/float"
        data = await self._api_get(url, {"ticker": ticker})
        results = data.get("results", [])
        return results[0] if results else {}

    async def _get_financials(self, ticker: str) -> list[dict[str, Any]]:
        """재무제표."""
        url = f"{BASE_URL}/vX/reference/financials"
        data = await self._api_get(url, {"ticker": ticker, "limit": 4})
        return data.get("results", [])

    async def _get_dividends(self, ticker: str) -> list[dict[str, Any]]:
        """배당 이력."""
        url = f"{BASE_URL}/v3/reference/dividends"
        data = await self._api_get(url, {"ticker": ticker, "limit": 5})
        return data.get("results", [])

    async def _get_splits(self, ticker: str) -> list[dict[str, Any]]:
        """주식 분할 이력."""
        url = f"{BASE_URL}/v3/reference/splits"
        data = await self._api_get(url, {"ticker": ticker, "limit": 5})
        return data.get("results", [])

    async def _get_filings(self, ticker: str, cik: Optional[str] = None) -> list[dict[str, Any]]:
        """SEC 공시."""
        if not cik:
            return []
        url = f"{BASE_URL}/v1/reference/sec/filings"
        data = await self._api_get(url, {"cik": cik, "limit": 5})
        return data.get("results", [])

    async def _get_news(self, ticker: str) -> list[dict[str, Any]]:
        """뉴스."""
        url = f"{BASE_URL}/v2/reference/news"
        data = await self._api_get(url, {"ticker": ticker, "limit": 5})
        results = data.get("results", [])
        # 간소화
        return [
            {
                "title": n.get("title"),
                "published": n.get("published_utc"),
                "source": n.get("publisher", {}).get("name"),
                "url": n.get("article_url"),
            }
            for n in results
        ]

    async def _get_related(self, ticker: str) -> list[dict[str, Any]]:
        """관련 기업."""
        url = f"{BASE_URL}/v1/related-companies/{ticker}"
        client = await self._ensure_client()
        try:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if resp.status_code == 200:
                return resp.json().get("results", [])
        except httpx.HTTPError:
            pass
        return []

    async def _get_snapshot(self, ticker: str) -> dict[str, Any]:
        """현재가 스냅샷."""
        url = f"{BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        client = await self._ensure_client()
        try:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if resp.status_code == 200:
                ticker_data = resp.json().get("ticker", {})
                return {
                    "price": ticker_data.get("day", {}).get("c"),
                    "change_pct": ticker_data.get("todaysChangePerc"),
                    "volume": ticker_data.get("day", {}).get("v"),
                    "prev_close": ticker_data.get("prevDay", {}).get("c"),
                }
        except httpx.HTTPError:
            pass
        return {}

    async def _get_short_interest(self, ticker: str) -> list[dict[str, Any]]:
        """공매도 잔고."""
        url = f"{BASE_URL}/vX/reference/short-interest/ticker/{ticker}"
        data = await self._api_get(url, {"limit": 5})
        return data.get("results", [])

    async def _get_short_volume(self, ticker: str) -> list[dict[str, Any]]:
        """공매도 거래량."""
        url = f"{BASE_URL}/vX/reference/short-volume/{ticker}"
        data = await self._api_get(url, {"limit": 5})
        return data.get("results", [])

    async def _get_ipo(self, ticker: str) -> dict[str, Any]:
        """IPO 정보."""
        url = f"{BASE_URL}/vX/reference/ipos"
        data = await self._api_get(url, {"ticker": ticker, "limit": 1})
        results = data.get("results", [])
        return results[0] if results else {}

    async def _get_ticker_events(self, ticker: str) -> list[dict[str, Any]]:
        """티커 이벤트."""
        url = f"{BASE_URL}/vX/reference/tickers/{ticker}/events"
        client = await self._ensure_client()
        try:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if resp.status_code == 200:
                return resp.json().get("results", {}).get("events", [])
        except httpx.HTTPError:
            pass
        return []

    # =========================================================================
    # 메인 메서드
    # =========================================================================

    async def get_ticker_info(
        self, ticker: str, force_refresh: bool = False
    ) -> TickerInfo:
        """
        티커 종합 정보 조회.

        캐시 우선 조회 후, 만료되었거나 force_refresh=True면 API 호출.
        Dynamic 카테고리(snapshot, short, news)는 항상 API 호출.

        Args:
            ticker: 종목 심볼
            force_refresh: 강제 갱신 여부

        Returns:
            TickerInfo: 종합 티커 정보
        """
        ticker = ticker.upper()
        info = TickerInfo(ticker=ticker)

        # Profile 먼저 조회 (CIK 필요)
        if force_refresh:
            info.profile = await self._get_profile(ticker)
            self._set_cached(ticker, "profile", info.profile)
        else:
            cached = self._get_cached(ticker, "profile")
            if cached:
                info.profile = cached
            else:
                info.profile = await self._get_profile(ticker)
                self._set_cached(ticker, "profile", info.profile)

        cik = info.profile.get("cik")

        # 나머지 카테고리 병렬 조회
        async def fetch_or_cache(category: str, fetch_fn) -> Any:
            if force_refresh or REFRESH_POLICY.get(category, 0) == 0:
                return await fetch_fn()
            cached = self._get_cached(ticker, category)
            if cached is not None:
                return cached
            result = await fetch_fn()
            self._set_cached(ticker, category, result)
            return result

        # 병렬 실행
        results = await asyncio.gather(
            fetch_or_cache("float", lambda: self._get_float(ticker)),
            fetch_or_cache("financials", lambda: self._get_financials(ticker)),
            fetch_or_cache("dividends", lambda: self._get_dividends(ticker)),
            fetch_or_cache("splits", lambda: self._get_splits(ticker)),
            fetch_or_cache("filings", lambda: self._get_filings(ticker, cik)),
            fetch_or_cache("news", lambda: self._get_news(ticker)),
            fetch_or_cache("related", lambda: self._get_related(ticker)),
            fetch_or_cache("snapshot", lambda: self._get_snapshot(ticker)),
            fetch_or_cache("short_interest", lambda: self._get_short_interest(ticker)),
            fetch_or_cache("short_volume", lambda: self._get_short_volume(ticker)),
            fetch_or_cache("ipo", lambda: self._get_ipo(ticker)),
            fetch_or_cache("ticker_events", lambda: self._get_ticker_events(ticker)),
            return_exceptions=True,
        )

        # 결과 할당
        info.float_data = results[0] if not isinstance(results[0], Exception) else {}
        info.financials = results[1] if not isinstance(results[1], Exception) else []
        info.dividends = results[2] if not isinstance(results[2], Exception) else []
        info.splits = results[3] if not isinstance(results[3], Exception) else []
        info.filings = results[4] if not isinstance(results[4], Exception) else []
        info.news = results[5] if not isinstance(results[5], Exception) else []
        info.related_companies = results[6] if not isinstance(results[6], Exception) else []
        info.snapshot = results[7] if not isinstance(results[7], Exception) else {}
        info.short_interest = results[8] if not isinstance(results[8], Exception) else []
        info.short_volume = results[9] if not isinstance(results[9], Exception) else []
        info.ipo = results[10] if not isinstance(results[10], Exception) else {}
        info.ticker_events = results[11] if not isinstance(results[11], Exception) else []

        logger.debug(f"TickerInfo 조회 완료: {ticker}")
        return info

    async def get_dynamic_data(self, ticker: str) -> dict[str, Any]:
        """
        Dynamic 데이터만 조회 (1초 갱신용).

        Snapshot, Short Interest, Short Volume만 반환합니다.
        캐싱 없이 항상 API 호출.

        Args:
            ticker: 종목 심볼

        Returns:
            Dynamic 데이터 딕셔너리
        """
        ticker = ticker.upper()

        snapshot, short_interest, short_volume = await asyncio.gather(
            self._get_snapshot(ticker),
            self._get_short_interest(ticker),
            self._get_short_volume(ticker),
            return_exceptions=True,
        )

        return {
            "snapshot": snapshot if not isinstance(snapshot, Exception) else {},
            "short_interest": short_interest if not isinstance(short_interest, Exception) else [],
            "short_volume": short_volume if not isinstance(short_volume, Exception) else [],
        }
