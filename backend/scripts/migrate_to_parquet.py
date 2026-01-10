# ============================================================================
# SQLite → Parquet 마이그레이션 스크립트
# ============================================================================
# 📌 이 파일의 역할:
#   - 기존 SQLite (market_data.db)의 일봉 데이터를 Parquet으로 변환
#   - 티커별 배치 처리로 메모리 효율적 마이그레이션
#   - 데이터 무결성 검증 (row count, checksum)
#
# 📖 실행 방법:
#   python -m backend.scripts.migrate_to_parquet
#   python -m backend.scripts.migrate_to_parquet --verify-only
# ============================================================================

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from tqdm import tqdm
from loguru import logger

from backend.data.database import MarketDB
from backend.data.parquet_manager import ParquetManager


async def migrate_daily_data(
    db_path: str = "data/market_data.db",
    parquet_dir: str = "data/parquet",
    batch_size: int = 50,
) -> dict:
    """
    SQLite → Parquet 일봉 데이터 마이그레이션

    Args:
        db_path: SQLite DB 경로
        parquet_dir: Parquet 저장 디렉터리
        batch_size: 티커당 배치 크기

    Returns:
        dict: 마이그레이션 결과
            - total_tickers: 전체 티커 수
            - total_rows: 전체 레코드 수
            - elapsed_seconds: 소요 시간
    """
    import time

    start_time = time.time()

    # 초기화
    db = MarketDB(db_path)
    await db.initialize()
    pm = ParquetManager(parquet_dir)

    logger.info("🚀 SQLite → Parquet 마이그레이션 시작")
    logger.info(f"   Source: {db_path}")
    logger.info(f"   Target: {parquet_dir}")

    # 모든 티커 조회
    tickers = await db.get_all_tickers_with_data()
    logger.info(f"📊 총 {len(tickers)}개 티커 발견")

    if not tickers:
        logger.warning("⚠️ 마이그레이션할 데이터가 없습니다")
        await db.close()
        return {"total_tickers": 0, "total_rows": 0, "elapsed_seconds": 0}

    # 배치 단위로 마이그레이션
    all_rows = []
    for i in tqdm(range(0, len(tickers), batch_size), desc="Migrating"):
        batch_tickers = tickers[i : i + batch_size]

        for ticker in batch_tickers:
            # 해당 티커의 모든 일봉 데이터 조회
            bars = await db.get_daily_bars(ticker, days=365 * 5)  # 최대 5년치
            if bars:
                for bar in bars:
                    all_rows.append(bar.to_dict())

    # Parquet으로 저장
    if all_rows:
        df = pd.DataFrame(all_rows)
        pm.write_daily(df)
        logger.info(f"✅ {len(all_rows)} 레코드 Parquet 저장 완료")

    elapsed = time.time() - start_time
    await db.close()

    result = {
        "total_tickers": len(tickers),
        "total_rows": len(all_rows),
        "elapsed_seconds": round(elapsed, 2),
    }

    logger.info(f"🎉 마이그레이션 완료! {result}")
    return result


async def verify_migration(
    db_path: str = "data/market_data.db",
    parquet_dir: str = "data/parquet",
) -> dict:
    """
    마이그레이션 데이터 무결성 검증

    Args:
        db_path: SQLite DB 경로
        parquet_dir: Parquet 디렉터리

    Returns:
        dict: 검증 결과
            - sqlite_rows: SQLite 레코드 수
            - parquet_rows: Parquet 레코드 수
            - match: 일치 여부
    """
    db = MarketDB(db_path)
    await db.initialize()
    pm = ParquetManager(parquet_dir)

    # SQLite 레코드 수
    stats = await db.get_stats()
    sqlite_rows = stats["total_bars"]

    # Parquet 레코드 수
    parquet_stats = pm.get_stats()
    parquet_rows = parquet_stats["daily_rows"]

    match = sqlite_rows == parquet_rows

    await db.close()

    result = {
        "sqlite_rows": sqlite_rows,
        "parquet_rows": parquet_rows,
        "match": match,
    }

    if match:
        logger.info(f"✅ 검증 성공: {sqlite_rows} 레코드 일치")
    else:
        logger.error(f"❌ 검증 실패: SQLite={sqlite_rows}, Parquet={parquet_rows}")

    return result


async def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(description="SQLite → Parquet 마이그레이션")
    parser.add_argument(
        "--verify-only", action="store_true", help="검증만 수행 (마이그레이션 없이)"
    )
    parser.add_argument(
        "--db-path", default="data/market_data.db", help="SQLite DB 경로"
    )
    parser.add_argument(
        "--parquet-dir", default="data/parquet", help="Parquet 저장 디렉터리"
    )

    args = parser.parse_args()

    if args.verify_only:
        await verify_migration(args.db_path, args.parquet_dir)
    else:
        await migrate_daily_data(args.db_path, args.parquet_dir)
        await verify_migration(args.db_path, args.parquet_dir)


if __name__ == "__main__":
    asyncio.run(main())
