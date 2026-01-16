# ============================================================================
# Parquet 데이터 복구 스크립트 (11-004)
# ============================================================================
# 📌 이 파일의 역할:
#   - 중복 레코드 자동 제거
#   - NULL 값 보간/삭제
#   - Dry-run 모드 지원
#   - 복구 전 자동 백업 (변경 파일만)
#
# 📖 사용 예시:
#   >>> python -m backend.scripts.repair_parquet_data --dry-run
#   >>> python -m backend.scripts.repair_parquet_data --apply
# ============================================================================

"""
Parquet 데이터 복구 CLI (11-004)

데이터 품질 문제를 자동으로 수정하는 복구 스크립트.

기능:
1. 중복 레코드 제거 (ticker+date 기준)
2. NULL 값 처리 (forward fill / linear interpolation)
3. Dry-run 모드 (실제 수정 없이 시뮬레이션)
4. 변경 파일만 백업

ELI5: 문제 있는 데이터를 자동으로 고쳐주는 의사.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pyarrow.parquet as pq
from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# DataRepairer 클래스
# ═══════════════════════════════════════════════════════════════════════════


class DataRepairer:
    """
    Parquet 데이터 복구 클래스

    중복 제거, NULL 처리 등 데이터 품질 문제를 자동으로 수정합니다.

    Attributes:
        base_dir: Parquet 베이스 디렉터리
        backup_dir: 백업 저장 디렉터리
        dry_run: True면 실제 수정 없이 시뮬레이션만

    Example:
        >>> repairer = DataRepairer(Path("data/parquet"), dry_run=True)
        >>> report = repairer.repair_all()
        >>> print(report)
    """

    def __init__(
        self,
        base_dir: Path,
        backup_dir: Path = None,
        dry_run: bool = True,
    ):
        """
        DataRepairer 초기화

        Args:
            base_dir: Parquet 베이스 디렉터리
            backup_dir: 백업 저장 디렉터리 (기본: data/backup)
            dry_run: True면 실제 수정 없이 시뮬레이션
        """
        self.base_dir = Path(base_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else Path("data/backup")
        self.dry_run = dry_run

        # 복구 리포트
        self.report: dict = {
            "started_at": datetime.now().isoformat(),
            "dry_run": dry_run,
            "actions": [],
            "errors": [],
        }

        logger.info(f"🔧 DataRepairer 초기화: base_dir={base_dir}, dry_run={dry_run}")

    # ═══════════════════════════════════════════════════════════════════════
    # 백업
    # ═══════════════════════════════════════════════════════════════════════

    def backup_file(self, file_path: Path) -> Path | None:
        """
        파일 백업 생성

        Args:
            file_path: 백업할 파일 경로

        Returns:
            Path: 백업 파일 경로 (dry_run이면 None)
        """
        if self.dry_run:
            logger.info(f"  [DRY-RUN] 백업 생략: {file_path.name}")
            return None

        # 백업 디렉터리 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / timestamp
        backup_subdir.mkdir(parents=True, exist_ok=True)

        # 상대 경로 유지하여 백업
        relative_path = file_path.relative_to(self.base_dir)
        backup_path = backup_subdir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(file_path, backup_path)
        logger.info(f"  💾 백업 완료: {backup_path}")

        return backup_path

    # ═══════════════════════════════════════════════════════════════════════
    # 중복 제거
    # ═══════════════════════════════════════════════════════════════════════

    def remove_duplicates_daily(self) -> int:
        """
        Daily 데이터에서 중복 레코드 제거

        (ticker, date) 기준으로 중복 제거, 마지막 레코드 유지.

        Returns:
            int: 제거된 중복 레코드 수
        """
        daily_path = self.base_dir / "daily" / "all_daily.parquet"

        if not daily_path.exists():
            logger.warning("⚠️ all_daily.parquet 없음")
            return 0

        try:
            df = pq.read_table(daily_path).to_pandas()
            original_count = len(df)

            # 중복 확인
            dups = df.duplicated(subset=["ticker", "date"], keep="last")
            dup_count = dups.sum()

            if dup_count == 0:
                logger.info("✅ Daily 데이터: 중복 없음")
                return 0

            logger.info(f"🔍 Daily 중복 발견: {dup_count}건")

            # 중복 제거
            df_dedup = df[~dups].reset_index(drop=True)

            if not self.dry_run:
                # 백업 후 저장
                self.backup_file(daily_path)
                df_dedup.to_parquet(daily_path, index=False)
                logger.info(f"✅ Daily 중복 제거 완료: {dup_count}건")
            else:
                logger.info(f"  [DRY-RUN] 중복 제거 예정: {dup_count}건")

            self.report["actions"].append(
                {
                    "type": "remove_duplicates",
                    "file": str(daily_path),
                    "removed": dup_count,
                    "original": original_count,
                    "final": len(df_dedup),
                }
            )

            return dup_count

        except Exception as e:
            logger.error(f"❌ Daily 중복 제거 실패: {e}")
            self.report["errors"].append(
                {
                    "type": "remove_duplicates",
                    "file": str(daily_path),
                    "error": str(e),
                }
            )
            return 0

    def remove_duplicates_intraday(self) -> int:
        """
        Intraday 데이터에서 중복 레코드 제거

        timestamp 기준으로 중복 제거.

        Returns:
            int: 총 제거된 중복 레코드 수
        """
        total_removed = 0
        tf_folders = ["1m", "3m", "5m", "15m", "1h", "4h"]

        for tf in tf_folders:
            tf_dir = self.base_dir / tf
            if not tf_dir.exists():
                continue

            for f in tf_dir.glob("*.parquet"):
                try:
                    df = pq.read_table(f).to_pandas()

                    dups = df.duplicated(subset=["timestamp"], keep="last")
                    dup_count = dups.sum()

                    if dup_count == 0:
                        continue

                    df_dedup = df[~dups].reset_index(drop=True)

                    if not self.dry_run:
                        self.backup_file(f)
                        df_dedup.to_parquet(f, index=False)

                    total_removed += dup_count

                    self.report["actions"].append(
                        {
                            "type": "remove_duplicates",
                            "file": str(f),
                            "removed": dup_count,
                        }
                    )

                    logger.info(
                        f"  {'[DRY-RUN] ' if self.dry_run else ''}"
                        f"{tf}/{f.name}: 중복 {dup_count}건 제거"
                    )

                except Exception as e:
                    logger.error(f"❌ {f}: 처리 실패 - {e}")
                    self.report["errors"].append(
                        {
                            "type": "remove_duplicates",
                            "file": str(f),
                            "error": str(e),
                        }
                    )

        return total_removed

    # ═══════════════════════════════════════════════════════════════════════
    # NULL 처리
    # ═══════════════════════════════════════════════════════════════════════

    def fill_nulls_daily(self, strategy: str = "ffill") -> int:
        """
        Daily 데이터에서 NULL 값 처리

        OHLCV 컬럼의 NULL을 보간합니다.

        Args:
            strategy: 보간 전략 ('ffill', 'linear', 'drop')

        Returns:
            int: 처리된 NULL 셀 수
        """
        daily_path = self.base_dir / "daily" / "all_daily.parquet"

        if not daily_path.exists():
            return 0

        try:
            df = pq.read_table(daily_path).to_pandas()

            # OHLCV 컬럼만 대상
            price_cols = ["open", "high", "low", "close", "volume"]
            null_counts = df[price_cols].isnull().sum()
            total_nulls = null_counts.sum()

            if total_nulls == 0:
                logger.info("✅ Daily 데이터: NULL 없음")
                return 0

            logger.info(f"🔍 Daily NULL 발견: {total_nulls}건")
            logger.debug(f"  컬럼별: {null_counts.to_dict()}")

            # NULL 처리
            if strategy == "drop":
                # NULL 있는 행 삭제
                df_clean = df.dropna(subset=price_cols)
            elif strategy == "linear":
                # 선형 보간
                df_clean = df.copy()
                df_clean[price_cols] = df_clean[price_cols].interpolate(method="linear")
            else:
                # Forward fill (기본값)
                df_clean = df.copy()
                df_clean[price_cols] = df_clean[price_cols].ffill()

            if not self.dry_run:
                self.backup_file(daily_path)
                df_clean.to_parquet(daily_path, index=False)
                logger.info(f"✅ Daily NULL 처리 완료: {total_nulls}건 ({strategy})")
            else:
                logger.info(f"  [DRY-RUN] NULL 처리 예정: {total_nulls}건")

            self.report["actions"].append(
                {
                    "type": "fill_nulls",
                    "file": str(daily_path),
                    "strategy": strategy,
                    "processed": int(total_nulls),
                }
            )

            return int(total_nulls)

        except Exception as e:
            logger.error(f"❌ Daily NULL 처리 실패: {e}")
            self.report["errors"].append(
                {
                    "type": "fill_nulls",
                    "file": str(daily_path),
                    "error": str(e),
                }
            )
            return 0

    # ═══════════════════════════════════════════════════════════════════════
    # 전체 복구
    # ═══════════════════════════════════════════════════════════════════════

    def repair_all(self, null_strategy: str = "ffill") -> dict:
        """
        전체 데이터 복구 실행

        1. Daily 중복 제거
        2. Intraday 중복 제거
        3. Daily NULL 처리

        Args:
            null_strategy: NULL 처리 전략

        Returns:
            dict: 복구 리포트
        """
        logger.info("=" * 60)
        logger.info("🔧 데이터 복구 시작")
        logger.info(f"   모드: {'DRY-RUN' if self.dry_run else 'APPLY'}")
        logger.info("=" * 60)

        # 1. 중복 제거
        print("\n📊 중복 레코드 제거:")
        daily_dups = self.remove_duplicates_daily()
        intraday_dups = self.remove_duplicates_intraday()
        print(f"  Daily: {daily_dups}건")
        print(f"  Intraday: {intraday_dups}건")

        # 2. NULL 처리
        print("\n📊 NULL 값 처리:")
        daily_nulls = self.fill_nulls_daily(strategy=null_strategy)
        print(f"  Daily: {daily_nulls}건 ({null_strategy})")

        # 리포트 완료
        self.report["completed_at"] = datetime.now().isoformat()
        self.report["summary"] = {
            "duplicates_removed": daily_dups + intraday_dups,
            "nulls_processed": daily_nulls,
            "total_actions": len(self.report["actions"]),
            "total_errors": len(self.report["errors"]),
        }

        logger.info("=" * 60)
        if self.dry_run:
            logger.info("🔍 DRY-RUN 완료 - 실제 변경 없음")
        else:
            logger.info("✅ 데이터 복구 완료")
        logger.info("=" * 60)

        return self.report


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main():
    """CLI 진입점"""
    parser = argparse.ArgumentParser(description="Parquet 데이터 복구 (11-004)")
    parser.add_argument(
        "--base-dir",
        default="data/parquet",
        help="Parquet 베이스 디렉터리 (기본: data/parquet)",
    )
    parser.add_argument(
        "--backup-dir",
        default="data/backup",
        help="백업 저장 디렉터리 (기본: data/backup)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 수정 없이 시뮬레이션 (기본 동작)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제로 데이터 수정 적용",
    )
    parser.add_argument(
        "--null-strategy",
        choices=["ffill", "linear", "drop"],
        default="ffill",
        help="NULL 처리 전략 (기본: ffill)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="JSON 리포트 출력 경로",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )

    args = parser.parse_args()

    # dry_run 결정: --apply 없으면 기본 dry_run
    dry_run = not args.apply

    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        logger.error(f"❌ 디렉터리가 존재하지 않습니다: {base_dir}")
        sys.exit(1)

    # 복구 실행
    repairer = DataRepairer(
        base_dir=base_dir,
        backup_dir=Path(args.backup_dir),
        dry_run=dry_run,
    )

    report = repairer.repair_all(null_strategy=args.null_strategy)

    # JSON 리포트 저장
    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 JSON 리포트 저장: {output_path}")

    # 종료 코드
    return 0 if len(report["errors"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
