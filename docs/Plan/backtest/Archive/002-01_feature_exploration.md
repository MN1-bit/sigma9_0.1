# 002-01: 전체 피처 카탈로그

> **문서 번호**: 002-01  
> **작성일**: 2026-01-15  
> **목표**: Daygainer vs Control 차별화를 위한 전체 피처 목록  
> **선행 문서**: [_overview.md](./_overview.md), [_detection.md](./_detection.md), Rheograph overview

---

## 1. 개요

### 1.1 피처 분류 체계

| 분류 | 설명 | 소스 |
|------|------|------|
| **Seismograph** | 매집 탐지 전략 시그널 | `backend/strategies/seismograph/signals/` |
| **Rheograph** | 유동성 우선성 전략 지표 | `docs/context/strategy/Rheograph/overview.md` |
| **추가사항** | 백테스트 연구용 확장 피처 | 문헌/도메인 지식 |

### 1.2 현재 구현 상태

| 구분 | 정의됨 | 구현됨 | Gap |
|------|--------|--------|-----|
| Seismograph | 12개 | 4개 | 8개 |
| Rheograph | 30+개 | 0개 | 30+개 |
| 추가사항 | 15개 | 0개 | 15개 |

---

## 2. Seismograph 피처 (매집 탐지)

> 소스: `backend/strategies/seismograph/signals/`

### 2.1 Accumulation Bar (매집봉)

| 피처 | 설명 | 계산 | 구현 |
|------|------|------|------|
| `accum_bar_intensity` | 매집봉 강도 (V2) | 가격변동 <2.5% AND volume >2x avg | ✅ |
| `accum_bar_intensity_v3` | 매집봉 강도 (V3) | 양봉비율 + 방향성 조용함 | ✅ |
| `volume_spike_ratio` | 거래량 스파이크 배수 | current_vol / avg_vol | ✅ |
| `price_change_pct` | 봉 가격 변동률 | abs(C-O)/O | ✅ |
| `bullish_ratio_10d` | 10일 양봉 비율 | green_days / 10 | 🔲 추출 필요 |
| `quiet_days_ratio` | 조용한 날 비율 (레인지 <2%) | quiet_days / period | 🔲 추출 필요 |

### 2.2 Tight Range (변동성 수축)

| 피처 | 설명 | 계산 | 구현 |
|------|------|------|------|
| `tight_range_intensity` | 변동성 수축 강도 (V2) | ATR_5 / ATR_20 비율 역수 | ✅ |
| `tight_range_intensity_v3` | 변동성 수축 강도 (V3) | ATR percentile (60일) | ✅ |
| `atr_5d` | 5일 ATR | 5일 True Range 평균 | 🔲 추출 필요 |
| `atr_20d` | 20일 ATR | 20일 True Range 평균 | 🔲 추출 필요 |
| `atr_percentile_60d` | ATR 60일 백분위 | 현재 ATR의 상대 위치 | 🔲 추출 필요 |

### 2.3 OBV Divergence (가격-거래량 괴리)

| 피처 | 설명 | 계산 | 구현 |
|------|------|------|------|
| `obv_divergence_intensity` | OBV 다이버전스 강도 (V2) | price↓ + OBV↑ | ✅ |
| `absorption_intensity_v3` | 흡수 강도 (V3) | Signed Volume vs Price Reaction | ✅ |
| `obv_20d` | 20일 OBV | Σ(sign(return) × volume) | 🔲 추출 필요 |
| `obv_slope` | OBV 기울기 | OBV 선형회귀 기울기 | 🔲 추출 필요 |
| `signed_volume_10d` | 10일 Signed Volume | Σ(sign × vol) | 🔲 추출 필요 |
| `price_reaction_10d` | 10일 Price Reaction | Σ(abs(return)) | 🔲 추출 필요 |

### 2.4 Volume Dryout (거래량 마름)

