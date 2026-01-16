# ============================================================================
# Scanner Orchestrator - DataRepository 기반 Watchlist 생성
# ============================================================================
# 📌 이 파일의 역할:
#   - DataRepository 데이터를 기반으로 Watchlist 생성
#   - SeismographStrategy의 calculate_watchlist_score() 실행
#   - 상위 N개 종목을 Watchlist로 반환
#
# 🔄 스캔 프로세스:
#   1. Universe Filter 통과 종목 추출 (가격, 거래량 기준)
#   2. 각 종목의 최근 20일 데이터 조회
#   3. calculate_watchlist_score() 실행
#   4. 점수 순 정렬 → 상위 50개 반환
#
# 📖 사용 예시:
#   >>> scanner = Scanner(data_repository)
#   >>> watchlist = await scanner.run_daily_scan()
#   >>> print(f"Watchlist: {len(watchlist)}개 종목")
#
# 📌 [11-002] DataRepository 마이그레이션 완료
# ============================================================================

from typing import TYPE_CHECKING
from loguru import logger

from backend.strategies.seismograph import SeismographStrategy
from backend.core.ticker_filter import TickerFilter, get_ticker_filter

if TYPE_CHECKING:
    from backend.data.data_repository import DataRepository


# ═══════════════════════════════════════════════════════════════════════════
# [12-002] 모듈 레벨 스코어 계산 함수 (ProcessPoolExecutor pickle 호환성)
# ═══════════════════════════════════════════════════════════════════════════


def _calculate_score(item: tuple) -> dict | None:
    """
    개별 티커 스코어 계산 (병렬 처리용)

    ProcessPoolExecutor에서 사용하기 위해 모듈 레벨에 정의
    (내부 함수는 pickle 불가)

    Args:
        item: (ticker, data) 튜플

    Returns:
        dict: 스코어 결과 (score > 50일 때만)
        None: 스코어 미달 또는 오류
    """
    ticker, data = item
    try:
        # SeismographStrategy 인스턴스 생성 (각 워커에서)
        strategy = SeismographStrategy()
        result = strategy.calculate_watchlist_score_detailed(ticker, data)

        if result["score"] > 50:
            last_close = data[-1]["close"] if data else 0
            prev_close = data[-2]["close"] if len(data) >= 2 else last_close
            change_pct = (
                ((last_close - prev_close) / prev_close * 100)
                if prev_close > 0
                else 0.0
            )
            avg_vol = sum(d["volume"] for d in data) / len(data) if data else 0

            return {
                "ticker": ticker,
                "score": result["score"],
                "score_v2": result.get("score_v2", result["score"]),
                "score_v3": result.get("score_v3"),
                "intensities": result.get("intensities_v3", {}),
                "stage": result["stage"],
                "stage_number": result.get("stage_number", 0),
                "signals": result.get("signals", {}),
                "can_trade": result.get("can_trade", True),
                "last_close": last_close,
                "change_pct": round(change_pct, 2),
                "avg_volume": avg_vol,
                "dollar_volume": last_close * avg_vol,
            }
        return None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Scanner 클래스
# ═══════════════════════════════════════════════════════════════════════════


