# ============================================================================
# Intraday Data Procurement Script
# ============================================================================
# 📌 이 파일의 역할:
#   - 8,000 종목의 1분봉/1시간봉 데이터를 Massive API로 조달
#   - 실시간 Parquet 변환 및 저장
#   - 진행 상황 실시간 로깅 및 중단 시 재개 지원
#
# 📖 사용 예시:
#   >>> python -m backend.scripts.procure_intraday_data
#   >>> python -m backend.scripts.procure_intraday_data --test  # 10개만 테스트
# ============================================================================

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# 프로젝트 루트를 PYTHONPATH에 추가
# ─────────────────────────────────────────────────────────────────────────────
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드 (API 키 등)
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from backend.data.massive_client import MassiveClient
from backend.data.parquet_manager import ParquetManager
from backend.data.database import MarketDB


# ═══════════════════════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════════════════════

# 조달 범위
DAYS_1M = 10  # 1분봉: 10 거래일
DAYS_1H = 63  # 1시간봉: 3개월 (~63 거래일)

# 경로
DB_PATH = "data/market_data.db"
PARQUET_DIR = "data/parquet"
PROGRESS_FILE = "data/procurement_progress.json"

# Rate Limit 설정 (100 req/min = 0.6초/호출)
REQUEST_DELAY = 0.6


# ═══════════════════════════════════════════════════════════════════════════
# 진행 상황 관리
# ═══════════════════════════════════════════════════════════════════════════


def load_progress() -> set:
    """완료된 티커 목록 로드 (재개 지원)"""
    import json

    progress_path = Path(PROGRESS_FILE)
    if progress_path.exists():
        with open(progress_path, "r") as f:
            data = json.load(f)
            return set(data.get("completed", []))
    return set()


def save_progress(completed: set):
    """진행 상황 저장"""
    import json

    progress_path = Path(PROGRESS_FILE)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    with open(progress_path, "w") as f:
        json.dump(
            {"completed": list(completed), "last_updated": datetime.now().isoformat()},
            f,
        )


# ═══════════════════════════════════════════════════════════════════════════
# 메인 조달 함수
# ═══════════════════════════════════════════════════════════════════════════


async def procure_intraday_data(test_mode: bool = False):
    """
    8,000 종목의 1m/1h 데이터 조달

    Args:
        test_mode: True이면 10개 종목만 테스트
    """
    logger.info("=" * 60)
    logger.info("📥 Intraday Data Procurement 시작")
    logger.info("=" * 60)

    # ─────────────────────────────────────────────────────────────────────────
    # 초기화
    # ─────────────────────────────────────────────────────────────────────────
    db = MarketDB(DB_PATH)
    await db.initialize()

    pm = ParquetManager(PARQUET_DIR)

    # 날짜 범위 계산
    end_date = datetime.now()
    start_date_1m = end_date - timedelta(days=DAYS_1M + 5)  # 여유분 추가
    start_date_1h = end_date - timedelta(days=DAYS_1H + 10)

    from_1m = start_date_1m.strftime("%Y-%m-%d")
    from_1h = start_date_1h.strftime("%Y-%m-%d")
    to_date = end_date.strftime("%Y-%m-%d")

    logger.info(f"📅 1분봉 범위: {from_1m} ~ {to_date} ({DAYS_1M}일)")
    logger.info(f"📅 1시간봉 범위: {from_1h} ~ {to_date} ({DAYS_1H}일)")

    # ─────────────────────────────────────────────────────────────────────────
    # 티커 목록 조회
    # ─────────────────────────────────────────────────────────────────────────
    tickers = await db.get_all_tickers_with_data()

    if not tickers:
        logger.warning("⚠️ DB에 티커가 없습니다. 먼저 일봉 데이터를 로드하세요.")
        return

    logger.info(f"📊 총 {len(tickers)}개 티커 발견")

    # 테스트 모드
    if test_mode:
        tickers = tickers[:10]
        logger.info(f"🧪 테스트 모드: {len(tickers)}개만 처리")

    # 진행 상황 로드 (재개 지원)
    completed = load_progress()
    remaining = [t for t in tickers if t not in completed]

    if completed:
        logger.info(
            f"📌 이전 진행 복원: {len(completed)}개 완료, {len(remaining)}개 남음"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # API 클라이언트
    # ─────────────────────────────────────────────────────────────────────────
    import os

    api_key = os.environ.get("MASSIVE_API_KEY")
    if not api_key:
        logger.error("❌ MASSIVE_API_KEY 환경변수가 설정되지 않았습니다.")
        return

    async with MassiveClient(api_key=api_key) as client:
        total = len(remaining)
        success = 0
        errors = 0
        start_time = datetime.now()

        for i, ticker in enumerate(remaining):
            try:
                # ─────────────────────────────────────────────────────────
                # 1분봉 조달
                # ─────────────────────────────────────────────────────────
                bars_1m = await client.fetch_intraday_bars(
                    ticker=ticker,
                    multiplier=1,
                    from_date=from_1m,
                    to_date=to_date,
                    limit=5000,
                )

                if bars_1m:
                    df_1m = pd.DataFrame(bars_1m)
                    pm.append_intraday(ticker, "1m", df_1m)

                await asyncio.sleep(REQUEST_DELAY)

                # ─────────────────────────────────────────────────────────
                # 1시간봉 조달
                # ─────────────────────────────────────────────────────────
                bars_1h = await client.fetch_intraday_bars(
                    ticker=ticker,
                    multiplier=60,
                    from_date=from_1h,
                    to_date=to_date,
                    limit=5000,
                )

                if bars_1h:
                    df_1h = pd.DataFrame(bars_1h)
                    pm.append_intraday(ticker, "1h", df_1h)

                await asyncio.sleep(REQUEST_DELAY)

                # ─────────────────────────────────────────────────────────
                # 진행 상황 업데이트
                # ─────────────────────────────────────────────────────────
                success += 1
                completed.add(ticker)

                # 100개마다 저장 및 로그
                if (i + 1) % 100 == 0:
                    save_progress(completed)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    eta = (total - i - 1) / rate if rate > 0 else 0

                    logger.info(
                        f"📊 진행: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%) "
                        f"| 성공: {success} | 오류: {errors} "
                        f"| ETA: {eta / 60:.1f}분"
                    )

            except Exception as e:
                errors += 1
                logger.warning(f"⚠️ {ticker} 실패: {e}")

                # 연속 오류 5회 시 중단
                if errors > 5:
                    logger.error("🛑 오류가 너무 많아 중단합니다.")
                    save_progress(completed)
                    break

    # ─────────────────────────────────────────────────────────────────────────
    # 완료 보고
    # ─────────────────────────────────────────────────────────────────────────
    save_progress(completed)
    elapsed = (datetime.now() - start_time).total_seconds() / 60

    logger.info("=" * 60)
    logger.info("✅ Procurement 완료!")
    logger.info(f"📊 성공: {success}/{total} 종목")
    logger.info(f"⏱️ 소요 시간: {elapsed:.1f}분")
    logger.info("=" * 60)

    # 최종 통계
    stats = pm.get_stats()
    logger.info(f"📦 Parquet 통계: {stats}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Intraday Data Procurement")
    parser.add_argument(
        "--test", action="store_true", help="Test mode (10 tickers only)"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Reset progress and start fresh"
    )
    args = parser.parse_args()

    if args.reset:
        progress_path = Path(PROGRESS_FILE)
        if progress_path.exists():
            progress_path.unlink()
            logger.info("🗑️ Progress reset")

    asyncio.run(procure_intraday_data(test_mode=args.test))