| 피처 | 설명 | 계산 | 구현 |
|------|------|------|------|
| `volume_dryout_intensity` | 거래량 마름 강도 (V2) | (1 - vol_3d/vol_20d) / threshold | ✅ |
| `volume_dryout_intensity_v3` | 거래량 마름 강도 (V3) | V2 × Support Penalty | ✅ |
| `vol_ratio_3d_20d` | 3일/20일 거래량 비율 | avg_3d / avg_20d | 🔲 추출 필요 |
| `support_factor` | 가격 지지 위치 | (close - low_20d) / range_20d | 🔲 추출 필요 |
| `is_volume_dryout` | 마름 여부 (bool) | ratio < 0.4 | 🔲 추출 필요 |

---

## 3. Rheograph 피처 (유동성 우선성)

> 소스: `docs/context/strategy/Rheograph/overview.md`

### 3.1 Stage 1: Universe Filtering (스캐닝)

| 피처 | 설명 | 계산 | 구현 |
|------|------|------|------|
| `dollar_float` | 달러 플로트 | Price × Float Shares | 🔲 |
| `rvol_realtime` | 실시간 RVOL (5분) | 5분봉 vol / 20일 5분 평균 | 🔲 |
| `rvol_cumulative` | 누적 RVOL | 당일 누적 / 20일 평균 | ⚠️ 일봉 근사 |
| `gap_pct` | 갭 비율 | (Open - PrevClose) / PrevClose | 🔲 |
| `catalyst_tier` | 촉매 등급 (1-3) | 뉴스 분류 | 🔲 |
| `has_atm_offering` | ATM 오퍼링 여부 | SEC 공시 확인 | 🔲 |
| `short_interest_pct` | 공매도 비율 | SI / Float | 🔲 |
| `is_frontside` | Frontside 여부 | HOD 근접 | 🔲 |
| `half_life_est` | 촉매 효력 추정 시간 | 촉매 분류 기반 | 🔲 |

### 3.2 Stage 2: Entry Timing (진입)

| 피처 | 설명 | 계산 | 구현 |
|------|------|------|------|
| `spread_bps` | 스프레드 (bps) | (ask - bid) / mid × 10000 | 🔲 |
| `price_vs_vwap` | VWAP 대비 가격 | (price - VWAP) / VWAP | 🔲 |
| `is_above_vwap` | VWAP 상방 여부 | price > VWAP | 🔲 |
| `hod_distance_pct` | HOD 까지 거리 | (HOD - price) / price | 🔲 |
| `pmh` | 프리마켓 고점 | max(premarket high) | 🔲 |
| `orb_high` | ORB 상단 | 첫 5분/15분 고점 | 🔲 |
| `orb_low` | ORB 하단 | 첫 5분/15분 저점 | 🔲 |

### 3.3 Layer 1: 원시 지표

| 피처 | 설명 | 계산 | 구현 |
|------|------|------|------|
| `effective_spread` | 유효 스프레드 | 2 × |price - mid| | 🔲 |
| `bid_volume` | 매수 체결량 | Lee-Ready 분류 | 🔲 |
| `ask_volume` | 매도 체결량 | Lee-Ready 분류 | 🔲 |
| `vwap` | VWAP | Σ(price × vol) / Σ(vol) | 🔲 |

### 3.4 Layer 2: 파생 지표

| 피처 | 설명 | 계산 | 구현 |
|------|------|------|------|
| `tape_accel` | 체결 가속도 | d(velocity)/dt | 🔲 |
| `trade_imbalance` | 거래 불균형 | (bid - ask) / total | 🔲 |
| `absorption_ratio` | 흡수 비율 | Tick Proxy (MVP) | 🔲 |
| `rotation_velocity` | Float 회전 속도 | d(cumVol/Float)/dt | 🔲 |
| `rotation_accel` | 회전 가속도 | d(velocity)/dt | 🔲 |

### 3.5 Layer 3: 마이크로 상태

