# score_v3_config.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/score_v3_config.py` |
| **역할** | Score V3 "Pinpoint" Algorithm 설정 상수 및 dataclass 정의 |
| **라인 수** | 223 |
| **바이트** | 10,731 |

## 상수

### V3_WEIGHTS
> V3 가중치 (4개 신호)

| 신호 | 가중치 | 설명 |
|------|--------|------|
| `tight_range` | 0.30 | VCP 패턴 (30%) |
| `obv_divergence` | 0.35 | 스마트 머니 (35%) |
| `accumulation_bar` | 0.20 | 매집 완료 (20%) |
| `volume_dryout` | 0.15 | 준비 단계 (15%) |

## Dataclass 목록

| 클래스 | 역할 |
|--------|------|
| `ZScoreSigmoidConfig` | Z-Score Sigmoid 변환 설정 |
| `SignalModifierConfig` | Dynamic Signal Modifier (Boost + Penalty) |
| `VWAPConfig` | VWAP 설정 (Massive API 기반) |
| `SupportConfig` | Volume Dryout 하방 경직성 체크 |
| `RefreshConfig` | Score 재계산 간격 설정 |
| `AccumBarConfig` | Accumulation Bar V3.1 설정 |
| `PercentileConfig` | V3.2 Percentile 정규화 설정 |
| `RedundancyPenaltyConfig` | V3.2 RedundancyPenalty 설정 |

## 주요 설정 인스턴스

| 인스턴스 | 타입 | 설명 |
|----------|------|------|
| `ZSCORE_SIGMOID` | `ZScoreSigmoidConfig` | lookback 60일, sigmoid_k=1.0 |
| `SIGNAL_MODIFIER_CONFIG` | `SignalModifierConfig` | 가산 보너스 방식 (V3.2) |
| `VWAP_CONFIG` | `VWAPConfig` | Massive API 소스 |
| `SUPPORT_CONFIG` | `SupportConfig` | min_price_location=0.4 |
| `REFRESH_CONFIG` | `RefreshConfig` | 60초 간격, 최대 50 티커 |
| `ACCUMBAR_CONFIG` | `AccumBarConfig` | Base 0.5 + 가감점 구조 |
| `PERCENTILE_CONFIG` | `PercentileConfig` | Percentile 사용 활성화 |
| `REDUNDANCY_PENALTY_CONFIG` | `RedundancyPenaltyConfig` | 죽은 압축 패턴 필터링 |

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| (표준 라이브러리) | `dataclass`, `Dict` |

### Imported By (이 파일을 가져가는 것)
| 파일 | 사용 목적 |
|------|----------|
| `backend/strategies/seismograph/scoring/*.py` | V3 스코어링 파라미터 참조 |
| `backend/strategies/seismograph/signals/*.py` | 신호 계산 임계값 참조 |

## 버전 히스토리

| 버전 | 변경 내용 |
|------|----------|
| V3.1 | AccumBarConfig 도입 (Base 0.5 + 가감점) |
| V3.2 | 곱셈 부스트 → 가산 보너스, Percentile 정규화, RedundancyPenalty |

## 참조 문서
- `docs/strategy/Score_v3.md`
- `docs/Plan/bugfix/03-003_accumbar_v31_redesign.md`

## 외부 의존성
- (없음 - 표준 라이브러리만)
