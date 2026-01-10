# ============================================================================
# Massive Loader Tests
# ============================================================================
# 📌 이 파일의 역할:
#   - massive_loader.py 모듈의 단위 테스트
#   - 증분 업데이트 로직 검증 (Mock API 사용)
#   - 거래일 계산 로직 테스트
#
# 📖 실행 방법:
#   pytest tests/test_massive_loader.py -v
# ============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

# 테스트 대상 모듈 임포트를 위한 경로 설정
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.data.massive_loader import MassiveLoader, US_HOLIDAYS


# ═══════════════════════════════════════════════════════════════════════════
# 거래일 계산 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestTradingDayCalculation:
    """거래일 계산 로직 테스트"""

    def test_weekday_is_trading_day(self):
        """평일은 거래일"""
        # 2024-12-16은 월요일
        monday = datetime(2024, 12, 16)
        assert MassiveLoader.is_trading_day(monday) is True

        # 2024-12-17은 화요일
        tuesday = datetime(2024, 12, 17)
        assert MassiveLoader.is_trading_day(tuesday) is True

    def test_weekend_is_not_trading_day(self):
        """주말은 거래일 아님"""
        # 2024-12-14는 토요일
        saturday = datetime(2024, 12, 14)
        assert MassiveLoader.is_trading_day(saturday) is False

        # 2024-12-15는 일요일
        sunday = datetime(2024, 12, 15)
        assert MassiveLoader.is_trading_day(sunday) is False

    def test_holiday_is_not_trading_day(self):
        """공휴일은 거래일 아님"""
        # 2024-12-25은 크리스마스
        christmas = datetime(2024, 12, 25)
        assert MassiveLoader.is_trading_day(christmas) is False

        # 2024-07-04은 독립기념일
        july4 = datetime(2024, 7, 4)
        assert MassiveLoader.is_trading_day(july4) is False

    def test_get_trading_days_between(self):
        """두 날짜 사이의 거래일 계산"""
        # 2024-12-09 (월) ~ 2024-12-13 (금): 5 거래일
        start = datetime(2024, 12, 9)
        end = datetime(2024, 12, 13)

        trading_days = MassiveLoader.get_trading_days_between(start, end)

        assert len(trading_days) == 5
        assert trading_days[0] == "2024-12-09"
        assert trading_days[-1] == "2024-12-13"

    def test_get_trading_days_skips_weekend(self):
        """주말이 포함된 기간에서 주말 제외"""
        # 2024-12-13 (금) ~ 2024-12-16 (월): 2 거래일 (금, 월)
        start = datetime(2024, 12, 13)
        end = datetime(2024, 12, 16)

        trading_days = MassiveLoader.get_trading_days_between(start, end)

        assert len(trading_days) == 2
        assert "2024-12-14" not in trading_days  # 토요일
        assert "2024-12-15" not in trading_days  # 일요일

    def test_get_trading_days_skips_holiday(self):
        """공휴일 포함된 기간에서 공휴일 제외"""
        # 크리스마스 주간
        start = datetime(2024, 12, 23)
        end = datetime(2024, 12, 27)

        trading_days = MassiveLoader.get_trading_days_between(start, end)

        assert "2024-12-25" not in trading_days  # 크리스마스

    def test_get_last_trading_day(self):
        """가장 최근 거래일 반환"""
        last_day = MassiveLoader.get_last_trading_day()

        # 형식 확인
        assert len(last_day) == 10
        assert last_day.count("-") == 2

        # 과거 날짜인지 확인
        last_dt = datetime.strptime(last_day, "%Y-%m-%d")
        assert last_dt < datetime.now()


# ═══════════════════════════════════════════════════════════════════════════
# 증분 업데이트 로직 테스트 (Mock)
# ═══════════════════════════════════════════════════════════════════════════