| 피처 | 설명 | 조건 | 구현 |
|------|------|------|------|
| `micro_state` | 마이크로 상태 | enum: ABSORPTION/VACUUM/DISTRIBUTION/EXHAUSTION | 🔲 |
| `is_absorption` | 흡수 상태 | 대량체결 + 가격유지 | 🔲 |
| `is_vacuum` | 진공 상태 | tape_accel↑ + ask↓ | 🔲 |
| `is_distribution` | 분배 상태 | imbalance < -0.3 | 🔲 |
| `is_exhaustion` | 소진 상태 | tape_accel↓ + spread↑ | 🔲 |

### 3.6 Layer 4: 매크로 상태

| 피처 | 설명 | 조건 | 구현 |
|------|------|------|------|
| `macro_regime` | 매크로 레짐 | 🟢Green / 🟡Yellow / 🔴Red | 🔲 |
| `rotation_phase` | 로테이션 위상 | FUEL / TRANSITION / FATIGUE | 🔲 |

### 3.7 붕괴 경보

| 피처 | 설명 | 조건 | 구현 |
|------|------|------|------|
| `collapse_warning` | 붕괴 경보 | rotation_accel < 0 AND spread↑ | 🔲 |
| `is_dead_zone` | 데드존 시간대 | 11:30-14:00 | 🔲 |

---

## 4. 추가사항 (연구 확장)

> 문헌 및 도메인 지식 기반 추가 피처

### 4.1 캔들 구조 피처

| 피처 | 설명 | 계산 | 우선순위 |
|------|------|------|----------|
| `low_to_close_ratio` | 저점-종가 위치 | (C - L) / (H - L) | ⭐⭐⭐ |
| `upper_wick_ratio` | 윗꼬리 비율 | (H - max(O,C)) / (H - L) | ⭐⭐ |
| `lower_wick_ratio` | 아랫꼬리 비율 | (min(O,C) - L) / (H - L) | ⭐⭐ |
| `body_ratio` | 몸통 비율 | abs(O - C) / (H - L) | ⭐⭐ |
| `consecutive_green` | 연속 양봉 일수 | count | ⭐ |
| `consecutive_red` | 연속 음봉 일수 | count | ⭐ |

### 4.2 이동평균 피처

| 피처 | 설명 | 계산 | 우선순위 |
|------|------|------|----------|
| `price_vs_5ma` | 5일 이평 대비 | (C - MA5) / MA5 | ⭐⭐ |
| `price_vs_10ma` | 10일 이평 대비 | (C - MA10) / MA10 | ⭐⭐ |
| `price_vs_50ma` | 50일 이평 대비 | (C - MA50) / MA50 | ⭐⭐ |
| `ma_5_10_cross` | 5/10 골든크로스 | MA5 > MA10 | ⭐ |
| `ma_slope_5d` | 5일선 기울기 | 선형회귀 기울기 | ⭐ |

### 4.3 모멘텀 피처

| 피처 | 설명 | 계산 | 우선순위 |
|------|------|------|----------|
| `rsi_14` | 14일 RSI | 표준 RSI | ⭐⭐ |
| `rsi_5` | 5일 RSI | 단기 RSI | ⭐⭐ |
| `roc_5` | 5일 ROC | (C - C_5) / C_5 | ⭐⭐ |
| `roc_10` | 10일 ROC | (C - C_10) / C_10 | ⭐ |
| `macd_histogram` | MACD 히스토그램 | MACD - Signal | ⭐ |
| `macd_crossover` | MACD 크로스오버 | MACD > Signal 전환 | ⭐ |

### 4.4 변동성 피처

| 피처 | 설명 | 계산 | 우선순위 |
|------|------|------|----------|
| `atr_pct` | ATR 비율 | ATR / Close | ⭐⭐ |
| `bb_width` | 볼린저밴드 폭 | (Upper - Lower) / MA | ⭐ |
| `bb_position` | BB 내 위치 | (C - Lower) / Width | ⭐ |
| `keltner_squeeze` | 켈트너 스퀴즈 | BB inside Keltner | ⭐ |

### 4.5 거래량 피처

