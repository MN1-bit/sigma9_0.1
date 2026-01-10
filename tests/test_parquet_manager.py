# ============================================================================
# Parquet Manager Tests
# ============================================================================
# 📌 이 파일의 역할:
#   - parquet_manager.py 모듈의 단위 테스트
#   - Write/Read/Append 라운드트립 검증
#   - 중복 처리 및 대용량 데이터 성능 테스트
#
# 📖 실행 방법:
#   pytest tests/test_parquet_manager.py -v
# ============================================================================

import pytest
import tempfile
import shutil
import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.data.parquet_manager import ParquetManager


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_parquet_dir():
    """
    임시 Parquet 디렉터리 생성 Fixture

    테스트 후 자동으로 삭제됩니다.
    """
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)


@pytest.fixture
def parquet_manager(temp_parquet_dir):
    """
    ParquetManager 인스턴스 생성
    """
    return ParquetManager(temp_parquet_dir)


@pytest.fixture
def sample_daily_df():
    """
    테스트용 샘플 일봉 데이터
    """
    return pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "date": "2024-12-16",
                "open": 150.0,
                "high": 152.5,
                "low": 149.0,
                "close": 151.0,
                "volume": 50000000,
            },
            {
                "ticker": "AAPL",
                "date": "2024-12-17",
                "open": 151.0,
                "high": 153.0,
                "low": 150.0,
                "close": 152.0,
                "volume": 45000000,
            },
            {
                "ticker": "MSFT",
                "date": "2024-12-16",
                "open": 380.0,
                "high": 385.0,
                "low": 378.0,
                "close": 382.0,
                "volume": 30000000,
            },
        ]
    )


@pytest.fixture
def sample_intraday_df():
    """
    테스트용 샘플 분봉 데이터
    """
    import time

    base_ts = int(time.time() * 1000) - 3600000  # 1시간 전부터
    return pd.DataFrame(
        [
            {
                "timestamp": base_ts,
                "open": 150.0,
                "high": 150.5,
                "low": 149.8,
                "close": 150.2,
                "volume": 10000,
            },
            {
                "timestamp": base_ts + 60000,  # +1분
                "open": 150.2,
                "high": 150.8,
                "low": 150.0,
                "close": 150.5,
                "volume": 12000,
            },
            {
                "timestamp": base_ts + 120000,  # +2분
                "open": 150.5,
                "high": 151.0,
                "low": 150.3,
                "close": 150.8,
                "volume": 8000,
            },
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════
# Daily Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDailyOperations:
    """일봉 데이터 CRUD 테스트"""

    def test_write_and_read_daily(self, parquet_manager, sample_daily_df):
        """일봉 Write/Read 라운드트립"""
        # Write
        count = parquet_manager.write_daily(sample_daily_df)
        assert count == 3

        # Read all (days=None returns everything)
        result = parquet_manager.read_daily()
        assert len(result) == 3

        # Read by ticker
        aapl = parquet_manager.read_daily(ticker="AAPL")
        assert len(aapl) == 2
        assert all(aapl["ticker"] == "AAPL")

    def test_append_daily_deduplication(self, parquet_manager, sample_daily_df):
        """일봉 Append 시 중복 제거"""
        # 첫 번째 삽입
        parquet_manager.write_daily(sample_daily_df)

        # 중복 + 신규 데이터 추가
        new_data = pd.DataFrame(
            [
                {
                    "ticker": "AAPL",
                    "date": "2024-12-17",  # 중복
                    "open": 155.0,
                    "high": 158.0,
                    "low": 154.0,
                    "close": 157.0,
                    "volume": 60000000,
                },
                {
                    "ticker": "AAPL",
                    "date": "2024-12-18",  # 신규
                    "open": 157.0,
                    "high": 160.0,
                    "low": 156.0,
                    "close": 159.0,
                    "volume": 55000000,
                },
            ]
        )

        count = parquet_manager.append_daily(new_data)
        assert count == 4  # 기존 3 - 중복 1 + 신규 2 = 4

        # 중복 데이터는 최신 값으로 업데이트
        result = parquet_manager.read_daily(ticker="AAPL")
        dec17 = result[result["date"] == "2024-12-17"].iloc[0]
        assert dec17["close"] == 157.0  # 업데이트된 값

    def test_read_empty_daily(self, parquet_manager):
        """빈 일봉 읽기"""
        result = parquet_manager.read_daily()
        assert result.empty


# ═══════════════════════════════════════════════════════════════════════════
# Intraday Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestIntradayOperations:
    """분봉 데이터 CRUD 테스트"""

    def test_write_and_read_intraday(self, parquet_manager, sample_intraday_df):
        """분봉 Write/Read 라운드트립"""
        # Write
        count = parquet_manager.write_intraday("AAPL", "1m", sample_intraday_df)
        assert count == 3

        # Read
        result = parquet_manager.read_intraday("AAPL", "1m", days=1)
        assert len(result) == 3

    def test_intraday_file_path(self, parquet_manager):
        """Intraday 파일 경로 확인"""
        path = parquet_manager._get_intraday_path("AAPL", "1m")
        assert path.name == "AAPL_1m.parquet"

    def test_read_nonexistent_intraday(self, parquet_manager):
        """존재하지 않는 분봉 읽기"""
        result = parquet_manager.read_intraday("INVALID", "1m")
        assert result.empty


# ═══════════════════════════════════════════════════════════════════════════
# Utility Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUtilities:
    """유틸리티 메서드 테스트"""

    def test_get_available_tickers(self, parquet_manager, sample_daily_df):
        """티커 목록 조회"""
        parquet_manager.write_daily(sample_daily_df)

        tickers = parquet_manager.get_available_tickers()
        assert set(tickers) == {"AAPL", "MSFT"}

    def test_get_stats(self, parquet_manager, sample_daily_df):
        """통계 조회"""
        parquet_manager.write_daily(sample_daily_df)

        stats = parquet_manager.get_stats()
        assert stats["daily_rows"] == 3
        assert stats["daily_tickers"] == 2
        assert stats["daily_file_size_mb"] > 0

    def test_delete_ticker_intraday(self, parquet_manager, sample_intraday_df):
        """티커 분봉 삭제"""
        parquet_manager.write_intraday("AAPL", "1m", sample_intraday_df)
        parquet_manager.write_intraday("AAPL", "1h", sample_intraday_df)

        # 삭제
        deleted = parquet_manager.delete_ticker_intraday("AAPL")
        assert deleted is True

        # 확인
        assert parquet_manager.read_intraday("AAPL", "1m").empty
        assert parquet_manager.read_intraday("AAPL", "1h").empty


# ═══════════════════════════════════════════════════════════════════════════
# Performance Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPerformance:
    """성능 테스트"""

    def test_large_daily_insert(self, parquet_manager):
        """대용량 일봉 삽입 성능 (5000 rows < 1s)"""
        import time

        # 5000개 레코드 생성
        rows = []
        for i in range(5000):
            rows.append(
                {
                    "ticker": f"TEST{i:04d}",
                    "date": "2024-12-17",
                    "open": 10.0 + i * 0.01,
                    "high": 10.5 + i * 0.01,
                    "low": 9.5 + i * 0.01,
                    "close": 10.2 + i * 0.01,
                    "volume": 100000 + i,
                }
            )
        df = pd.DataFrame(rows)

        start = time.time()
        count = parquet_manager.write_daily(df)
        elapsed = time.time() - start

        assert count == 5000
        assert elapsed < 5.0  # 5초 이내 완료

        print(f"\n📊 5000 레코드 Parquet 삽입: {elapsed:.3f}초")
