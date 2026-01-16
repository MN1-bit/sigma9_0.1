# accumulation_bar.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/seismograph/signals/accumulation_bar.py` |
| **역할** | 매집봉 시그널 감지 - 가격 변동 작고 거래량 높은 캔들 |
| **라인 수** | 161 |
| **바이트** | 4,957 |

## 함수

### `calc_accumulation_bar_intensity(data) -> float`
> V2: Volume Spike 배수 기반 (0.0~1.0)

#### 조건
- 가격 변동 > 2.5% → 0.0 (매집봉 아님)

#### Volume Spike 강도
| 배수 | 강도 |
|------|------|
| 2x 미만 | 0.0 |
| 3x | 0.33 |
| 5x 이상 | 1.0 |

---

### `calc_accumulation_bar_intensity_v3(data, ...) -> float`
> V3.1: 시간 분리 + 이상치 내성 (Base 0.5 가감점)

#### 특징
1. Base 0.5 + 가감점 구조 (중립 기준점)
2. 과거 10일 매집 기간 분석 (Dryout와 시간 분리)
3. Median 기반 (이상치 강건)
4. Float 기반 동적 기간 계산

#### 가감점 요소
| 요소 | 조건 | 가감점 |
|------|------|--------|
| 양봉 비율 | ≥ 60% | +0.15 |
| 양봉 비율 | ≤ 40% | -0.15 |
| 조용한 날 (상단 종가) | ≥ 70% | +0.1 |
| 조용한 날 (하단 종가) | ≤ 30% | -0.05 |

## 🔗 외부 연결

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `base.py` | `get_column` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `signals/__init__.py` | export |

## 외부 의존성
- `numpy`
