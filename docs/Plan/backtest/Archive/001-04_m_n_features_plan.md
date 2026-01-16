# R-4 급등 탐지 2-Tier 파이프라인

> **작성일**: 2026-01-15 | **예상**: 8h  
> **선행**: R-3 완료 (control_groups.csv 확보)

---

## 1. 목표

급등주 탐지를 위한 **2-Tier 시스템** 구축:

| Tier | 용도 | 시점 | 적용 |
|------|------|------|------|
| **D-1** | 유니버스 스캐너 | 전일 종가 기준 | 장 전 워치리스트 생성 |
| **M-n** | 실시간 경보기 | 장중 분봉 기준 | 급등 직전 알림 |

```
[D-1 스캐너] → 후보군 100~200개 → [M-n 경보기] → 실시간 알림
```

---

## 1.1 레이어 체크

- [x] 레이어 규칙 위반 없음 (`scripts/` 독립 스크립트, backend 미연동)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: **아니오** (독립 분석 스크립트)

---

## 1.2 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| `pandas-ta` | PyPI | ✅ 부분 채택 | ATR, MA, RSI 계산 활용 |
| `ta-lib` | PyPI | ❌ 미채택 | C 의존성 설치 복잡 |
| `finplot` | PyPI | ❌ 해당없음 | 시각화 전용, 피처 추출 불가 |
| 직접 구현 | - | ✅ | z-score, 가속도 등 커스텀 로직 |

---

## 2. Tier 1: D-1 유니버스 스캐너

### 2.1 목적
- 장 시작 전, **급등 가능성 높은 종목** 사전 필터링
- 전체 유니버스(~10,000) → 워치리스트(100~200개)

### 2.2 D-1 시점 정의
```
D-1 = 전일 종가 시점 (4:00 PM ET 기준)
```

### 2.3 D-1 피처 (일봉 기반)
| 피처 | 설명 |
|------|------|
| `rvol_20d` | 20일 평균 대비 당일 거래량 |
| `price_vs_20ma` | 20일 이평선 대비 종가 위치 |
| `price_vs_52w_high` | 52주 고점 대비 거리 % |
| `atr_pct` | ATR / 종가 (변동성) |
| `volume_trend_5d` | 5일 거래량 추세 (상승/하락) |
| `gap_history` | 최근 30일 갭 발생 횟수 |
| `sector_momentum` | 섹터 상대 강도 |

### 2.4 출력
- `scripts/d1_features.parquet`
- 레코드: Daygainer 1,284 + Control 4,205 = ~5,500건

---

## 3. Tier 2: M-n 실시간 경보기

### 3.1 목적
- 장중 **급등 직전 이상 징후** 실시간 감지
- D-1 워치리스트 종목 모니터링 → 알림

### 3.2 T0 시점 정의 (병렬 실험)

> **설계 원칙**: T0는 **Price 기반만 사용** (RVOL 등은 피처로 보존)  
> 이유: "RVOL 상승 + 가격 미변동" 패턴을 피처로 분석하기 위함

#### 방식 A: Threshold T0
```
T0_threshold = 전일 종가 대비 +6% 최초 돌파 시점
```
- 장점: 단순, 직관적
- 단점: 느린 상승 종목에서 급등 중반에 T0 찍힘

#### 방식 B: Acceleration T0
```python
rolling_return = close.pct_change(10) / 10  # 10분 평균 상승률
acceleration = rolling_return.diff()         # 가속도
T0_accel = (acceleration > 0.002).idxmax()   # 첫 가속 시점
```
- 장점: 느린 상승/빠른 펌프 모두 급등 시작점 포착
- 단점: threshold 튜닝 필요

#### Control 종목 T0
- 방식 A: +6% 돌파 시점, 없으면 **장중 최고가 도달 시점**
- 방식 B: 첫 가속 시점, 없으면 **장중 최고가 도달 시점**

#### 분석 윈도우
```
분석 윈도우 = T0 - n분 ~ T0 - 1분 (n = 15, 30, 60, 120)
```

> **중요**: 프리마켓(4:00-9:30 AM) 및 애프터마켓(4:00-8:00 PM) 데이터 **필수 포함**

### 3.3 프리마켓/애프터마켓 데이터
| 피처 | 설명 |
|------|------|
| `premarket_volume` | 프리마켓 누적 거래량 |
| `premarket_change` | 프리마켓 가격 변화율 (전일 종가 대비) |
| `premarket_high` | 프리마켓 고점 |
| `afterhours_activity` | 전일 애프터마켓 활동 여부 |
| `gap_from_close` | 전일 종가 대비 프리마켓 갭 % |

