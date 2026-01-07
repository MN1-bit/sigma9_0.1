# ============================================================================
# Market Data Pipeline Tests
# ============================================================================
# 📌 이 파일의 역할:
#   - database.py 모듈의 단위 테스트
#   - MarketDB CRUD 동작 검증
#   - Bulk Upsert 성능 테스트
#
# 📖 실행 방법:
#   pytest tests/test_database.py -v
# ============================================================================

import pytest
import os
import tempfile
from datetime import datetime

# 테스트 대상 모듈 임포트를 위한 경로 설정
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.data.database import MarketDB, DailyBar, Ticker


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
async def temp_db():
    """
    임시 SQLite DB 생성 Fixture
    
    테스트 후 자동으로 삭제됩니다.
    """
    # 임시 파일 생성
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # DB 초기화
    db = MarketDB(path)
    await db.initialize()
    
    yield db
    
    # 정리
    await db.close()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_bars():
    """
    테스트용 샘플 일봉 데이터
    """
    return [
        {
            "ticker": "AAPL",
            "date": "2024-12-16",
            "open": 150.0,
            "high": 152.5,
            "low": 149.0,
            "close": 151.0,
            "volume": 50000000,
            "vwap": 150.8,
            "transactions": 100000,
        },
        {
            "ticker": "AAPL",
            "date": "2024-12-17",
            "open": 151.0,
            "high": 153.0,
            "low": 150.0,
            "close": 152.0,
            "volume": 45000000,
            "vwap": 151.5,
            "transactions": 90000,
        },
        {
            "ticker": "MSFT",
            "date": "2024-12-16",
            "open": 380.0,
            "high": 385.0,
            "low": 378.0,
            "close": 382.0,
            "volume": 30000000,
            "vwap": 381.5,
            "transactions": 70000,
        },
    ]