| 피처 | 설명 | 계산 | 우선순위 |
|------|------|------|----------|
| `volume_trend_5d` | 5일 거래량 추세 | 선형회귀 기울기 | ⭐⭐ |
| `volume_trend_10d` | 10일 거래량 추세 | 선형회귀 기울기 | ⭐ |
| `mfi_14` | 14일 MFI | Money Flow Index | ⭐ |
| `cmf_20` | 20일 CMF | Chaikin Money Flow | ⭐ |
| `ad_line` | A/D Line | Accumulation/Distribution | ⭐ |

### 4.6 가격 레벨 피처

| 피처 | 설명 | 계산 | 우선순위 |
|------|------|------|----------|
| `price_vs_52w_high` | 52주 고점 대비 | (C - 52wH) / 52wH | ⭐⭐ |
| `price_vs_52w_low` | 52주 저점 대비 | (C - 52wL) / 52wL | ⭐ |
| `price_vs_20d_high` | 20일 고점 대비 | (C - 20dH) / 20dH | ⭐⭐ |
| `price_vs_20d_low` | 20일 저점 대비 | (C - 20dL) / 20dL | ⭐ |
| `distance_to_resistance` | 저항선까지 거리 | 직전 고점 기준 | ⭐ |

### 4.7 분봉 특화 피처 (M-n)

| 피처 | 설명 | 계산 | 우선순위 |
|------|------|------|----------|
| `rvol_max_intraday` | 당일 최대 분봉 RVOL | max(minute_rvol) | ⭐⭐⭐ |
| `rvol_spike_time` | 첫 RVOL 2x 돌파 시간 | minutes since open | ⭐⭐ |
| `volume_profile_skew` | 거래량 시간 분포 편향 | first_half / second_half | ⭐⭐ |
| `gap_fill_pct` | 갭 메꿈 비율 | filled / gap_size | ⭐ |
| `first_5min_range` | 첫 5분 레인지 | (H5 - L5) / O | ⭐⭐ |
| `first_15min_direction` | 첫 15분 방향 | close_15m > open ? 1 : -1 | ⭐ |

---

## 5. 구현 우선순위

### Phase 1: D-1 기반 즉시 구현 (일봉)

| 피처 | 소스 | 예상 효과 |
|------|------|----------|
| `low_to_close_ratio` | 일봉 | ⭐⭐⭐ |
| `tight_range_intensity_v3` | Seismograph | ⭐⭐⭐ |
| `volume_dryout_intensity_v3` | Seismograph | ⭐⭐⭐ |
| `absorption_intensity_v3` | Seismograph | ⭐⭐⭐ |
| `accum_bar_intensity_v3` | Seismograph | ⭐⭐ |
| `atr_percentile_60d` | 추가 | ⭐⭐ |
| `rsi_5` | 추가 | ⭐⭐ |
| `price_vs_20d_high` | 추가 | ⭐⭐ |

### Phase 2: M-n 기반 구현 (분봉 다운로드 후)

| 피처 | 소스 | 예상 효과 |
|------|------|----------|
| `rvol_max_intraday` | Rheograph | ⭐⭐⭐ |
| `rvol_spike_time` | Rheograph | ⭐⭐ |
| `first_5min_range` | 추가 | ⭐⭐ |
| `volume_profile_skew` | 추가 | ⭐⭐ |

### Phase 3: 실시간 데이터 필요 (향후)

| 피처 | 소스 | 데이터 요구 |
|------|------|------------|
| `tape_accel` | Rheograph | T&S |
| `trade_imbalance` | Rheograph | L1/L2 |
| `effective_spread` | Rheograph | Quote |
| `rotation_velocity` | Rheograph | Cumulative Vol |

---

## 6. 다음 단계

1. [ ] Phase 1 피처 구현 (`build_d1_features_v2.py`)
2. [ ] Seismograph 시그널 함수 → 피처 추출기 연결
3. [ ] 분봉 다운로드 완료 후 Phase 2 구현
4. [ ] 전체 EDA 재실행
5. [ ] ML 분류기 학습 (R-6)

---

**문서 이력**
| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| 002-01 | 2026-01-15 | 전체 피처 카탈로그 초안 |
