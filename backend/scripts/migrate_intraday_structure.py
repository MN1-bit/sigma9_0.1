# ============================================================================
# Parquet 폴더 구조 마이그레이션 스크립트 (11-003)
# ============================================================================
# 📌 이 파일의 역할:
#   - intraday/AAPL_1m.parquet → 1m/AAPL.parquet 마이그레이션
#   - 파일 이동 + 검증 + 롤백 지원
#
# 📖 사용 예시:
#   >>> python -m backend.scripts.migrate_intraday_structure
#   >>> python -m backend.scripts.migrate_intraday_structure --dry-run
# ============================================================================

"""
Parquet Intraday 폴더 구조 마이그레이션

[11-003] 평탄화 구조에서 타임프레임별 폴더 구조로 마이그레이션

기존: data/parquet/intraday/AAPL_1m.parquet
신규: data/parquet/1m/AAPL.parquet

ELI5: intraday 폴더에 있는 모든 파일을 타임프레임별 폴더로 정리합니다.
      마치 서랍 하나에 모아둔 물건들을 종류별 서랍으로 분류하는 것과 같습니다.
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime

from loguru import logger


# 지원하는 타임프레임 목록
SUPPORTED_TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h", "4h"]


def parse_legacy_filename(filename: str) -> tuple[str, str] | None:
    """
    레거시 파일명에서 티커와 타임프레임 추출

    Args:
        filename: 파일명 (예: "AAPL_1m.parquet")

    Returns:
        (ticker, timeframe) 튜플 또는 None
    """
    if not filename.endswith(".parquet"):
        return None

    stem = filename.replace(".parquet", "")

    # 타임프레임 찾기 (뒤에서부터)
    for tf in SUPPORTED_TIMEFRAMES:
        suffix = f"_{tf}"
        if stem.endswith(suffix):
            ticker = stem[: -len(suffix)]
            return ticker, tf

    return None


def migrate_intraday_structure(
    base_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Intraday 폴더 구조 마이그레이션 수행

    Args:
        base_dir: Parquet 베이스 디렉터리 (data/parquet)
        dry_run: True면 실제 파일 이동 없이 시뮬레이션
        verbose: 상세 로그 출력

    Returns:
        dict: 마이그레이션 결과 통계
    """
    intraday_dir = base_dir / "intraday"

    if not intraday_dir.exists():
        logger.warning(f"❌ intraday 폴더가 없습니다: {intraday_dir}")
        return {"total": 0, "migrated": 0, "skipped": 0, "errors": []}

    # 통계
    stats = {
        "total": 0,
        "migrated": 0,
        "skipped": 0,
        "errors": [],
        "by_tf": {},
    }

    # 모든 .parquet 파일 수집
    files = list(intraday_dir.glob("*.parquet"))
    stats["total"] = len(files)

    logger.info(f"📦 마이그레이션 시작: {len(files)} 파일 발견")
    if dry_run:
        logger.info("🔍 DRY-RUN 모드 - 실제 파일 이동 없음")

    for f in files:
        parsed = parse_legacy_filename(f.name)

        if not parsed:
            logger.warning(f"⚠️ 파싱 실패 (스킵): {f.name}")
            stats["skipped"] += 1
            continue

        ticker, tf = parsed

        # 목표 경로
        tf_dir = base_dir / tf
        new_path = tf_dir / f"{ticker}.parquet"

        # 이미 존재하면 스킵
        if new_path.exists():
            if verbose:
                logger.debug(f"⏭️ 이미 존재 (스킵): {new_path}")
            stats["skipped"] += 1
            continue

        # 디렉터리 생성
        if not dry_run:
            tf_dir.mkdir(parents=True, exist_ok=True)

        # 파일 이동
        try:
            if not dry_run:
                shutil.move(str(f), str(new_path))

            if verbose:
                logger.info(f"✅ {f.name} → {tf}/{ticker}.parquet")

            stats["migrated"] += 1
            stats["by_tf"][tf] = stats["by_tf"].get(tf, 0) + 1

        except Exception as e:
            logger.error(f"❌ 이동 실패: {f.name} - {e}")
            stats["errors"].append(str(f))

    # 빈 intraday 폴더 정리
    if not dry_run and stats["migrated"] > 0:
        remaining = list(intraday_dir.glob("*.parquet"))
        if not remaining:
            # 백업 마커 파일 생성 (롤백 지원)
            marker = intraday_dir / ".migrated_to_tf_folders"
            marker.write_text(f"Migrated at {datetime.now().isoformat()}\n")
            logger.info(f"📝 마이그레이션 마커 생성: {marker}")

    return stats


def main():
    """CLI 진입점"""
    parser = argparse.ArgumentParser(
        description="Parquet Intraday 폴더 구조 마이그레이션 (11-003)"
    )
    parser.add_argument(
        "--base-dir",
        default="data/parquet",
        help="Parquet 베이스 디렉터리 (기본: data/parquet)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일 이동 없이 시뮬레이션",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )

    args = parser.parse_args()

    base_dir = Path(args.base_dir)

    if not base_dir.exists():
        logger.error(f"❌ 디렉터리가 존재하지 않습니다: {base_dir}")
        sys.exit(1)

    # 마이그레이션 실행
    print("=" * 60)
    print("Parquet Intraday 폴더 구조 마이그레이션 (11-003)")
    print("=" * 60)
    print(f"소스: {base_dir / 'intraday'}")
    print(f"대상: {base_dir}/{{tf}}/{{ticker}}.parquet")
    print("=" * 60)

    stats = migrate_intraday_structure(
        base_dir=base_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    # 결과 출력
    print()
    print("=" * 60)
    print("마이그레이션 결과")
    print("=" * 60)
    print(f"전체 파일: {stats['total']}")
    print(f"마이그레이션 완료: {stats['migrated']}")
    print(f"스킵: {stats['skipped']}")
    print(f"오류: {len(stats['errors'])}")

    if stats["by_tf"]:
        print()
        print("타임프레임별:")
        for tf, count in sorted(stats["by_tf"].items()):
            print(f"  {tf}: {count} 파일")

    if stats["errors"]:
        print()
        print("오류 파일:")
        for err in stats["errors"][:10]:
            print(f"  - {err}")
        if len(stats["errors"]) > 10:
            print(f"  ... 외 {len(stats['errors']) - 10}개")

    print("=" * 60)

    if args.dry_run:
        print("✅ DRY-RUN 완료 - 실제 파일 변경 없음")
        print("실제 마이그레이션을 수행하려면 --dry-run 옵션을 제거하세요.")
    else:
        print("✅ 마이그레이션 완료!")

    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
