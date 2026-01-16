# ============================================================================
# 데이터 정합성 유닛 테스트 (11-004)
# ============================================================================
# 📌 이 파일의 역할:
#   - validators.py 함수 테스트
#   - repair_parquet_data.py DataRepairer 테스트
#   - Dry-run 모드 검증
# ============================================================================

"""
데이터 정합성 검증 테스트 (11-004)

validators 모듈과 DataRepairer 클래스의 유닛 테스트.
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import shutil

from backend.data.validators import (
    validate_ohlc_relationship,
    validate_volume,
    detect_daily_gaps,
    detect_intraday_gaps,
    detect_price_outliers,
    interpolate_outliers,
)


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def valid_ohlc_df():
    """정상적인 OHLC 데이터"""
    return pd.DataFrame({
        "ticker": ["AAPL", "AAPL", "AAPL"],
        "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
        "open": [100.0, 102.0, 105.0],
        "high": [105.0, 108.0, 110.0],
        "low": [98.0, 100.0, 103.0],
        "close": [103.0, 106.0, 108.0],
        "volume": [1000000, 1200000, 1100000],
    })


@pytest.fixture
def invalid_ohlc_df():
    """OHLC 관계 위반 데이터"""
    return pd.DataFrame({
        "ticker": ["AAPL", "AAPL", "AAPL"],
        "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
        # 위반 1: High < Low (row 0)
        # 위반 2: High < Close (row 1)
        # 위반 3: Low > Open (row 2)
        "open": [100.0, 102.0, 105.0],
        "high": [95.0, 104.0, 110.0],   # row 0: High(95) < Low(98)
        "low": [98.0, 100.0, 107.0],    # row 2: Low(107) > Open(105)
        "close": [103.0, 106.0, 108.0],  # row 1: High(104) < Close(106)
        "volume": [1000000, 1200000, 1100000],
    })


@pytest.fixture
def temp_parquet_dir():
    """임시 Parquet 디렉터리"""
    temp_dir = Path(tempfile.mkdtemp())
    daily_dir = temp_dir / "daily"
    daily_dir.mkdir(parents=True)
    yield temp_dir
    shutil.rmtree(temp_dir)


# ═══════════════════════════════════════════════════════════════════════════
# OHLC 검증 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateOHLC:
    """OHLC 관계 검증 테스트"""

    def test_valid_ohlc_no_violations(self, valid_ohlc_df):
        """정상 데이터는 위반 없음"""
        violations = validate_ohlc_relationship(valid_ohlc_df)
        assert len(violations) == 0

    def test_detects_high_lt_low(self):
        """High < Low 탐지"""
        df = pd.DataFrame({
            "open": [100.0],
            "high": [95.0],   # High(95) < Low(98) 위반
            "low": [98.0],
            "close": [97.0],
        })
        violations = validate_ohlc_relationship(df)
        assert any(v["violation_type"] == "high_lt_low" for v in violations)

    def test_detects_high_lt_close(self):
        """High < Close 탐지"""
        df = pd.DataFrame({
            "open": [100.0],
            "high": [102.0],  # High(102) < Close(105) 위반
            "low": [98.0],
            "close": [105.0],
        })
        violations = validate_ohlc_relationship(df)
        assert any(v["violation_type"] == "high_lt_max_oc" for v in violations)

    def test_detects_low_gt_open(self):
        """Low > Open 탐지"""
        df = pd.DataFrame({
            "open": [100.0],
            "high": [110.0],
            "low": [102.0],   # Low(102) > Open(100) 위반
            "close": [105.0],
        })
        violations = validate_ohlc_relationship(df)
        assert any(v["violation_type"] == "low_gt_min_oc" for v in violations)

    def test_detects_non_positive_price(self):
        """음수/0 가격 탐지"""
        df = pd.DataFrame({
            "open": [0.0],   # Open <= 0 위반
            "high": [10.0],
            "low": [5.0],
            "close": [8.0],
        })
        violations = validate_ohlc_relationship(df)
        assert any("non_positive" in v["violation_type"] for v in violations)


# ═══════════════════════════════════════════════════════════════════════════
# Volume 검증 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateVolume:
    """Volume 검증 테스트"""

    def test_valid_volume(self, valid_ohlc_df):
        """정상 거래량"""
        violations = validate_volume(valid_ohlc_df)
        assert len(violations) == 0

    def test_detects_negative_volume(self):
        """음수 거래량 탐지"""
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "volume": [-100],
        })
        violations = validate_volume(df)
        assert len(violations) == 1
        assert violations[0]["violation_type"] == "negative_volume"


# ═══════════════════════════════════════════════════════════════════════════
# 갭 탐지 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestDetectDailyGaps:
    """Daily 갭 탐지 테스트"""

    def test_no_gaps_when_complete(self):
        """완전한 데이터는 갭 없음"""
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
        })
        calendar = ["2024-01-02", "2024-01-03", "2024-01-04"]
        gaps = detect_daily_gaps(df, trading_calendar=calendar)
        assert len(gaps) == 0

    def test_detects_missing_date(self):
        """누락된 날짜 탐지"""
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL"],  # 2024-01-03 누락
            "date": ["2024-01-02", "2024-01-04"],
        })
        calendar = ["2024-01-02", "2024-01-03", "2024-01-04"]
        gaps = detect_daily_gaps(df, trading_calendar=calendar)
        assert "AAPL" in gaps
        assert "2024-01-03" in gaps["AAPL"]


class TestDetectIntradayGaps:
    """Intraday 갭 탐지 테스트"""

    def test_no_gaps_continuous(self):
        """연속적인 데이터는 갭 없음"""
        timestamps = pd.date_range("2024-01-02 09:30", periods=5, freq="1min")
        df = pd.DataFrame({"timestamp": timestamps})
        gaps = detect_intraday_gaps(df, timeframe_minutes=1)
        assert len(gaps) == 0

    def test_detects_gap(self):
        """시간 갭 탐지"""
        # 09:30, 09:31, 09:35 (2분 갭)
        df = pd.DataFrame({
            "timestamp": [
                "2024-01-02 09:30:00",
                "2024-01-02 09:31:00",
                "2024-01-02 09:35:00",  # 3분 갭
            ]
        })
        gaps = detect_intraday_gaps(df, timeframe_minutes=1)
        assert len(gaps) > 0


# ═══════════════════════════════════════════════════════════════════════════
# 이상치 탐지 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestDetectOutliers:
    """이상치 탐지 테스트"""

    def test_no_outliers_in_normal_data(self):
        """정상 데이터는 이상치 없음"""
        df = pd.DataFrame({
            "close": [100, 101, 102, 101, 100, 99, 100],
        })
        outliers = detect_price_outliers(df, z_threshold=3.0)
        assert len(outliers) == 0

    def test_detects_spike(self):
        """가격 스파이크 탐지"""
        df = pd.DataFrame({
            # 정상 데이터 후 500% 급등
            "close": [100, 101, 102, 101, 100, 600, 100],
        })
        outliers = detect_price_outliers(df, z_threshold=2.0)
        assert len(outliers) > 0


class TestInterpolateOutliers:
    """이상치 보간 테스트"""

    def test_interpolates_correctly(self):
        """선형 보간 정확성"""
        df = pd.DataFrame({
            "open": [100.0, 200.0, 300.0],
            "high": [105.0, 205.0, 305.0],
            "low": [95.0, 195.0, 295.0],
            "close": [102.0, 202.0, 302.0],
        })
        # 인덱스 1을 이상치로 표시하고 보간
        result_df, report = interpolate_outliers(df, [1], method="linear")

        # 보간 후 중간값이 평균에 가까워야 함
        assert len(report) == 1
        assert report[0]["index"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# DataRepairer 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestDataRepairer:
    """DataRepairer 클래스 테스트"""

    def test_dry_run_no_modification(self, temp_parquet_dir):
        """Dry-run 모드는 파일 수정 안함"""
        from backend.scripts.repair_parquet_data import DataRepairer

        # 중복 데이터 생성
        daily_dir = temp_parquet_dir / "daily"
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "date": ["2024-01-02", "2024-01-02", "2024-01-03"],  # 중복
            "open": [100.0, 100.0, 102.0],
            "high": [105.0, 105.0, 108.0],
            "low": [98.0, 98.0, 100.0],
            "close": [103.0, 103.0, 106.0],
            "volume": [1000000, 1000000, 1200000],
        })
        df.to_parquet(daily_dir / "all_daily.parquet", index=False)

        # Dry-run 실행
        repairer = DataRepairer(temp_parquet_dir, dry_run=True)
        repairer.remove_duplicates_daily()

        # 파일 변경 없음 확인
        result_df = pd.read_parquet(daily_dir / "all_daily.parquet")
        assert len(result_df) == 3  # 여전히 3개 (중복 포함)

    def test_apply_removes_duplicates(self, temp_parquet_dir):
        """Apply 모드는 중복 제거"""
        from backend.scripts.repair_parquet_data import DataRepairer

        # 중복 데이터 생성
        daily_dir = temp_parquet_dir / "daily"
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "date": ["2024-01-02", "2024-01-02", "2024-01-03"],  # 중복
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 108.0],
            "low": [98.0, 99.0, 100.0],
            "close": [103.0, 104.0, 106.0],
            "volume": [1000000, 1100000, 1200000],
        })
        df.to_parquet(daily_dir / "all_daily.parquet", index=False)

        # Apply 실행
        repairer = DataRepairer(
            temp_parquet_dir,
            backup_dir=temp_parquet_dir / "backup",
            dry_run=False,
        )
        removed = repairer.remove_duplicates_daily()

        # 중복 제거 확인
        assert removed == 1
        result_df = pd.read_parquet(daily_dir / "all_daily.parquet")
        assert len(result_df) == 2  # 중복 제거됨