@pytest.fixture
def sample_tickers():
    """
    테스트용 샘플 종목 정보
    """
    return [
        {
            "ticker": "TEST1",
            "name": "Test Company 1",
            "market_cap": 100_000_000,
            "outstanding_shares": 10_000_000,
            "float_shares": 5_000_000,
            "primary_exchange": "NASDAQ",
            "last_updated": "2024-12-17",
        },
        {
            "ticker": "TEST2",
            "name": "Test Company 2",
            "market_cap": 200_000_000,
            "outstanding_shares": 20_000_000,
            "float_shares": 10_000_000,
            "primary_exchange": "NYSE",
            "last_updated": "2024-12-17",
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Database Initialization Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_db_initialization(temp_db):
    """
    DB 초기화 테스트
    
    - 테이블이 생성되었는지 확인
    - WAL 모드가 활성화되었는지 확인
    """
    # 통계 조회로 테이블 존재 확인
    stats = await temp_db.get_stats()
    
    assert stats["total_bars"] == 0
    assert stats["total_tickers"] == 0
    assert stats["latest_date"] is None


@pytest.mark.asyncio
async def test_db_creation_with_directory():
    """
    디렉토리가 없을 때 자동 생성되는지 확인
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "subdir", "nested", "test.db")
        
        db = MarketDB(db_path)
        await db.initialize()
        
        # DB 파일이 생성되었는지 확인
        assert os.path.exists(db_path)
        
        await db.close()


# ═══════════════════════════════════════════════════════════════════════════
# DailyBar CRUD Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_upsert_bulk(temp_db, sample_bars):
    """
    Bulk Insert 테스트
    """
    count = await temp_db.upsert_bulk(sample_bars)
    
    assert count == 3
    
    # 통계 확인
    stats = await temp_db.get_stats()
    assert stats["total_bars"] == 3


@pytest.mark.asyncio
async def test_upsert_update(temp_db, sample_bars):
    """
    Upsert가 기존 데이터를 업데이트하는지 확인
    """
    # 첫 번째 삽입
    await temp_db.upsert_bulk(sample_bars)
    
    # 수정된 데이터로 다시 삽입
    updated_bars = [
        {
            "ticker": "AAPL",
            "date": "2024-12-16",
            "open": 150.0,
            "high": 155.0,  # 변경됨
            "low": 149.0,
            "close": 154.0,  # 변경됨
            "volume": 60000000,  # 변경됨
            "vwap": 152.0,
            "transactions": 120000,
        },
    ]
    await temp_db.upsert_bulk(updated_bars)
    
    # 총 레코드 수는 변하지 않아야 함
    stats = await temp_db.get_stats()
    assert stats["total_bars"] == 3
    
    # 업데이트된 값 확인
    bars = await temp_db.get_daily_bars("AAPL", days=5)
    dec16_bar = next(b for b in bars if b.date == "2024-12-16")
    
    assert dec16_bar.high == 155.0
    assert dec16_bar.close == 154.0
    assert dec16_bar.volume == 60000000


@pytest.mark.asyncio
async def test_get_daily_bars(temp_db, sample_bars):
    """
    일봉 조회 테스트
    """
    await temp_db.upsert_bulk(sample_bars)
    
    # AAPL 조회 (2일치)
    bars = await temp_db.get_daily_bars("AAPL", days=10)
    
    assert len(bars) == 2
    # 최신순 정렬 확인
    assert bars[0].date == "2024-12-17"
    assert bars[1].date == "2024-12-16"


@pytest.mark.asyncio
async def test_get_latest_date(temp_db, sample_bars):
    """
    최신 날짜 조회 테스트
    """
    # 데이터 없을 때
    latest = await temp_db.get_latest_date()
    assert latest is None
    
    # 데이터 삽입 후
    await temp_db.upsert_bulk(sample_bars)
    latest = await temp_db.get_latest_date()
    
    assert latest == "2024-12-17"


@pytest.mark.asyncio
async def test_get_all_tickers_with_data(temp_db, sample_bars):
    """
    데이터가 있는 종목 리스트 조회
    """
    await temp_db.upsert_bulk(sample_bars)
    
    tickers = await temp_db.get_all_tickers_with_data()
    
    assert set(tickers) == {"AAPL", "MSFT"}


# ═══════════════════════════════════════════════════════════════════════════
# Ticker CRUD Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_fundamentals(temp_db, sample_tickers):
    """
    펀더멘털 정보 Upsert 테스트
    """
    count = await temp_db.update_fundamentals(sample_tickers)
    
    assert count == 2
    
    stats = await temp_db.get_stats()
    assert stats["total_tickers"] == 2


@pytest.mark.asyncio
async def test_get_ticker_info(temp_db, sample_tickers):
    """
    종목 정보 조회 테스트
    """
    await temp_db.update_fundamentals(sample_tickers)
    
    ticker = await temp_db.get_ticker_info("TEST1")
    
    assert ticker is not None
    assert ticker.name == "Test Company 1"
    assert ticker.market_cap == 100_000_000
    
    # 없는 종목
    missing = await temp_db.get_ticker_info("INVALID")
    assert missing is None


@pytest.mark.asyncio
async def test_get_universe_candidates(temp_db, sample_tickers):
    """
    Universe Filter 테스트
    """
    await temp_db.update_fundamentals(sample_tickers)
    
    # 기본 필터 (Market Cap $50M ~ $300M, Float < 15M)
    candidates = await temp_db.get_universe_candidates(
        min_market_cap=50_000_000,
        max_market_cap=300_000_000,
        max_float=15_000_000,
    )
    
    # 둘 다 조건 만족
    assert len(candidates) == 2
    
    # Float 조건 강화
    candidates = await temp_db.get_universe_candidates(
        min_market_cap=50_000_000,
        max_market_cap=300_000_000,
        max_float=6_000_000,  # TEST2는 float 10M이라 제외됨
    )
    
    assert len(candidates) == 1
    assert candidates[0] == "TEST1"


# ═══════════════════════════════════════════════════════════════════════════
# Performance Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bulk_insert_performance(temp_db):
    """
    대량 데이터 삽입 성능 테스트
    
    5000개 종목 × 1일 = 5000 레코드
    실제 Massive Grouped Daily 응답 규모
    """
    import time
    
    # 5000개 종목 데이터 생성
    bars = []
    for i in range(5000):
        bars.append({
            "ticker": f"TEST{i:04d}",
            "date": "2024-12-17",
            "open": 10.0 + i * 0.01,
            "high": 10.5 + i * 0.01,
            "low": 9.5 + i * 0.01,
            "close": 10.2 + i * 0.01,
            "volume": 100000 + i,
            "vwap": 10.1 + i * 0.01,
            "transactions": 1000 + i,
        })
    
    start = time.time()
    count = await temp_db.upsert_bulk(bars)
    elapsed = time.time() - start
    
    assert count == 5000
    assert elapsed < 5.0  # 5초 이내 완료 기대
    
    print(f"\n📊 5000 레코드 삽입: {elapsed:.2f}초")


# ═══════════════════════════════════════════════════════════════════════════
# Empty Input Tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_upsert_empty_list(temp_db):
    """
    빈 리스트 처리 테스트
    """
    count = await temp_db.upsert_bulk([])
    assert count == 0


@pytest.mark.asyncio
async def test_update_fundamentals_empty(temp_db):
    """
    빈 펀더멘털 리스트 처리 테스트
    """
    count = await temp_db.update_fundamentals([])
    assert count == 0