class TestIncrementalUpdate:
    """증분 업데이트 로직 테스트"""

    @pytest.mark.asyncio
    async def test_update_calls_api_for_missing_days(self):
        """
        누락된 날짜에 대해서만 API 호출하는지 확인
        """
        # Mock DB
        mock_db = AsyncMock()
        mock_db.get_latest_date.return_value = "2024-12-13"  # 금요일
        mock_db.upsert_bulk.return_value = 5000

        # Mock Client
        mock_client = AsyncMock()
        mock_client.fetch_grouped_daily.return_value = [
            {
                "ticker": "AAPL",
                "date": "2024-12-16",
                "open": 150,
                "high": 152,
                "low": 149,
                "close": 151,
                "volume": 50000000,
            }
        ]

        loader = MassiveLoader(mock_db, mock_client)

        # 현재 시간을 2024-12-17 화요일로 가정하고 테스트
        with patch.object(
            MassiveLoader, "get_last_trading_day", return_value="2024-12-16"
        ):
            await loader.update_market_data()

        # 12/16 (월)만 호출되어야 함 (12/14, 15는 주말)
        mock_client.fetch_grouped_daily.assert_called_once_with("2024-12-16")

    @pytest.mark.asyncio
    async def test_update_when_up_to_date(self):
        """
        이미 최신 상태일 때 API 호출 안 함
        """
        mock_db = AsyncMock()
        mock_db.get_latest_date.return_value = "2024-12-16"

        mock_client = AsyncMock()

        loader = MassiveLoader(mock_db, mock_client)

        # 마지막 거래일도 12/16이라고 가정
        with patch.object(
            MassiveLoader, "get_last_trading_day", return_value="2024-12-16"
        ):
            result = await loader.update_market_data()

        assert result == 0
        mock_client.fetch_grouped_daily.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_when_db_empty(self):
        """
        DB가 비어있을 때 initial_load 호출
        """
        mock_db = AsyncMock()
        mock_db.get_latest_date.return_value = None  # DB 비어있음
        mock_db.upsert_bulk.return_value = 5000

        mock_client = AsyncMock()
        mock_client.fetch_grouped_daily.return_value = [
            {
                "ticker": "AAPL",
                "date": "2024-12-16",
                "open": 150,
                "high": 152,
                "low": 149,
                "close": 151,
                "volume": 50000000,
            }
        ]

        loader = MassiveLoader(mock_db, mock_client)

        # update_market_data가 initial_load를 호출하는지 확인
        with patch.object(loader, "initial_load", return_value=150000) as mock_initial:
            await loader.update_market_data()
            mock_initial.assert_called_once_with(days=30)


# ═══════════════════════════════════════════════════════════════════════════
# 동기화 상태 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestSyncStatus:
    """동기화 상태 확인 테스트"""

    @pytest.mark.asyncio
    async def test_sync_status_up_to_date(self):
        """최신 상태일 때"""
        mock_db = AsyncMock()
        mock_db.get_latest_date.return_value = "2024-12-16"

        mock_client = AsyncMock()

        loader = MassiveLoader(mock_db, mock_client)

        with patch.object(
            MassiveLoader, "get_last_trading_day", return_value="2024-12-16"
        ):
            status = await loader.get_sync_status()

        assert status["is_up_to_date"] is True
        assert status["missing_days"] == 0

    @pytest.mark.asyncio
    async def test_sync_status_missing_days(self):
        """누락된 날짜가 있을 때"""
        mock_db = AsyncMock()
        mock_db.get_latest_date.return_value = "2024-12-12"  # 목요일

        mock_client = AsyncMock()

        loader = MassiveLoader(mock_db, mock_client)

        with patch.object(
            MassiveLoader, "get_last_trading_day", return_value="2024-12-16"
        ):
            status = await loader.get_sync_status()

        assert status["is_up_to_date"] is False
        assert status["missing_days"] == 2  # 금요일, 월요일

    @pytest.mark.asyncio
    async def test_sync_status_empty_db(self):
        """DB가 비어있을 때"""
        mock_db = AsyncMock()
        mock_db.get_latest_date.return_value = None

        mock_client = AsyncMock()

        loader = MassiveLoader(mock_db, mock_client)

        status = await loader.get_sync_status()

        assert status["db_latest_date"] is None
        assert status["is_up_to_date"] is False


# ═══════════════════════════════════════════════════════════════════════════
# 공휴일 데이터 유효성 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestHolidayData:
    """공휴일 데이터 검증"""

    def test_holidays_format(self):
        """공휴일 날짜 형식 검증"""
        for holiday in US_HOLIDAYS:
            # YYYY-MM-DD 형식 확인
            assert len(holiday) == 10
            assert holiday[4] == "-"
            assert holiday[7] == "-"

            # 유효한 날짜인지 확인
            try:
                datetime.strptime(holiday, "%Y-%m-%d")
            except ValueError:
                pytest.fail(f"Invalid date format: {holiday}")

    def test_major_holidays_included(self):
        """주요 공휴일 포함 확인"""
        assert "2024-12-25" in US_HOLIDAYS  # Christmas
        assert "2024-07-04" in US_HOLIDAYS  # Independence Day
        assert "2024-11-28" in US_HOLIDAYS  # Thanksgiving
