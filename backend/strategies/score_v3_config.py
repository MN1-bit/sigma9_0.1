# ============================================================================
# Score V3 Configuration
# ============================================================================
# 📌 이 파일의 역할:
#   - Score V3 "Pinpoint" Algorithm 설정 상수
#   - V3 전용 가중치, 임계값, 부스트/페널티 파라미터
#
# 📖 참조: docs/strategy/Score_v3.md
# ============================================================================

from dataclasses import dataclass
from typing import Dict

# ═══════════════════════════════════════════════════════════════════════════
# V3 가중치 (재조정됨)
# ═══════════════════════════════════════════════════════════════════════════

V3_WEIGHTS: Dict[str, float] = {
    "tight_range": 0.30,  # VCP 패턴 (30%) - 유지
    "obv_divergence": 0.35,  # 스마트 머니 (35%) - 유지
    "accumulation_bar": 0.20,  # 매집 완료 (20%) - 25% → 20% (후행적)
    "volume_dryout": 0.15,  # 준비 단계 (15%) - 10% → 15% (OBV 다이버전스 보완)
}

# ═══════════════════════════════════════════════════════════════════════════
# Z-Score Sigmoid 파라미터
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ZScoreSigmoidConfig:
    """Z-Score Sigmoid 변환 설정"""

    lookback_days: int = 60  # Z-Score 계산용 히스토리 일수
    sigmoid_k: float = 1.0  # Sigmoid 기울기 (k)
    sigmoid_x0: float = 0.0  # Sigmoid 중심점 (x₀)


ZSCORE_SIGMOID = ZScoreSigmoidConfig()

# ═══════════════════════════════════════════════════════════════════════════
# Signal Modifier 설정 (Boost + Penalty 통합)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SignalModifierConfig:
    """
    Dynamic Signal Modifier 설정 (V3.2 가산 보너스 방식)

    V3.2 변경: 곱셈 부스트 → 가산 보너스
    - harmony_bonus = B * max(0, min_intensity - threshold)
    - 모든 신호가 강할수록 보너스 증가 (최대 약 8점)

    약한 신호 (< weak_threshold) 개수에 따라 페널티
    - 1개 약함 → mild_penalty
    - 2개+ 약함 → severe_penalty
    - 그 외 → 1.0 (중립)
    """

    weak_threshold: float = 0.2  # 약한 신호 기준
    strong_threshold: float = 0.6  # 강한 신호 기준

    # V3.2: 가산 보너스 설정
    harmony_bonus_scale: float = 20.0  # B: 최대 약 8점 추가 (20 * 0.4 = 8)
    bonus_threshold: float = 0.6  # 최소 min_intensity 임계값

    # Deprecated: V3.1 곱셈 방식 (하위 호환용)
    boost_multiplier: float = 1.30  # (사용 안 함)
    mild_penalty: float = 1.0  # 1개 약할 때 (임시 무력화)
    severe_penalty: float = 1.0  # 2개+ 약할 때 (임시 무력화)


SIGNAL_MODIFIER_CONFIG = SignalModifierConfig()

# 하위 호환성 유지 (기존 코드 참조용)
BOOST_CONFIG = None  # Deprecated: SignalModifierConfig 사용
SIGNAL_PENALTY_CONFIG = None  # Deprecated: SignalModifierConfig 사용

# ═══════════════════════════════════════════════════════════════════════════
# VWAP 설정
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class VWAPConfig:
    """
    VWAP (Volume Weighted Average Price) 설정

    Massive.com API에서 직접 VWAP 수신 (자체 계산 불필요)
    - WebSocket AM 채널: 분봉 VWAP (필드: 'a')
    - REST Daily Bars: 일봉 VWAP (필드: 'vw')
    """

    source: str = "massive_api"  # VWAP 소스 (massive_api | calculated)
    lookback_days: int = 5  # VWAP 이격도 계산 기간


VWAP_CONFIG = VWAPConfig()

