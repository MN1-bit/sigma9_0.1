# signals/__init__.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/seismograph/signals/__init__.py` |
| **역할** | Signals 모듈 진입점 - V2/V3 시그널 함수 export |
| **라인 수** | 24 |
| **바이트** | 805 |

## Export 목록

| Export | 소스 | 버전 | 설명 |
|--------|------|------|------|
| `calc_tight_range_intensity` | `tight_range.py` | V2 | VCP 변동성 수축 |
| `calc_obv_divergence_intensity` | `obv_divergence.py` | V2 | OBV 다이버전스 |
| `calc_accumulation_bar_intensity` | `accumulation_bar.py` | V2 | 매집봉 |
| `calc_volume_dryout_intensity` | `volume_dryout.py` | V2 | 볼륨 드라이아웃 |
| `calc_tight_range_intensity_v3` | `tight_range.py` | V3 | Percentile 기반 |
| `calc_absorption_intensity_v3` | `obv_divergence.py` | V3 | Signed Volume 흡수 |
| `calc_accumulation_bar_intensity_v3` | `accumulation_bar.py` | V3 | Base 0.5 가감점 |
| `calc_volume_dryout_intensity_v3` | `volume_dryout.py` | V3 | Sigmoid 페널티 |

## 🔗 외부 연결

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `seismograph/strategy.py` | 시그널 강도 계산 |

## 외부 의존성
- (없음)