class Scanner:
    """
    DataRepository 기반 Watchlist 생성 오케스트레이터

    [11-002] DataRepository를 사용하여 Parquet 데이터를 기반으로
    SeismographStrategy의 Accumulation Score를 계산하고
    상위 N개 종목을 Watchlist로 반환합니다.

    Attributes:
        data_repository: DataRepository 인스턴스
        strategy: SeismographStrategy 인스턴스
        watchlist_size: Watchlist 크기 (기본값: 50)
        ticker_filter: TickerFilter 인스턴스

    Example:
        >>> from backend.container import container
        >>> repo = container.data_repository()
        >>> scanner = Scanner(repo)
        >>> watchlist = await scanner.run_daily_scan()
        >>> for item in watchlist[:10]:
        ...     print(f"{item['ticker']}: {item['score']:.1f}점")
    """

    def __init__(
        self,
        data_repository: "DataRepository",
        watchlist_size: int = 50,
        ticker_filter: TickerFilter | None = None,
    ):
        """
        Scanner 초기화

        Args:
            data_repository: DataRepository 인스턴스
            watchlist_size: Watchlist에 포함할 종목 수
            ticker_filter: TickerFilter 인스턴스 (None이면 기본값)
        """
        # [11-002] DataRepository 사용
        self.repo = data_repository
        self.watchlist_size = watchlist_size
        self.ticker_filter = ticker_filter or get_ticker_filter()

        # SeismographStrategy 인스턴스 생성
        self.strategy = SeismographStrategy()

        logger.debug(f"🔍 Scanner 초기화 (Watchlist Size: {watchlist_size})")

    # ═══════════════════════════════════════════════════════════════════════
    # 스캔 메서드
    # ═══════════════════════════════════════════════════════════════════════

    async def run_daily_scan(
        self,
        min_price: float = 2.0,
        max_price: float = 20.0,
        min_volume: int = 100_000,
        lookback_days: int = 20,
    ) -> list[dict]:
        """
        일일 스캔 실행 - Watchlist 생성

        [12-001] 전체 유니버스 스캔 전략
        [12-002] 벌크 로드 최적화 적용

        1. 전체 티커 조회 → TickerFilter로 제외
        2. 벌크 로드 (파일 1회 읽기)
        3. 스코어 계산 (50점 초과만)
        4. 가격/거래량 Post-Filter (옵션)
        5. 상위 N개 반환

        Args:
            min_price: 최소 종가 (기본값: $2.00)
            max_price: 최대 종가 (기본값: $20.00)
            min_volume: 최소 평균 거래량 (기본값: 100K)
            lookback_days: 데이터 조회 기간 (기본값: 20일)

        Returns:
            list[dict]: Watchlist (점수 내림차순 정렬)
        """
        import time

        start_time = time.time()

        logger.info("🔍 Daily Scan 시작 [12-002 벌크 로드 최적화]...")

        # ─────────────────────────────────────────────────────────────────
        # 1. Universe 후보 추출 (TickerFilter 적용)
        # ─────────────────────────────────────────────────────────────────
        candidates = await self._get_universe_candidates(
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume,
        )

        if not candidates:
            logger.warning("⚠️ Universe 후보가 없습니다. 데이터를 확인하세요.")
            return []

        logger.info(f"📊 스캔 대상: {len(candidates):,}개 종목")

        # ─────────────────────────────────────────────────────────────────
        # 2. [12-002] 벌크 로드 (파일 1회 읽기)
        # ELI5: 10,000개 티커를 조회해도 파일 읽기는 1번만 수행
        # ─────────────────────────────────────────────────────────────────
        bulk_start = time.time()
        all_data = self.repo.get_daily_bars_bulk(tickers=candidates, days=lookback_days)
        bulk_elapsed = time.time() - bulk_start
        logger.info(
            f"📦 벌크 로드 완료: {len(all_data):,}개 티커 ({bulk_elapsed:.2f}초)"
        )

        # ─────────────────────────────────────────────────────────────────
        # 3. [12-002] 병렬 스코어링
        # ELI5: CPU 여러 개를 동시에 사용해서 계산 속도를 높입니다
        # ─────────────────────────────────────────────────────────────────
        import os
        from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

        # AWS Lambda 환경 감지 (Lambda는 ProcessPool 사용 불가)
        # ELI5: 어떤 서버에서 돌아가는지 보고, 적절한 병렬 처리 방식 선택
        IS_LAMBDA = "AWS_LAMBDA_FUNCTION_NAME" in os.environ

        # Executor 선택 (Lambda: ThreadPool, 그 외: ProcessPool)
        Executor = ThreadPoolExecutor if IS_LAMBDA else ProcessPoolExecutor
        max_workers = 2 if IS_LAMBDA else min(4, os.cpu_count() or 4)

        logger.info(f"⚡ 병렬 처리 시작 ({Executor.__name__}, workers={max_workers})")

        # 스코어 계산 대상 필터링 (최소 5일 데이터)
        score_items = [
            (ticker, data) for ticker, data in all_data.items() if len(data) >= 5
        ]
        skipped = len(all_data) - len(score_items)

        # 병렬 스코어 계산 실행
        score_start = time.time()
        raw_results = []

        with Executor(max_workers=max_workers) as executor:
            # map()으로 병렬 실행 (모듈 레벨 함수 사용)
            raw_results = list(executor.map(_calculate_score, score_items))

        # None 제거 (score <= 50 또는 에러)
        results = [r for r in raw_results if r is not None]

        score_elapsed = time.time() - score_start
        logger.info(
            f"⚡ 병렬 스코어링 완료: {len(results):,}개 (50점+ 통과) / {len(score_items):,}개 ({score_elapsed:.2f}초)"
        )

        # ─────────────────────────────────────────────────────────────────
        # 4. Post-Score 가격/거래량 필터링 (Hybrid 옵션)
        # ─────────────────────────────────────────────────────────────────
        before_filter = len(results)
        results = [
            r
            for r in results
            if min_price <= r["last_close"] <= max_price
            and r["avg_volume"] >= min_volume
        ]
        filtered_out = before_filter - len(results)

        if filtered_out > 0:
            logger.info(
                f"📊 가격/거래량 필터: {filtered_out:,}개 제외 (${min_price}~${max_price}, Vol≥{min_volume:,})"
            )

        # ─────────────────────────────────────────────────────────────────
        # 5. 점수 순 정렬 → 상위 N개 선택
        # ─────────────────────────────────────────────────────────────────
        results.sort(key=lambda x: x["score"], reverse=True)
        watchlist = results[: self.watchlist_size]

        elapsed = time.time() - start_time
        logger.info(
            f"✅ Daily Scan 완료: {len(watchlist)}개 Watchlist ({elapsed:.1f}초, 스킵: {skipped:,})"
        )

        # 상위 5개 로그
        for i, item in enumerate(watchlist[:5]):
            logger.info(
                f"  {i + 1}. {item['ticker']}: {item['score']:.0f}점 ({item['stage']})"
            )

        return watchlist

    # ═══════════════════════════════════════════════════════════════════════
    # Universe Filter
    # ═══════════════════════════════════════════════════════════════════════

    async def _get_universe_candidates(
        self,
        min_price: float,
        max_price: float,
        min_volume: int,
    ) -> list[str]:
        """
        Universe 후보 종목 추출

        [12-001] 전체 유니버스 스캔 전략으로 변경
        - 기존: 티커별 DB 조회 후 가격/거래량 사전 필터링 (느림)
        - 변경: 전체 티커 → TickerFilter만 적용 (빠름)
        - 가격/거래량 필터링은 스코어 계산 후 적용 (run_daily_scan에서)

        Args:
            min_price: 최소 종가 (현재 미사용, 하위호환용)
            max_price: 최대 종가 (현재 미사용, 하위호환용)
            min_volume: 최소 평균 거래량 (현재 미사용, 하위호환용)

        Returns:
            list[str]: 종목 심볼 리스트
        """
        # [12-001] 전체 티커 조회
        all_tickers = self.repo.get_all_tickers()

        if not all_tickers:
            logger.warning("⚠️ 저장된 티커가 없습니다.")
            return []

        logger.info(f"📊 전체 티커: {len(all_tickers):,}개")

        # TickerFilter로 Warrant/Preferred/Rights/Units 제외
        candidates = self.ticker_filter.filter(all_tickers)

        logger.info(
            f"📊 TickerFilter 후: {len(candidates):,}개 (제외: {len(all_tickers) - len(candidates):,}개)"
        )

        return candidates

    # ═══════════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _score_to_stage(score: float) -> str:
        """
        점수를 Stage 문자열로 변환

        Args:
            score: Accumulation Score

        Returns:
            str: Stage 문자열
        """
        if score >= 100:
            return "Stage 4 (폭발 임박 🔥)"
        elif score >= 80:
            return "Stage 4 (Tight Range)"
        elif score >= 70:
            return "Stage 3 (관심 대상)"
        elif score >= 50:
            return "Stage 3 (Accum Bar)"
        elif score >= 30:
            return "Stage 2 (OBV Divergence)"
        elif score >= 10:
            return "Stage 1 (Volume Dry-out)"
        else:
            return "No Signal"


# ═══════════════════════════════════════════════════════════════════════════
# 편의 함수
# ═══════════════════════════════════════════════════════════════════════════


async def run_scan() -> list[dict]:
    """
    스캔 실행 편의 함수

    [11-002] DI Container에서 DataRepository 가져와서 스캔 실행

    Returns:
        list[dict]: Watchlist
    """
    from backend.container import container

    repo = container.data_repository()
    scanner = Scanner(repo)
    watchlist = await scanner.run_daily_scan()

    return watchlist


# ═══════════════════════════════════════════════════════════════════════════
# CLI 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    독립 실행 테스트
    
    Usage:
        python scanner.py
    """
    import asyncio
    import sys

    # 로거 설정
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    async def main():
        watchlist = await run_scan()

        print("\n" + "=" * 60)
        print("📋 WATCHLIST")
        print("=" * 60)

        for i, item in enumerate(watchlist, 1):
            print(
                f"{i:3}. {item['ticker']:6} | {item['score']:5.0f}점 | {item['stage']}"
            )

    asyncio.run(main())