# ═══════════════════════════════════════════════════════════════════════════
# Support Check 설정 (하방 경직성)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SupportConfig:
    """
    Volume Dryout 하방 경직성 체크 설정 (V3.2 연속 페널티)

    거래량 고갈 시 가격 지지 여부 확인
    - Price Location: (종가 - 저가) / (고가 - 저가)

    V3.2 변경: 불연속 드랍 → Sigmoid 연속 페널티
    - support_dist = (close - support) / atr
    - penalty = 1 / (1 + exp(-k * support_dist))
    """

    min_price_location: float = 0.4  # 종가가 레인지의 40% 이상에 있어야 함
    penalty_steepness: float = 3.0  # V3.2: Sigmoid k 값


SUPPORT_CONFIG = SupportConfig()

# ═══════════════════════════════════════════════════════════════════════════
# Refresh Rate 설정
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class RefreshConfig:
    """Score V3 재계산 간격 설정"""

    interval_seconds: int = 60  # 1분 (V2와 동일)
    max_concurrent_tickers: int = 50  # 동시 계산 제한


REFRESH_CONFIG = RefreshConfig()

# ═══════════════════════════════════════════════════════════════════════════
# Accumulation Bar V3.1 설정
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class AccumBarConfig:
    """
    Accumulation Bar V3.1 설정

    Base 0.5 + 가감점 구조:
    - 양봉 비율, 조용한 날 비율 → 캔들 패턴 분석
    - Body Ratio, 거래량 Median → 이상치 내성

    참조: docs/Plan/bugfix/03-003_accumbar_v31_redesign.md
    """

    base_score: float = 0.5  # 중립 기준점
    accum_period_days: int = 10  # 매집 기간 (일)

    # 가감점 임계값
    bullish_threshold_high: float = 0.7  # 70% 이상 양봉 → 보너스
    bullish_threshold_low: float = 0.3  # 30% 이하 양봉 → 페널티
    quiet_threshold_high: float = 0.7  # 70% 이상 조용 → 보너스
    quiet_threshold_low: float = 0.3  # 30% 미만 조용 → 페널티
    quiet_range_pct: float = 0.03  # 조용한 날 기준 (3% 변동 미만)
    body_ratio_high: float = 0.6  # 60% 이상 실체 → 보너스
    body_ratio_low: float = 0.3  # 30% 미만 실체 → 페널티
    volume_ratio_high: float = 1.3  # 130% 이상 → 보너스
    volume_ratio_low: float = 0.7  # 70% 미만 → 페널티

    # 가감점 값
    adj_bullish: float = 0.15  # 양봉 비율 보너스/페널티
    adj_quiet: float = 0.15  # 조용한 날 보너스/페널티
    adj_body: float = 0.10  # Body Ratio 보너스/페널티
    adj_volume: float = 0.10  # 거래량 보너스/페널티


ACCUMBAR_CONFIG = AccumBarConfig()

# ═══════════════════════════════════════════════════════════════════════════
# V3.2 Phase 3: Percentile 정규화 설정
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PercentileConfig:
    """
    V3.2 Percentile 기반 정규화 설정

    Z-Score 대신 percentile rank 사용으로 레짐 변화에 강건
    - percentile = (현재값보다 작은 값 개수) / 전체 개수
    - intensity = 1 - percentile (낮을수록 높은 강도)
    """

    use_percentile: bool = True  # True: percentile, False: Z-Score
    min_samples: int = 10  # 최소 샘플 수


PERCENTILE_CONFIG = PercentileConfig()

# ═══════════════════════════════════════════════════════════════════════════
# V3.2 Phase 3: RedundancyPenalty 설정
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class RedundancyPenaltyConfig:
    """
    V3.2 RedundancyPenalty 설정

    압축(TR)만 있고 흡수(OBV/Absorption) 없으면 감점
    - "죽은 압축" 패턴 필터링
    - 거짓 양성 감소
    """

    enabled: bool = True
    tr_threshold: float = 0.6  # TR이 이 이상이면 압축 상태
    obv_threshold: float = 0.4  # OBV가 이 이하면 흡수 없음
    penalty_multiplier: float = 0.7  # 0.7x 페널티


REDUNDANCY_PENALTY_CONFIG = RedundancyPenaltyConfig()
