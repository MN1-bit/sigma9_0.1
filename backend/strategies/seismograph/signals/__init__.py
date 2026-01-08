# Signals 모듈 - 시그널 탐지 함수
# [03-001] Phase 2: 로직 분리

from .tight_range import calc_tight_range_intensity, calc_tight_range_intensity_v3
from .obv_divergence import calc_obv_divergence_intensity, calc_absorption_intensity_v3
from .accumulation_bar import calc_accumulation_bar_intensity, calc_accumulation_bar_intensity_v3
from .volume_dryout import calc_volume_dryout_intensity, calc_volume_dryout_intensity_v3

__all__ = [
    # V2
    "calc_tight_range_intensity",
    "calc_obv_divergence_intensity",
    "calc_accumulation_bar_intensity",
    "calc_volume_dryout_intensity",
    # V3
    "calc_tight_range_intensity_v3",
    "calc_absorption_intensity_v3",
    "calc_accumulation_bar_intensity_v3",
    "calc_volume_dryout_intensity_v3",
]
