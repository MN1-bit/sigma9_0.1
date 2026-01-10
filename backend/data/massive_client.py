# ============================================================================
# Massive.com API Client
# ============================================================================
# 📌 이 파일의 역할:
#   - Massive.com REST API 클라이언트
#   - Rate Limit 핸들링 (Free Tier: 5 req/min)
#   - Grouped Daily API로 전체 미국 주식 일봉 조회
#
# 📡 사용 API:
#   - Grouped Daily: /v2/aggs/grouped/locale/us/market/stocks/{date}
#     → 특정 날짜의 전체 미국 주식 OHLCV 데이터 (1회 호출로 5000+ 종목)
#
# 🔒 Rate Limiting:
#   - Free Tier: 5 requests/minute
#   - aiolimiter 라이브러리로 정확한 제한
#   - Exponential Backoff로 실패 시 재시도
#
# 📖 사용 예시:
#   >>> client = MassiveClient(api_key="your_key")
#   >>> bars = await client.fetch_grouped_daily("2024-12-17")
#   >>> print(f"{len(bars)}개 종목 데이터 수신")
# ============================================================================

import asyncio
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger

# aiolimiter가 없을 경우를 대비한 폴백
try:
    from aiolimiter import AsyncLimiter

    HAS_AIOLIMITER = True
