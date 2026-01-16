# ============================================================================
# Parquet 데이터 품질 검사 스크립트 (11-003, 11-004)
# ============================================================================
# 📌 이 파일의 역할:
#   - Parquet 파일 무결성 검사
#   - 필수 컴럼 존재 여부 확인
#   - OHLC 관계 무결성 검사 (11-004)
#   - 중복 레코드 검사
#   - 데이터 범위 유효성 검증
#   - JSON 리포트 출력 (11-004)
#
# 📖 사용 예시:
#   >>> python -m backend.scripts.validate_parquet_quality
#   >>> python -m backend.scripts.validate_parquet_quality --verbose
#   >>> python -m backend.scripts.validate_parquet_quality --output-json report.json
# ============================================================================

"""
Parquet 데이터 품질 검사

[11-003] 마이그레이션 후 데이터 무결성 검증
[11-004] OHLC 관계 검증, 갭 탐지, JSON 리포트 추가

검사 항목:
1. 파일 읽기 가능 여부 (무결성)
2. 필수 컴럼 존재 여부
3. OHLC 관계 무결성 (High >= max(O,C), Low <= min(O,C))
4. 중복 레코드 검사
5. NULL 값 비율
6. 데이터 범위 유효성

ELI5: 파일들이 제대로 되어있는지 건강검진을 합니다.
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import pyarrow.parquet as pq
from loguru import logger

# 11-004: 검증 모듈 import
from backend.data.validators import (
    validate_ohlc_relationship,
    validate_volume,
    detect_daily_gaps,
    detect_price_outliers,
)


# 필수 컬럼 정의
DAILY_REQUIRED_COLS = ["ticker", "date", "open", "high", "low", "close", "volume"]
INTRADAY_REQUIRED_COLS = ["timestamp", "open", "high", "low", "close", "volume"]


def validate_daily(daily_dir: Path, verbose: bool = False) -> dict:
    """
    Daily Parquet 품질 검사

    Args:
        daily_dir: daily 디렉터리 경로
        verbose: 상세 로그 출력

    Returns:
        dict: 검사 결과
    """
    results = {
        "files": 0,
        "valid": 0,
        "errors": [],
        "warnings": [],
    }

    all_daily_path = daily_dir / "all_daily.parquet"

    if not all_daily_path.exists():
        results["errors"].append("all_daily.parquet 파일 없음")
        return results

    results["files"] = 1

    try:
        df = pq.read_table(all_daily_path).to_pandas()

        # 필수 컬럼 검사
        missing = set(DAILY_REQUIRED_COLS) - set(df.columns)
        if missing:
            results["errors"].append(f"누락 컬럼: {missing}")
            return results

        # 데이터 존재 검사
        if len(df) == 0:
            results["errors"].append("빈 파일")
            return results

        # 중복 검사
        dups = df.duplicated(subset=["ticker", "date"]).sum()
        if dups > 0:
            results["warnings"].append(f"중복 레코드: {dups}건")

        # NULL 값 검사
        null_counts = df[DAILY_REQUIRED_COLS].isnull().sum()
        null_cols = null_counts[null_counts > 0]
        if len(null_cols) > 0:
            results["warnings"].append(f"NULL 값 발견: {null_cols.to_dict()}")

        # 티커 수, 날짜 범위
        num_tickers = df["ticker"].nunique()
        date_range = f"{df['date'].min()} ~ {df['date'].max()}"

        if verbose:
            logger.info(f"  📊 티커 수: {num_tickers}")
            logger.info(f"  📅 날짜 범위: {date_range}")
            logger.info(f"  📝 레코드 수: {len(df)}")

        # [11-004] OHLC 관계 검증
        ohlc_violations = validate_ohlc_relationship(df)
        if ohlc_violations:
            results["warnings"].append(f"OHLC 위반: {len(ohlc_violations)}건")
            results["ohlc_violations"] = ohlc_violations[:10]  # 상위 10건만 저장

        # [11-004] Volume 검증 (음수)
        vol_violations = validate_volume(df)
        if vol_violations:
            results["warnings"].append(f"Volume 음수: {len(vol_violations)}건")

        # [11-004] Volume 누락 (OHLC는 있는데 Volume이 0 또는 NULL)
        vol_missing_mask = ((df["volume"].isnull()) | (df["volume"] == 0)) & (
            df["close"] > 0
        )
        vol_missing_count = vol_missing_mask.sum()
        if vol_missing_count > 0:
            results["warnings"].append(f"Volume 누락(0/NULL): {vol_missing_count}건")
            # 샘플 5개 저장
            sample_tickers = (
                df[vol_missing_mask].head(5)[["ticker", "date"]].to_dict("records")
            )
            results["volume_missing_samples"] = sample_tickers

        # [11-004] 날짜 갭 검사 (티커별 거래일 누락)
        # 상위 100개 티커만 샘플 검사 (전체는 너무 느림)
        top_tickers = df["ticker"].value_counts().head(100).index.tolist()
        df_sample = df[df["ticker"].isin(top_tickers)]
        date_gaps = detect_daily_gaps(df_sample)
        total_gap_days = sum(len(v) for v in date_gaps.values())
        if total_gap_days > 0:
            results["warnings"].append(
                f"날짜 갭: {len(date_gaps)} 티커, {total_gap_days}일"
            )
            # 상위 5개 티커 갭 저장
            results["date_gaps_sample"] = {
                k: v[:5] for k, v in list(date_gaps.items())[:5]
            }

        # [11-004] 가격 이상치 (Z-score > 3)
        # 티커별로 그룹핑하여 검사
        total_outliers = 0
        outlier_samples = []
        for ticker in top_tickers[:20]:  # 상위 20개만
            ticker_df = df[df["ticker"] == ticker].sort_values("date")
            if len(ticker_df) < 10:
                continue
            outliers = detect_price_outliers(ticker_df, z_threshold=4.0)
            if outliers:
                total_outliers += len(outliers)
                for o in outliers[:2]:
                    o["ticker"] = ticker
                    outlier_samples.append(o)

        if total_outliers > 0:
            results["warnings"].append(f"가격 이상치: {total_outliers}건 (z>4)")
            results["price_outliers_sample"] = outlier_samples[:10]

        results["valid"] = 1
        results["stats"] = {
            "tickers": num_tickers,
            "records": len(df),
            "date_range": date_range,
            "ohlc_violations": len(ohlc_violations),
            "volume_violations": len(vol_violations),
            "volume_missing": vol_missing_count,
            "date_gaps_tickers": len(date_gaps),
            "date_gaps_days": total_gap_days,
            "price_outliers": total_outliers,
        }

    except Exception as e:
        results["errors"].append(f"읽기 실패: {e}")

    return results


def _validate_single_intraday_file(
    file_path: Path,
    tf: str,
    full_ohlc: bool = False,
) -> dict:
    """
    단일 Intraday 파일 검사 (병렬 처리용 헬퍼)

    Args:
        file_path: 파일 경로
        tf: 타임프레임
        full_ohlc: OHLC 관계 검사 포함 여부

    Returns:
        dict: {valid, error, warning, ohlc_violations}
    """
    result = {
        "file": str(file_path),
        "tf": tf,
        "valid": False,
        "error": None,
        "warning": None,
        "ohlc_violations": 0,
        "records": 0,
    }

    try:
        df = pq.read_table(file_path).to_pandas()
        result["records"] = len(df)

        # 필수 컬럼 검사
        missing = set(INTRADAY_REQUIRED_COLS) - set(df.columns)
        if missing:
            result["error"] = f"누락 컬럼 {missing}"
            return result

        # 빈 파일 검사
        if len(df) == 0:
            result["error"] = "빈 파일"
            return result

        # 중복 검사
        dups = df.duplicated(subset=["timestamp"]).sum()
        if dups > 0:
            result["warning"] = f"중복 {dups}건"

        # [11-004] OHLC 관계 검사 (full 모드)
        if full_ohlc:
            ohlc_violations = validate_ohlc_relationship(df)
            result["ohlc_violations"] = len(ohlc_violations)
            if ohlc_violations:
                result["warning"] = f"OHLC 위반 {len(ohlc_violations)}건"

        result["valid"] = True

    except Exception as e:
        result["error"] = f"읽기 실패 - {e}"

    return result


def validate_intraday(
    base_dir: Path,
    verbose: bool = False,
    full_ohlc: bool = False,
    sample_ratio: float = 1.0,
    max_workers: int = 4,
) -> dict:
    """
    Intraday Parquet 품질 검사 (TF별 폴더 구조)

    Args:
        base_dir: Parquet 베이스 디렉터리
        verbose: 상세 로그 출력
        full_ohlc: OHLC 관계 심층 검사 (느림)
        sample_ratio: 샘플링 비율 (0.1 = 10%, 1.0 = 전체)
        max_workers: 병렬 처리 스레드 수

    Returns:
        dict: 검사 결과
    """
    import random
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {
        "files": 0,
        "valid": 0,
        "errors": [],
        "warnings": [],
        "ohlc_violations_total": 0,
        "by_tf": defaultdict(
            lambda: {"files": 0, "valid": 0, "errors": 0, "ohlc_violations": 0}
        ),
        "mode": "full" if full_ohlc else "quick",
        "sample_ratio": sample_ratio,
    }

    # TF별 폴더에서 파일 목록 수집
    tf_folders = ["1m", "3m", "5m", "15m", "1h", "4h"]
    all_files: list[tuple[Path, str]] = []  # (file_path, tf)

    for tf in tf_folders:
        tf_dir = base_dir / tf
        if not tf_dir.exists():
            continue
        for f in tf_dir.glob("*.parquet"):
            all_files.append((f, tf))

    # 샘플링
    total_files = len(all_files)
    if sample_ratio < 1.0:
        sample_size = max(1, int(total_files * sample_ratio))
        all_files = random.sample(all_files, sample_size)
        logger.info(
            f"🎲 샘플링: {total_files} → {len(all_files)}개 ({sample_ratio * 100:.0f}%)"
        )

    results["files"] = len(all_files)

    # 병렬 검사
    logger.info(
        f"🔍 {len(all_files)}개 파일 검사 시작 (workers={max_workers}, full_ohlc={full_ohlc})"
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_validate_single_intraday_file, f, tf, full_ohlc): (f, tf)
            for f, tf in all_files
        }

        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            if verbose and done_count % 1000 == 0:
                logger.info(f"  진행: {done_count}/{len(all_files)}")

            result = future.result()
            tf = result["tf"]
            results["by_tf"][tf]["files"] += 1

            if result["valid"]:
                results["valid"] += 1
                results["by_tf"][tf]["valid"] += 1
            if result["error"]:
                results["errors"].append(
                    f"{tf}/{Path(result['file']).name}: {result['error']}"
                )
                results["by_tf"][tf]["errors"] += 1
            if result["warning"]:
                results["warnings"].append(
                    f"{tf}/{Path(result['file']).name}: {result['warning']}"
                )
            if result["ohlc_violations"] > 0:
                results["ohlc_violations_total"] += result["ohlc_violations"]
                results["by_tf"][tf]["ohlc_violations"] = (
                    results["by_tf"][tf].get("ohlc_violations", 0)
                    + result["ohlc_violations"]
                )

    logger.info(f"✅ 검사 완료: {results['valid']}/{results['files']} 정상")

    return results


def main():
    """CLI 진입점"""
    parser = argparse.ArgumentParser(
        description="Parquet 데이터 품질 검사 (11-003, 11-004)"
    )
    parser.add_argument(
        "--base-dir",
        default="data/parquet",
        help="Parquet 베이스 디렉터리 (기본: data/parquet)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="JSON 리포트 출력 경로 (예: data/reports/integrity.json)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Intraday OHLC 심층 검사 포함 (느림, ~10분)",
    )
    parser.add_argument(
        "--sample",
        type=float,
        default=1.0,
        help="샘플링 비율 (0.1 = 10%%, 1.0 = 전체, 기본: 1.0)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="병렬 처리 스레드 수 (기본: 4)",
    )

    args = parser.parse_args()

    base_dir = Path(args.base_dir)

    if not base_dir.exists():
        logger.error(f"❌ 디렉터리가 존재하지 않습니다: {base_dir}")
        sys.exit(1)

    print("=" * 60)
    print("Parquet 데이터 품질 검사 (11-003)")
    print("=" * 60)

    total_errors = 0

    # Daily 검사
    print("\n📊 Daily 데이터 검사:")
    daily_results = validate_daily(base_dir / "daily", verbose=args.verbose)
    print(f"  파일 수: {daily_results['files']}")
    print(f"  정상: {daily_results['valid']}")
    print(f"  오류: {len(daily_results['errors'])}")
    print(f"  경고: {len(daily_results['warnings'])}")

    if daily_results.get("stats"):
        stats = daily_results["stats"]
        print(f"  ├─ 티커: {stats['tickers']}개")
        print(f"  ├─ 레코드: {stats['records']:,}개")
        print(f"  └─ 날짜: {stats['date_range']}")

    for err in daily_results["errors"][:3]:
        print(f"    ⛔ {err}")
    for warn in daily_results["warnings"][:3]:
        print(f"    ⚠️ {warn}")

    total_errors += len(daily_results["errors"])

    # Intraday 검사
    mode_str = "심층(OHLC)" if args.full else "빠른"
    sample_str = f" (샘플 {args.sample * 100:.0f}%)" if args.sample < 1.0 else ""
    print(f"\n📊 Intraday 데이터 검사 ({mode_str}{sample_str}):")

    intraday_results = validate_intraday(
        base_dir,
        verbose=args.verbose,
        full_ohlc=args.full,
        sample_ratio=args.sample,
        max_workers=args.workers,
    )
    print(f"  파일 수: {intraday_results['files']}")
    print(f"  정상: {intraday_results['valid']}")
    print(f"  오류: {len(intraday_results['errors'])}")
    print(f"  경고: {len(intraday_results['warnings'])}")
    if args.full and intraday_results.get("ohlc_violations_total", 0) > 0:
        print(f"  OHLC 위반: {intraday_results['ohlc_violations_total']}건")

    if intraday_results["by_tf"]:
        print("\n  타임프레임별:")
        for tf, stats in sorted(intraday_results["by_tf"].items()):
            if stats["files"] > 0:
                valid_pct = (
                    (stats["valid"] / stats["files"] * 100) if stats["files"] else 0
                )
                print(f"    {tf}: {stats['files']} 파일 ({valid_pct:.0f}% 정상)")

    for err in intraday_results["errors"][:5]:
        print(f"    ⛔ {err}")

    total_errors += len(intraday_results["errors"])

    # 최종 결과
    print("\n" + "=" * 60)
    if total_errors == 0:
        print("✅ 모든 데이터 품질 검사 통과!")
    else:
        print(f"⚠️ 총 {total_errors}건의 오류 발견")

    # [11-004] JSON 리포트 출력
    if args.output_json:
        report = {
            "generated_at": datetime.now().isoformat(),
            "base_dir": str(base_dir),
            "daily": daily_results,
            "intraday": {
                k: v
                for k, v in intraday_results.items()
                if k != "by_tf"  # defaultdict 직렬화 문제 회피
            },
            "intraday_by_tf": dict(intraday_results.get("by_tf", {})),
            "total_errors": total_errors,
            "passed": total_errors == 0,
        }

        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n📄 JSON 리포트 저장: {output_path}")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
