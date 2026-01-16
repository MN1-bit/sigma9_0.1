# ============================================================================
# Backtest Engine - 히스토리 데이터 기반 백테스팅 엔진
# ============================================================================
# 📌 이 파일의 역할:
#   - 히스토리 데이터를 사용한 전략 백테스팅
#   - 가상 주문 실행 (시뮬레이션)
#   - 성과 리포트 생성
#
# 📖 사용 예시:
#   >>> from backend.core.backtest_engine import BacktestEngine
#   >>> engine = BacktestEngine(db_path="data/market_data.db")
#   >>> await engine.initialize()
#   >>> report = await engine.run(strategy, tickers, "2024-01-01", "2024-12-01")
#   >>> report.print_summary()
# ============================================================================

"""
Backtest Engine Module

히스토리 데이터를 사용하여 전략을 백테스팅합니다.

Features:
    - 일봉 데이터 기반 백테스트 (Phase 1: Scanning)
    - 가상 주문 시뮬레이션
    - 성과 리포트 자동 생성
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import asyncio
import pandas as pd

# backend 경로 추가
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from loguru import logger

from core.backtest_report import BacktestReport, Trade


# ═══════════════════════════════════════════════════════════════════════════
# 백테스트 설정
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class BacktestConfig:
    """
    백테스트 설정

    Attributes:
        initial_capital: 초기 자본금 (USD)
        position_size_pct: 포지션 크기 (계좌 대비 %)
        max_positions: 최대 동시 보유 포지션 수
        stop_loss_pct: 손절 기준 (%)
        profit_target_pct: 익절 기준 (%)
        time_stop_days: 시간 손절 (일)
        entry_stage: 진입 대상 Stage (기본 4 = Tight Range)
        min_score: 최소 Accumulation Score
    """

    initial_capital: float = 100_000.0
    position_size_pct: float = 10.0  # 계좌의 10%
    max_positions: int = 5
    stop_loss_pct: float = -5.0
    profit_target_pct: float = 8.0
    time_stop_days: int = 3
    entry_stage: int = 4  # Stage 4 (Tight Range) 종목만 진입
    min_score: float = 80.0  # 최소 80점 이상


# ═══════════════════════════════════════════════════════════════════════════
# BacktestEngine 클래스
# ═══════════════════════════════════════════════════════════════════════════


class BacktestEngine:
    """
    백테스트 엔진

    히스토리 데이터를 사용하여 전략을 시뮬레이션합니다.

    [11-002] DataRepository 마이그레이션 완료.

    Attributes:
        repo: DataRepository 인스턴스
        config: 백테스트 설정
        report: 백테스트 결과 리포트

    Example:
        >>> from backend.container import container
        >>> repo = container.data_repository()
        >>> engine = BacktestEngine(data_repository=repo)
        >>>
        >>> from strategies.seismograph import SeismographStrategy
        >>> strategy = SeismographStrategy()
        >>>
        >>> report = await engine.run(
        ...     strategy=strategy,
        ...     tickers=["AAPL", "TSLA", "NVDA"],
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-01"
        ... )
        >>> report.print_summary()
    """

    def __init__(
        self,
        data_repository=None,
        config: Optional[BacktestConfig] = None,
        # [Deprecated] db_path는 하위 호환성을 위해 유지
        db_path: str = None,
    ):
        """
        BacktestEngine 초기화

        Args:
            data_repository: DataRepository 인스턴스 (권장)
            config: 백테스트 설정 (None이면 기본값 사용)
            db_path: [Deprecated] SQLite 데이터베이스 경로 (하위 호환성)
        """
        self._repo = data_repository
        self.config = config or BacktestConfig()
        self.report = None

        # [Deprecated] 하위 호환성: db_path가 주어진 경우
        self._legacy_db_path = db_path

        # ─────────────────────────────────────────────────────────────────
        # 시뮬레이션 상태
        # ─────────────────────────────────────────────────────────────────
        self._cash = self.config.initial_capital
        self._equity = self.config.initial_capital
        self._open_positions: Dict[str, Trade] = {}  # ticker -> Trade

        if self._repo:
            logger.debug("🔬 BacktestEngine 초기화 (DataRepository)")
        elif db_path:
            logger.debug(f"🔬 BacktestEngine 초기화 (Legacy DB: {db_path})")

    # ═══════════════════════════════════════════════════════════════════════
    # 초기화
    # ═══════════════════════════════════════════════════════════════════════

    async def initialize(self) -> None:
        """
        데이터 소스 초기화

        [11-002] DataRepository가 없는 경우 Container에서 가져오거나
        하위 호환성을 위해 MarketDB를 사용합니다.
        """
        if self._repo is None:
            # 하위 호환성: db_path가 주어진 경우 MarketDB 사용
            if self._legacy_db_path:
                from data.database import MarketDB

                self._legacy_db = MarketDB(self._legacy_db_path)
                await self._legacy_db.initialize()
                logger.debug("⚠️ Legacy MarketDB 사용 (Deprecated)")
            else:
                # Container에서 DataRepository 가져오기
                from backend.container import container

                self._repo = container.data_repository()

        logger.info("✅ BacktestEngine 초기화 완료")

    async def close(self) -> None:
        """리소스 정리"""
        # DataRepository는 Container가 관리하므로 별도 정리 불필요
        if hasattr(self, "_legacy_db") and self._legacy_db:
            await self._legacy_db.close()

    # ═══════════════════════════════════════════════════════════════════════
    # 백테스트 실행
    # ═══════════════════════════════════════════════════════════════════════

    async def run(
        self,
        strategy,
        tickers: List[str],
        start_date: str,
        end_date: str,
    ) -> BacktestReport:
        """
        백테스트 실행

        Args:
            strategy: StrategyBase 구현체 (예: SeismographStrategy)
            tickers: 백테스트 대상 종목 리스트
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            BacktestReport: 백테스트 결과 리포트
        """
        logger.info(f"🚀 백테스트 시작: {start_date} ~ {end_date}")
        logger.info(f"📊 대상 종목: {len(tickers)}개")

        # ─────────────────────────────────────────────────────────────────
        # 리포트 초기화
        # ─────────────────────────────────────────────────────────────────
        self.report = BacktestReport(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
            strategy_name=getattr(strategy, "name", "Unknown"),
        )

        # ─────────────────────────────────────────────────────────────────
        # 상태 초기화
        # ─────────────────────────────────────────────────────────────────
        self._cash = self.config.initial_capital
        self._equity = self.config.initial_capital
        self._open_positions.clear()

        # ─────────────────────────────────────────────────────────────────
        # 날짜 범위 생성
        # ─────────────────────────────────────────────────────────────────
        dates = self._generate_date_range(start_date, end_date)
        logger.info(f"📅 처리할 날짜: {len(dates)}일")

        # ─────────────────────────────────────────────────────────────────
        # 일별 데이터 캐싱 (성능 최적화)
        # ─────────────────────────────────────────────────────────────────
        all_data = await self._load_all_data(tickers, start_date, end_date)

        if not all_data:
            logger.warning("⚠️ 데이터가 없습니다.")
            return self.report

        # ─────────────────────────────────────────────────────────────────
        # 일별 Loop
        # ─────────────────────────────────────────────────────────────────
        for i, current_date in enumerate(dates):
            # 진행률 로깅 (매 20일마다)
            if i % 20 == 0:
                logger.debug(f"📆 Processing: {current_date} ({i + 1}/{len(dates)})")

            # 1. 오픈 포지션 청산 체크
            await self._check_exits(current_date, all_data)

            # 2. 새 진입 기회 탐색
            if len(self._open_positions) < self.config.max_positions:
                await self._check_entries(
                    strategy=strategy,
                    current_date=current_date,
                    tickers=tickers,
                    all_data=all_data,
                )

            # 3. Equity 업데이트
            self._update_equity(current_date, all_data)
            self.report.equity_curve.append(
                {
                    "date": current_date,
                    "equity": self._equity,
                    "cash": self._cash,
                    "positions": len(self._open_positions),
                }
            )

        # ─────────────────────────────────────────────────────────────────
        # 미청산 포지션 강제 청산
        # ─────────────────────────────────────────────────────────────────
        await self._close_all_positions(end_date, all_data, "backtest_end")

        logger.info(f"✅ 백테스트 완료: {self.report.total_trades}개 거래")
        return self.report

    # ═══════════════════════════════════════════════════════════════════════
    # 데이터 로드
    # ═══════════════════════════════════════════════════════════════════════

    async def _load_all_data(
        self, tickers: List[str], start_date: str, end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        모든 종목의 히스토리 데이터 로드

        [11-002] DataRepository에서 DataFrame을 직접 받음

        Args:
            tickers: 종목 리스트
            start_date: 시작일
            end_date: 종료일

        Returns:
            Dict[ticker, DataFrame]: 종목별 OHLCV 데이터
        """
        all_data = {}

        for ticker in tickers:
            # [11-002] DataRepository에서 데이터 조회 (DataFrame 반환)
            if self._repo:
                df = await self._repo.get_daily_bars(ticker, days=500, auto_fill=True)
            else:
                # Legacy fallback
                bars = await self._legacy_db.get_daily_bars(ticker, days=500)
                if not bars:
                    continue
                df = pd.DataFrame(
                    [
                        {
                            "date": bar.date,
                            "open": bar.open,
                            "high": bar.high,
                            "low": bar.low,
                            "close": bar.close,
                            "volume": bar.volume,
                        }
                        for bar in bars
                    ]
                )

            if df.empty:
                continue

            # 날짜 정렬 (오름차순)
            df = df.sort_values("date").reset_index(drop=True)

            # 날짜 범위 필터링 (lookback 고려하여 start 이전 데이터도 포함)
            all_data[ticker] = df

        logger.info(f"📊 {len(all_data)}개 종목 데이터 로드 완료")
        return all_data

    # ═══════════════════════════════════════════════════════════════════════
    # 진입 로직
    # ═══════════════════════════════════════════════════════════════════════

    async def _check_entries(
        self,
        strategy,
        current_date: str,
        tickers: List[str],
        all_data: Dict[str, pd.DataFrame],
    ) -> None:
        """
        새 진입 기회 탐색

        Args:
            strategy: 전략 인스턴스
            current_date: 현재 날짜
            tickers: 대상 종목 리스트
            all_data: 전체 데이터
        """
        # 이미 포지션을 보유한 종목 제외
        available = [t for t in tickers if t not in self._open_positions]

        candidates = []

        for ticker in available:
            if ticker not in all_data:
                continue

            df = all_data[ticker]

            # 현재 날짜까지의 데이터만 사용 (lookahead bias 방지)
            df_until = df[df["date"] <= current_date]

            if len(df_until) < 20:  # 최소 20일 데이터 필요
                continue

            # ─────────────────────────────────────────────────────────────
            # 전략의 Watchlist Score 계산
            # ─────────────────────────────────────────────────────────────
            try:
                result = strategy.calculate_watchlist_score_detailed(ticker, df_until)
                score = result.get("score", 0)
                stage = result.get("stage_number", 0)

                # Stage 4 (Tight Range) + 최소 점수 이상만 진입
                if stage >= self.config.entry_stage and score >= self.config.min_score:
                    candidates.append(
                        {
                            "ticker": ticker,
                            "score": score,
                            "stage": stage,
                            "signals": result.get("signals", {}),
                        }
                    )
            except Exception as e:
                logger.debug(f"⚠️ {ticker} score 계산 실패: {e}")
                continue

        # ─────────────────────────────────────────────────────────────────
        # 점수가 높은 순으로 정렬하여 진입
        # ─────────────────────────────────────────────────────────────────
        candidates.sort(key=lambda x: x["score"], reverse=True)

        available_slots = self.config.max_positions - len(self._open_positions)

        for candidate in candidates[:available_slots]:
            ticker = candidate["ticker"]

            # 다음날 시가에 진입 (백테스트에서는 다음 데이터 사용)
            df = all_data[ticker]
            next_idx = df[df["date"] > current_date].index

            if len(next_idx) == 0:
                continue

            next_bar = df.loc[next_idx[0]]
            entry_price = next_bar["open"]
            entry_date = next_bar["date"]

            # ─────────────────────────────────────────────────────────────
            # 포지션 오픈
            # ─────────────────────────────────────────────────────────────
            trade = Trade(
                ticker=ticker,
                entry_date=entry_date,
                entry_price=entry_price,
                stage=candidate["stage"],
                score=candidate["score"],
                metadata={
                    "signals": candidate["signals"],
                    "position_size_pct": self.config.position_size_pct,
                },
            )

            self._open_positions[ticker] = trade
            self.report.add_trade(trade)

            # 현금 차감 (간소화: 포지션 크기만큼)
            position_value = self._cash * (self.config.position_size_pct / 100)
            self._cash -= position_value

            logger.debug(
                f"🟢 진입: {ticker} @ ${entry_price:.2f} (Stage {candidate['stage']}, Score {candidate['score']:.0f})"
            )

    # ═══════════════════════════════════════════════════════════════════════
    # 청산 로직
    # ═══════════════════════════════════════════════════════════════════════

    async def _check_exits(
        self,
        current_date: str,
        all_data: Dict[str, pd.DataFrame],
    ) -> None:
        """
        오픈 포지션 청산 체크

        Args:
            current_date: 현재 날짜
            all_data: 전체 데이터
        """
        to_close = []

        for ticker, trade in self._open_positions.items():
            if ticker not in all_data:
                continue

            df = all_data[ticker]
            current_bar = df[df["date"] == current_date]

            if current_bar.empty:
                continue

            current_bar = current_bar.iloc[0]
            current_high = current_bar["high"]
            current_low = current_bar["low"]
            current_close = current_bar["close"]

            entry_price = trade.entry_price

            # ─────────────────────────────────────────────────────────────
            # 1. Stop Loss 체크 (장중 저가 기준)
            # ─────────────────────────────────────────────────────────────
            pnl_low = ((current_low - entry_price) / entry_price) * 100
            if pnl_low <= self.config.stop_loss_pct:
                exit_price = entry_price * (1 + self.config.stop_loss_pct / 100)
                to_close.append((ticker, exit_price, "stop_loss", current_date))
                continue

            # ─────────────────────────────────────────────────────────────
            # 2. Profit Target 체크 (장중 고가 기준)
            # ─────────────────────────────────────────────────────────────
            pnl_high = ((current_high - entry_price) / entry_price) * 100
            if pnl_high >= self.config.profit_target_pct:
                exit_price = entry_price * (1 + self.config.profit_target_pct / 100)
                to_close.append((ticker, exit_price, "profit_target", current_date))
                continue

            # ─────────────────────────────────────────────────────────────
            # 3. Time Stop 체크
            # ─────────────────────────────────────────────────────────────
            try:
                entry_dt = datetime.strptime(trade.entry_date, "%Y-%m-%d")
                current_dt = datetime.strptime(current_date, "%Y-%m-%d")
                holding_days = (current_dt - entry_dt).days

                if holding_days >= self.config.time_stop_days:
                    to_close.append((ticker, current_close, "time_stop", current_date))
                    continue
            except Exception:
                pass

        # ─────────────────────────────────────────────────────────────────
        # 청산 실행
        # ─────────────────────────────────────────────────────────────────
        for ticker, exit_price, exit_reason, exit_date in to_close:
            trade = self._open_positions.pop(ticker)
            pnl = trade.close(exit_date, exit_price, exit_reason)

            # 현금 복구
            entry_value = self.config.initial_capital * (
                self.config.position_size_pct / 100
            )
            exit_value = entry_value * (1 + pnl / 100)
            self._cash += exit_value

            emoji = "🟢" if pnl > 0 else "🔴"
            logger.debug(
                f"{emoji} 청산: {ticker} @ ${exit_price:.2f} ({exit_reason}, P&L {pnl:+.2f}%)"
            )

    async def _close_all_positions(
        self,
        date: str,
        all_data: Dict[str, pd.DataFrame],
        reason: str = "forced",
    ) -> None:
        """
        모든 포지션 강제 청산

        Args:
            date: 청산 날짜
            all_data: 전체 데이터
            reason: 청산 이유
        """
        for ticker in list(self._open_positions.keys()):
            trade = self._open_positions.pop(ticker)

            # 해당 날짜의 종가로 청산
            if ticker in all_data:
                df = all_data[ticker]
                close_bar = df[df["date"] <= date].tail(1)

                if not close_bar.empty:
                    exit_price = close_bar.iloc[0]["close"]
                    exit_date = close_bar.iloc[0]["date"]
                else:
                    exit_price = trade.entry_price
                    exit_date = date
            else:
                exit_price = trade.entry_price
                exit_date = date

            pnl = trade.close(exit_date, exit_price, reason)

            # 현금 복구
            entry_value = self.config.initial_capital * (
                self.config.position_size_pct / 100
            )
            exit_value = entry_value * (1 + pnl / 100)
            self._cash += exit_value

            logger.debug(f"⬜ 강제청산: {ticker} @ ${exit_price:.2f} (P&L {pnl:+.2f}%)")

    # ═══════════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_date_range(self, start_date: str, end_date: str) -> List[str]:
        """날짜 범위 생성 (주말 제외)"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        dates = []
        current = start

        while current <= end:
            # 주말 제외 (월=0, 일=6)
            if current.weekday() < 5:
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        return dates

    def _update_equity(
        self,
        current_date: str,
        all_data: Dict[str, pd.DataFrame],
    ) -> None:
        """현재 자산가치 업데이트"""
        positions_value = 0.0

        for ticker, trade in self._open_positions.items():
            if ticker not in all_data:
                continue

            df = all_data[ticker]
            current_bar = df[df["date"] == current_date]

            if not current_bar.empty:
                current_price = current_bar.iloc[0]["close"]
                pnl_pct = (
                    (current_price - trade.entry_price) / trade.entry_price
                ) * 100
                position_value = (
                    self.config.initial_capital * self.config.position_size_pct / 100
                ) * (1 + pnl_pct / 100)
                positions_value += position_value

        self._equity = self._cash + positions_value


# ═══════════════════════════════════════════════════════════════════════════
# CLI 실행
# ═══════════════════════════════════════════════════════════════════════════


async def main():
    """백테스트 CLI 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="Backtest Engine CLI")
    parser.add_argument("--db", default="data/market_data.db", help="Database path")
    parser.add_argument("--start", default="2024-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2024-12-01", help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--tickers", nargs="+", default=["AAPL"], help="Tickers to backtest"
    )

    args = parser.parse_args()

    # 엔진 초기화
    engine = BacktestEngine(db_path=args.db)
    await engine.initialize()

    try:
        # 전략 로드
        from strategies.seismograph import SeismographStrategy

        strategy = SeismographStrategy()

        # 백테스트 실행
        report = await engine.run(
            strategy=strategy,
            tickers=args.tickers,
            start_date=args.start,
            end_date=args.end,
        )

        # 결과 출력
        report.print_summary()

    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