except ImportError:
    HAS_AIOLIMITER = False
    logger.warning(
        "⚠️ aiolimiter 미설치. Rate Limiting이 동작하지 않습니다. pip install aiolimiter"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 예외 클래스
# ═══════════════════════════════════════════════════════════════════════════


class MassiveAPIError(Exception):
    """
    Massive API 에러

    API 호출 실패 시 발생합니다.
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class MassiveRateLimitError(MassiveAPIError):
    """
    Rate Limit 초과 에러

    Free Tier 제한 (5 req/min)을 초과했을 때 발생합니다.
    """

    pass


# ═══════════════════════════════════════════════════════════════════════════
# MassiveClient 클래스
# ═══════════════════════════════════════════════════════════════════════════


class MassiveClient:
    """
    Massive.com API 클라이언트

    Rate Limit를 준수하면서 Massive API를 호출합니다.
    Free Tier에서는 분당 5회 호출로 제한됩니다.

    Attributes:
        api_key: Massive.com API 키
        base_url: API 기본 URL
        rate_limiter: Rate Limit 제어기
        retry_count: 실패 시 재시도 횟수
        retry_delay: 재시도 대기 시간 (초)

    Example:
        >>> client = MassiveClient(api_key="your_api_key")
        >>>
        >>> # 특정 날짜의 전체 시장 데이터 조회
        >>> bars = await client.fetch_grouped_daily("2024-12-17")
        >>> print(f"{len(bars)}개 종목")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.massive.com",  # Massive.com → massive.com (deprecated)
        rate_limit: int = 100,  # requests per minute (유료 플랜 기준)
        retry_count: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        MassiveClient 초기화

        Args:
            api_key: Massive.com API 키 (환경변수 MASSIVE_API_KEY 권장)
            base_url: API 기본 URL
            rate_limit: 분당 최대 요청 수 (Free: 5, 유료: 100+)
            retry_count: 실패 시 재시도 횟수
            retry_delay: 첫 번째 재시도 대기 시간 (Exponential Backoff)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.retry_count = retry_count
        self.retry_delay = retry_delay

        # ─────────────────────────────────────────────────────────────────
        # Rate Limiter 설정
        # - 60초 동안 rate_limit 회 호출 가능
        # ─────────────────────────────────────────────────────────────────
        if HAS_AIOLIMITER:
            self.rate_limiter = AsyncLimiter(rate_limit, 60)
        else:
            self.rate_limiter = None

        # ─────────────────────────────────────────────────────────────────
        # HTTP 클라이언트 (재사용을 위해 인스턴스 변수로 저장)
        # ─────────────────────────────────────────────────────────────────
        self._client: Optional[httpx.AsyncClient] = None

        logger.debug(f"🔌 MassiveClient 초기화: rate_limit={rate_limit}/min")

    # ═══════════════════════════════════════════════════════════════════════
    # Context Manager (async with 지원)
    # ═══════════════════════════════════════════════════════════════════════

    async def __aenter__(self) -> "MassiveClient":
        """async with 진입 시 HTTP 클라이언트 생성"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 30초 타임아웃
            # Massive.com API는 apiKey 쿼리 파라미터 방식 사용
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """async with 종료 시 HTTP 클라이언트 정리"""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ═══════════════════════════════════════════════════════════════════════
    # 내부 헬퍼 메서드
    # ═══════════════════════════════════════════════════════════════════════

    async def _ensure_client(self) -> httpx.AsyncClient:
        """
        HTTP 클라이언트 반환 (없으면 생성)

        async with를 사용하지 않을 경우를 위한 폴백입니다.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                # Massive.com API는 apiKey 쿼리 파라미터 방식 사용
            )
        return self._client

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> dict:
        """
        Rate Limit + Retry 로직이 적용된 API 호출

        Args:
            method: HTTP 메서드 (GET, POST 등)
            url: 요청 URL
            **kwargs: httpx 요청에 전달할 추가 인자

        Returns:
            dict: API 응답 JSON

        Raises:
            MassiveAPIError: API 호출 실패 시
            MassiveRateLimitError: Rate Limit 초과 시
        """
        client = await self._ensure_client()

        # ─────────────────────────────────────────────────────────────────
        # Massive.com API 인증: apiKey 쿼리 파라미터 방식
        # ─────────────────────────────────────────────────────────────────
        if "params" not in kwargs:
            kwargs["params"] = {}
        kwargs["params"]["apiKey"] = self.api_key

        for attempt in range(self.retry_count + 1):
            # ─────────────────────────────────────────────────────────────
            # Rate Limit 대기
            # ─────────────────────────────────────────────────────────────
            if self.rate_limiter:
                await self.rate_limiter.acquire()

            try:
                response = await client.request(method, url, **kwargs)

                # ─────────────────────────────────────────────────────────
                # Rate Limit 에러 (429)
                # ─────────────────────────────────────────────────────────
                if response.status_code == 429:
                    if attempt < self.retry_count:
                        delay = self.retry_delay * (2**attempt)  # Exponential Backoff
                        logger.warning(
                            f"⏳ Rate Limit 초과. {delay:.1f}초 후 재시도... ({attempt + 1}/{self.retry_count})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise MassiveRateLimitError("Rate Limit 초과", status_code=429)

                # ─────────────────────────────────────────────────────────
                # 기타 HTTP 에러
                # ─────────────────────────────────────────────────────────
                if response.status_code >= 400:
                    error_msg = f"API 에러: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg = f"API 에러: {error_data['error']}"
                    except Exception:
                        pass
                    raise MassiveAPIError(error_msg, status_code=response.status_code)

                return response.json()

            except httpx.HTTPError as e:
                if attempt < self.retry_count:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"🔄 네트워크 에러. {delay:.1f}초 후 재시도... ({attempt + 1}/{self.retry_count})"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise MassiveAPIError(f"네트워크 에러: {e}")

        raise MassiveAPIError("최대 재시도 횟수 초과")

    # ═══════════════════════════════════════════════════════════════════════
    # API 메서드
    # ═══════════════════════════════════════════════════════════════════════

    async def fetch_grouped_daily(self, date: str) -> list[dict]:
        """
        특정 날짜의 전체 미국 주식 일봉 데이터 조회

        Massive Grouped Daily API를 사용합니다.
        1회 호출로 5000개 이상의 종목 데이터를 가져올 수 있습니다.

        Args:
            date: 조회할 날짜 (YYYY-MM-DD 형식)

        Returns:
            list[dict]: 일봉 데이터 리스트
                각 딕셔너리는 다음 키를 가집니다:
                - ticker: 종목 심볼
                - date: 날짜
                - open, high, low, close: 가격
                - volume: 거래량
                - vwap: 거래량 가중 평균가
                - transactions: 체결 건수

        Example:
            >>> bars = await client.fetch_grouped_daily("2024-12-17")
            >>> print(f"{len(bars)}개 종목 데이터")
            >>> print(bars[0])
            # {'ticker': 'AAPL', 'date': '2024-12-17', 'open': 150.0, ...}

        Note:
            - 주말이나 휴일에는 데이터가 없습니다.
            - Free Tier에서는 2년 전까지의 데이터만 조회 가능합니다.
        """
        url = f"{self.base_url}/v2/aggs/grouped/locale/us/market/stocks/{date}"

        logger.debug(f"📡 Grouped Daily API 호출: {date}")

        data = await self._request_with_retry("GET", url)

        # ─────────────────────────────────────────────────────────────────
        # 응답 파싱
        # Massive API 응답 형식:
        # {
        #   "status": "OK",
        #   "resultsCount": 5000,
        #   "results": [
        #     {"T": "AAPL", "o": 150.0, "h": 152.5, "l": 149.0, "c": 151.0, "v": 50000000, ...}
        #   ]
        # }
        # ─────────────────────────────────────────────────────────────────
        if data.get("status") != "OK":
            logger.warning(f"⚠️ API 응답 상태: {data.get('status')}")
            return []

        results = data.get("results", [])

        if not results:
            logger.info(f"📭 {date}에 데이터 없음 (휴일/주말)")
            return []

        # ─────────────────────────────────────────────────────────────────
        # 데이터 정규화 (Massive 형식 → 우리 형식)
        # ─────────────────────────────────────────────────────────────────
        bars = []
        for item in results:
            try:
                open_val = float(item.get("o", 0))
                high_val = float(item.get("h", 0))
                low_val = float(item.get("l", 0))
                close_val = float(item.get("c", 0))

                # 가격이 0 이하이면 데이터 오류로 간주하고 건너뜀
                if open_val <= 0 or high_val <= 0 or low_val <= 0 or close_val <= 0:
                    continue

                bar = {
                    "ticker": item["T"],  # Ticker
                    "date": date,
                    "open": open_val,
                    "high": high_val,
                    "low": low_val,
                    "close": close_val,
                    "volume": int(item.get("v", 0)),
                    "vwap": float(item.get("vw", 0)) if item.get("vw") else None,
                    "transactions": int(item.get("n", 0)) if item.get("n") else None,
                }
                bars.append(bar)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"⚠️ 데이터 파싱 실패: {item.get('T', 'UNKNOWN')} - {e}")
                continue

        logger.info(f"✅ {date}: {len(bars)}개 종목 데이터 수신")
        return bars

    async def fetch_ticker_details(self, ticker: str) -> Optional[dict]:
        """
        특정 종목의 상세 정보 조회

        Massive Ticker Details API를 사용합니다.
        시가총액, Float 등 펀더멘털 정보를 가져옵니다.

        Args:
            ticker: 종목 심볼 (예: "AAPL")

        Returns:
            dict | None: 종목 정보 또는 없으면 None
                - ticker: 종목 심볼
                - name: 종목명
                - market_cap: 시가총액
                - outstanding_shares: 총 발행 주식 수
                - float_shares: 유통 주식 수 (Float에서 직접 데이터 없으면 None)
                - primary_exchange: 주 거래소

        Note:
            - Rate Limit 주의: Free Tier에서 개별 종목 조회는 비효율적.
            - 대량 조회 시 fetch_grouped_daily()를 먼저 사용하고,
              필요한 종목만 선별해서 이 메서드를 호출하세요.
        """
        url = f"{self.base_url}/v3/reference/tickers/{ticker}"

        logger.debug(f"📡 Ticker Details API 호출: {ticker}")

        try:
            data = await self._request_with_retry("GET", url)
        except MassiveAPIError as e:
            logger.warning(f"⚠️ {ticker} 정보 조회 실패: {e}")
            return None

        if data.get("status") != "OK":
            return None

        results = data.get("results", {})

        # ─────────────────────────────────────────────────────────────────
        # 데이터 정규화
        # ─────────────────────────────────────────────────────────────────
        return {
            "ticker": results.get("ticker"),
            "name": results.get("name"),
            "market_cap": results.get("market_cap"),
            "outstanding_shares": results.get("share_class_shares_outstanding")
            or results.get("weighted_shares_outstanding"),
            "float_shares": None,  # Polygon에서 직접 제공하지 않음
            "primary_exchange": results.get("primary_exchange"),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
        }

    async def fetch_intraday_bars(
        self,
        ticker: str,
        multiplier: int = 5,
        from_date: str = None,
        to_date: str = None,
        limit: int = 5000,
    ) -> list[dict]:
        """
        특정 종목의 Intraday Bar 데이터 조회

        Massive Aggregates API를 사용합니다.
        1분, 5분, 15분, 60분 봉 데이터를 가져올 수 있습니다.

        Args:
            ticker: 종목 심볼 (예: "AAPL")
            multiplier: 타임프레임 배수 (1, 5, 15, 60)
            from_date: 시작일 (YYYY-MM-DD, 기본값: 2일 전)
            to_date: 종료일 (YYYY-MM-DD, 기본값: 오늘)
            limit: 최대 결과 수 (기본값: 5000)

        Returns:
            list[dict]: Intraday bar 데이터 리스트
                각 딕셔너리는 다음 키를 가집니다:
                - ticker: 종목 심볼
                - timestamp: Unix timestamp (ms)
                - open, high, low, close: 가격
                - volume: 거래량
                - vwap: 거래량 가중 평균가
                - transactions: 체결 건수

        Example:
            >>> bars = await client.fetch_intraday_bars("AAPL", multiplier=5, limit=100)
            >>> print(f"{len(bars)}개 5분봉 데이터")

        Note:
            - multiplier=1: 1분봉
            - multiplier=5: 5분봉
            - multiplier=15: 15분봉
            - multiplier=60: 1시간봉
        """
        # ─────────────────────────────────────────────────────────────────
        # 날짜 기본값 설정
        # ─────────────────────────────────────────────────────────────────
        if to_date is None:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if from_date is None:
            # 기본 2일 전 (Intraday 데이터는 보통 단기)
            from datetime import timedelta

            from_dt = datetime.now() - timedelta(days=2)
            from_date = from_dt.strftime("%Y-%m-%d")

        # ─────────────────────────────────────────────────────────────────
        # API 호출
        # GET /v2/aggs/ticker/{ticker}/range/{multiplier}/minute/{from}/{to}
        # ─────────────────────────────────────────────────────────────────
        url = f"{self.base_url}/v2/aggs/ticker/{ticker}/range/{multiplier}/minute/{from_date}/{to_date}"
        params = {
            "adjusted": "true",
            "sort": "desc",  # 최신부터 반환 (청크 로딩에 적합)
            "limit": str(limit),
        }

        logger.debug(
            f"📡 Intraday Bars API 호출: {ticker} {multiplier}m ({from_date} ~ {to_date})"
        )

        try:
            data = await self._request_with_retry("GET", url, params=params)
        except MassiveAPIError as e:
            logger.warning(f"⚠️ {ticker} Intraday 조회 실패: {e}")
            return []

        # ─────────────────────────────────────────────────────────────────
        # 응답 파싱
        # ─────────────────────────────────────────────────────────────────
        if data.get("status") != "OK":
            logger.warning(f"⚠️ Intraday API 응답 상태: {data.get('status')}")
            return []

        results = data.get("results", [])

        if not results:
            logger.info(f"📭 {ticker}에 Intraday 데이터 없음")
            return []

        # ─────────────────────────────────────────────────────────────────
        # 데이터 정규화
        # ─────────────────────────────────────────────────────────────────
        bars = []
        for item in results:
            try:
                timestamp = int(item.get("t", 0))
                open_val = float(item.get("o", 0))
                high_val = float(item.get("h", 0))
                low_val = float(item.get("l", 0))
                close_val = float(item.get("c", 0))

                bar = {
                    "ticker": ticker,
                    "timestamp": timestamp,  # Unix ms
                    "open": open_val,
                    "high": high_val,
                    "low": low_val,
                    "close": close_val,
                    "volume": int(item.get("v", 0)),
                    "vwap": float(item.get("vw", 0)) if item.get("vw") else None,
                    "transactions": int(item.get("n", 0)) if item.get("n") else None,
                }
                bars.append(bar)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"⚠️ Intraday 데이터 파싱 실패: {e}")
                continue

        logger.info(f"✅ {ticker} {multiplier}m: {len(bars)}개 바 데이터 수신")

        # sort=desc로 받았으므로 시간순(오래된→최신)으로 정렬
        bars.reverse()
        return bars

    async def fetch_day_gainers(self, include_otc: bool = False) -> list[dict]:
        """
        당일 급등주 상위 20개 조회

        Massive Snapshot Gainers API를 사용합니다.
        전일 종가 대비 상승률이 높은 상위 20개 종목을 반환합니다.

        Args:
            include_otc: OTC 종목 포함 여부 (기본 False)

        Returns:
            list[dict]: 급등주 리스트
                - ticker: 종목 심볼
                - change_pct: 변동률 (%)
                - last_price: 현재가
                - volume: 거래량
                - prev_close: 전일 종가

        Example:
            >>> gainers = await client.fetch_day_gainers()
            >>> for g in gainers[:5]:
            ...     print(f"{g['ticker']}: +{g['change_pct']:.1f}%")

        Note:
            - 장중 실시간 데이터입니다.
            - 거래량 10,000 이상인 종목만 포함됩니다.
            - 매일 3:30 AM EST에 초기화됩니다.
        """
        url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/gainers"
        params = {"include_otc": str(include_otc).lower()}

        logger.debug("📡 Day Gainers API 호출")

        try:
            data = await self._request_with_retry("GET", url, params=params)
        except MassiveAPIError as e:
            logger.warning(f"⚠️ Day Gainers 조회 실패: {e}")
            return []

        if data.get("status") != "OK":
            logger.warning(f"⚠️ Day Gainers API 응답 상태: {data.get('status')}")
            return []

        tickers = data.get("tickers", [])

        if not tickers:
            logger.info("📭 당일 급등주 데이터 없음")
            return []

        # ─────────────────────────────────────────────────────────────────
        # 데이터 정규화
        # ─────────────────────────────────────────────────────────────────
        gainers = []
        for item in tickers:
            try:
                ticker = item.get("ticker", "")
                day = item.get("day", {})
                prev_day = item.get("prevDay", {})

                if not ticker or not day:
                    continue

                prev_close = prev_day.get("c", 0)
                last_price = day.get("c", 0)
                change_pct = (
                    ((last_price - prev_close) / prev_close * 100)
                    if prev_close > 0
                    else 0
                )

                gainers.append(
                    {
                        "ticker": ticker,
                        "change_pct": round(change_pct, 2),
                        "last_price": last_price,
                        "volume": day.get("v", 0),
                        "prev_close": prev_close,
                        "todaysChange": item.get("todaysChange", 0),
                        "todaysChangePerc": item.get("todaysChangePerc", 0),
                        "updated": item.get("updated"),  # [08-001] E⏱ 계산용 타임스탬프
                    }
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"⚠️ Gainers 데이터 파싱 실패: {e}")
                continue

        logger.info(f"✅ Day Gainers: {len(gainers)}개 종목")
        return gainers

    async def get_gainers(self) -> list[dict]:
        """
        Top Gainers 조회 (1초 폴링용 최적화)

        fetch_day_gainers()의 래퍼로, 필요한 필드만 추출합니다.
        RealtimeScanner에서 1초 간격으로 호출됩니다.

        Returns:
            list[dict]: 급등주 리스트 (최소 필드)
                - ticker: 종목 심볼
                - change_pct: 변동률 (%)
                - price: 현재가
                - volume: 거래량

        Note:
            - 응답 크기: ~10KB, 21개 종목
            - 1초 폴링 시 600KB/분 (무시 가능한 수준)

        TODO [08-001]: E⏱ 비활성화됨
            - Massive API의 'updated' 타임스탬프가 미래 시간 반환 (2026-02-07)
            - Massive API 문서 확인 후 재활성화 필요
        """
        gainers = await self.fetch_day_gainers()

        # 필요한 필드만 추출 (메모리 최적화)
        return [
            {
                "ticker": g["ticker"],
                "change_pct": g.get("todaysChangePerc", g.get("change_pct", 0)),
                "price": g.get("last_price", 0),
                "volume": g.get("volume", 0),
            }
            for g in gainers
        ]

    async def close(self) -> None:
        """
        HTTP 클라이언트 연결 종료

        async with를 사용하지 않을 경우 수동으로 호출하세요.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.debug("🔌 MassiveClient 연결 종료")
