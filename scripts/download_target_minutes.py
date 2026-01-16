"""
R-4 Target-Based Minute Data Download

control_groups.csv의 (ticker, date) 조합에 대해 해당 날짜 분봉만 다운로드.
비동기 병렬 처리로 ~8분 예상.

Usage:
    python scripts/download_target_minutes.py
    python scripts/download_target_minutes.py --test     # 10건만 테스트
    python scripts/download_target_minutes.py --reset    # 진행 초기화
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger

# Project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(project_root / ".env")

from backend.data.massive_client import MassiveClient  # noqa: E402
from backend.data.parquet_manager import ParquetManager  # noqa: E402

# ==================================================
# 설정
# ==================================================
CONTROL_CSV = Path("scripts/control_groups.csv")
COVERAGE_CSV = Path("scripts/minute_coverage_report.csv")
PARQUET_DIR = Path("data/parquet")
PROGRESS_FILE = Path("data/target_download_progress.json")

# Rate limit: Massive API ~100 req/min = 0.6초/호출
REQUEST_DELAY = 0.65
MAX_CONCURRENT = 5  # 동시 요청 수 (보수적 시작)


# ==================================================
# 진행 상황 관리
# ==================================================


def load_progress() -> set:
    """완료된 (ticker, date) 조합 로드."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
            return set(tuple(x) for x in data.get("completed", []))
    return set()


def save_progress(completed: set) -> None:
    """진행 상황 저장."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(
            {
                "completed": [list(x) for x in completed],
                "last_updated": datetime.now().isoformat(),
            },
            f,
        )


# ==================================================
# 타겟 로드
# ==================================================


def load_targets() -> list[tuple[str, str]]:
    """
    control_groups.csv에서 다운로드 대상 추출.
    
    Returns:
        [(ticker, date_str), ...] 고유 조합 리스트
    """
    df = pd.read_csv(CONTROL_CSV)
    
    targets = set()
    
    # Daygainer
    for _, row in df.iterrows():
        targets.add((row["daygainer_ticker"], str(row["daygainer_date"])))
    
    # Control
    for _, row in df.iterrows():
        targets.add((row["control_ticker"], str(row["daygainer_date"])))
    
    logger.info(f"📋 고유 (ticker, date) 조합: {len(targets)}건")
    return list(targets)


# ==================================================
# 다운로드
# ==================================================


async def download_one(
    client: MassiveClient,
    pm: ParquetManager,
    ticker: str,
    date_str: str,
    semaphore: asyncio.Semaphore,
) -> bool:
    """
    단일 (ticker, date) 분봉 다운로드.
    
    해당 날짜 04:00 ~ 20:00 ET 범위 다운로드.
    """
    async with semaphore:
        try:
            # 하루치 범위 (프리마켓/애프터마켓 포함)
            bars = await client.fetch_intraday_bars(
                ticker=ticker,
                multiplier=1,
                from_date=date_str,
                to_date=date_str,
                limit=1000,  # 하루치 ~960분봉
            )
            
            if bars:
                df = pd.DataFrame(bars)
                pm.append_intraday(ticker, "1m", df)
                return True
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ {ticker} {date_str} 실패: {e}")
            return False
        finally:
            await asyncio.sleep(REQUEST_DELAY)


async def download_targets(test_mode: bool = False) -> None:
    """타겟 기반 분봉 다운로드 메인."""
    logger.info("=" * 60)
    logger.info("📥 R-4 Target-Based Minute Download")
    logger.info("=" * 60)
    
    # 타겟 로드
    all_targets = load_targets()
    
    # 진행 상황 복원
    completed = load_progress()
    remaining = [t for t in all_targets if t not in completed]
    
    logger.info(f"📌 전체: {len(all_targets)}건, 완료: {len(completed)}건, 남음: {len(remaining)}건")
    
    # 테스트 모드
    if test_mode:
        remaining = remaining[:10]
        logger.info(f"🧪 테스트 모드: {len(remaining)}건만 처리")
    
    if not remaining:
        logger.info("✅ 모든 타겟 다운로드 완료!")
        return
    
    # API 클라이언트
    api_key = os.environ.get("MASSIVE_API_KEY")
    if not api_key:
        logger.error("❌ MASSIVE_API_KEY 환경변수 없음")
        return
    
    pm = ParquetManager(str(PARQUET_DIR))
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async with MassiveClient(api_key=api_key) as client:
        total = len(remaining)
        success = 0
        errors = 0
        start_time = datetime.now()
        
        for i, (ticker, date_str) in enumerate(remaining):
            result = await download_one(client, pm, ticker, date_str, semaphore)
            
            if result:
                success += 1
                completed.add((ticker, date_str))
            else:
                errors += 1
            
            # 50건마다 저장 및 로그
            if (i + 1) % 50 == 0:
                save_progress(completed)
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (total - i - 1) / rate / 60 if rate > 0 else 0
                
                logger.info(
                    f"📊 {i + 1}/{total} ({(i + 1) / total * 100:.1f}%) "
                    f"| 성공: {success} | 오류: {errors} "
                    f"| ETA: {eta:.1f}분"
                )
    
    # 완료
    save_progress(completed)
    elapsed = (datetime.now() - start_time).total_seconds() / 60
    
    logger.info("=" * 60)
    logger.info("✅ 다운로드 완료!")
    logger.info(f"📊 성공: {success}/{total} ({success / total * 100:.1f}%)")
    logger.info(f"⏱️ 소요 시간: {elapsed:.1f}분")
    logger.info("=" * 60)


# ==================================================
# CLI
# ==================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="R-4 Target Minute Download")
    parser.add_argument("--test", action="store_true", help="Test mode (10 targets only)")
    parser.add_argument("--reset", action="store_true", help="Reset progress")
    args = parser.parse_args()
    
    if args.reset and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        logger.info("🗑️ Progress reset")
    
    asyncio.run(download_targets(test_mode=args.test))