### 3.4 M-n 피처 (분봉 기반 Anomaly)
| 피처 | 설명 |
|------|------|
| `volume_zscore_max` | 윈도우 내 거래량 z-score 최대값 |
| `volume_acceleration` | 거래량 가속 패턴 (후반 vs 초반) |
| `rvol_spike_count` | RVOL ≥ 1.5x 분봉 개수 |
| `price_momentum` | 윈도우 내 가격 변화율 |
| `unusual_bar_count` | 비정상 패턴 분봉 개수 |
| `first_anomaly_timing` | 첫 이상 신호 발생 시점 (T0-몇분) |
| `bid_ask_spread_trend` | 스프레드 변화 추세 |

### 3.5 출력
- `scripts/m_n_features.parquet`
- 레코드: 분봉 데이터 있는 종목만 (~3,000건 예상)

---

## 4. 실행 단계

### Phase 0: 데이터 커버리지 확인 (Step 0)

**Step 0**: 분봉 데이터 커버리지 검증 및 다운로드
```
1. control_groups.csv 로드 (Daygainer + Control 티커/날짜)
2. 각 (ticker, date)별 분봉 parquet 존재 여부 확인
3. 누락 데이터 리스트 생성
4. 누락 시 → Massive API로 분봉 다운로드
   - GET /v2/aggs/ticker/{ticker}/range/1/minute/{date}/{date}
   - include_premarket=true, include_afterhours=true
5. 다운로드 결과 저장 (기존 parquet 구조에 맞춰)
6. 커버리지 리포트 출력
```

> **주의**: 프리마켓(4:00 AM~) 데이터 포함 여부 반드시 확인

---

### Phase A: D-1 스캐너 (Step 1-2)

**Step 1**: 일봉 데이터 로드 및 D-1 피처 계산
```
1. all_daily.parquet 로드
2. 각 Daygainer/Control의 D-1 시점 피처 계산
3. 결측값 처리
```

**Step 2**: D-1 피처 출력
```
1. d1_features.parquet 저장
2. 기초 통계 출력
```

---

### Phase B: M-n 경보기 (Step 3-5)

**Step 3**: T0 탐지 (병렬 방식)
```
1. 프리마켓 + 정규장 분봉 로드
2. 방식 A: +6% 돌파 최초 시점 = T0_threshold
3. 방식 B: 첫 가속 시점 = T0_accel
4. T0 없으면 → 장중 고점 시점 fallback
```

**Step 4**: 가변 윈도우 피처 계산 (15/30/60/120분)
```
1. T0 - n분 ~ T0 - 1분 분봉 추출 (n = 15, 30, 60, 120)
2. 각 윈도우별 Anomaly 피처 계산
3. 프리마켓 데이터 포함 (4:00 AM부터)
4. 윈도우 부족 시 → 가용 분봉만 사용
```

**Step 5**: M-n 피처 출력
```
1. m_n_features.parquet 저장
2. 기초 통계 및 커버리지 출력
```

---

## 5. 변경/생성 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `scripts/check_minute_coverage.py` | [NEW] | ~100 |
| `scripts/build_d1_features.py` | [NEW] | ~150 |
| `scripts/build_m_n_features.py` | [NEW] | ~250 |
| `scripts/d1_features.parquet` | [NEW] 출력 | - |
| `scripts/m_n_features.parquet` | [NEW] 출력 | - |

---

## 6. 검증

### 6.1 실행 명령
```bash
python scripts/check_minute_coverage.py  # Step 0: 커버리지 확인
python scripts/build_d1_features.py      # D-1 피처
python scripts/build_m_n_features.py     # M-n 피처
```

### 6.2 검증 항목
| 검증 항목 | 기준 |
|----------|------|
| 분봉 커버리지 | ≥ 80% (다운로드 후) |
| 프리마켓 데이터 | 존재 여부 리포트 |
| 결측값 비율 | < 20% |
| 라벨 분포 | daygainer:control ≈ 1:4 |
| 피처 상관관계 | 초기 EDA 수행 |

### 6.3 코드 품질 (IMP-planning §2)
- [ ] lint-imports 통과
- [ ] pydeps --show-cycles 통과

---

## 7. 결정된 사항

| 항목 | 결정 |
|------|------|
| **T0 정의** | 병렬 실험: 방식 A (+6%) vs 방식 B (가속 시점) |
| **T0 설계 원칙** | Price 기반만 사용 (RVOL 등 피처 보존) |
| **M-n 윈도우** | 가변 (15/30/60/120분) |
| **프리마켓/애프터마켓** | ✅ 필수 포함 |

---

## 8. 다음 단계 (R-5)

- D-1 + M-n 피처셋 결합
- EDA: Daygainer vs Control 차별화 지표 탐색
- ML 모델링 준비

