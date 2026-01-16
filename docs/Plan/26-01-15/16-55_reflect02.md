# Pre‑Surge Detection (대안 B) 데이터/샘플링/룰학습 설계서 v1.0

**문서 번호**: 002‑03‑B
**작성일**: 2026‑01‑15
**전제**: antigravity 바이브코딩으로 백테스터 구현 중 / 로컬 PC(최신 하이엔드)에서 ML 학습·피처 계산·백테스트 수행
**목표**: “당일 +75% Daygainer”를 직접 맞히기보다, **Pump Attempt(시도)** → **성공/실패**로 문제를 분해하여

1. D‑1/장전 스캐너 룰, 2) 장중 경보 룰을 **해석 가능한 형태**로 도출

---

## 0. 설계 개요 (3‑Stage)

### Stage 0 — D‑1/장전: “Attempt(펌프 시도) 발생 후보” 스캐너

* **입력 시점**: D‑1 종가 기준 + (선택) D일 프리마켓 초반까지
* **출력**: 하루 Top‑N 후보(예: 200)
* **목표**: Attempt 리콜 최대화(“시도”라도 잡아두기)

### Stage 1 — 장중: “Attempt → Success(Daygainer) vs Fail(실패)” 판별

* **입력 시점**: Attempt Trigger 시점(또는 그 직전 n분)까지의 정보만
* **출력**: 성공 확률/점수 + 룰(경보)
* **목표**: FP를 줄이고, **리드타임(가능하면 T0 이전)** 확보

### Stage 2 — 경보 정책(옵션): 알림 예산/중복 방지/쿨다운

* “모델 점수 > θ”만으로는 FP 폭발 위험
* **하루 알림 예산**, **종목당 1회**, **쿨다운**, **시장 레짐별 θ** 같은 운영 정책을 명시적으로 둠

> 이 문서는 Stage 0/1을 중심으로, 이를 받쳐주는 **테이블 스키마 + 라벨/샘플링 레시피 + 룰 학습/추출(RuleFit 선택)**을 제안합니다.

---

## 1. 핵심 정의(라벨) — “포인트‑인‑타임” 준수

### 1.1 Daygainer (최종 목표 라벨)

* 거래일 D 정규장 **시가→종가 수익률 ≥ +75%**
* 거래대금(정규장) ≥ $500k
* 가격(정규장) ≥ $0.1
  → `is_daygainer = 1`

### 1.2 Pump Attempt (중간 라벨: “시도”)

**Attempt는 ‘하루에 0~여러 번’ 발생**할 수 있으나, 기본은 **가장 이른 Attempt 1회만** 사용(학습 안정/누수 감소).

Attempt Trigger(시점 `t_attempt`)는 다음을 만족하는 “이벤트”로 정의(추천 기본값, 파라미터화):

* **이상거래(볼륨) 조건**:
  `minute_rvol(t) >= RVOL_TRIG` (예: 3.0)

  * 여기서 `minute_rvol`은 “분당 기대 거래량(동일 분‑of‑day, 과거 20거래일)” 대비 비율을 권장(장초/장말 계절성 제거)
* **가격 반응 조건**(둘 중 하나):

  * (A) `ret_5m(t) >= +P_TRIG` (예: +1.5%)
  * 또는 (B) `close(t) > vwap(t)` AND `breakout_from_range` (최근 30~60분 박스 상단 돌파)

→ `has_attempt = 1`, 이벤트 테이블에 `t_attempt` 저장

### 1.3 Failed Pump (Stage 1의 음성 라벨)

Attempt가 있었던 종목‑일 중, 아래를 만족하면 `is_failed_pump=1`:

* Attempt 이후 **당일 고점(HOD_after_attempt)** 대비
* 종가 또는 특정 시점(예: 15:30) 가격이 **−30% 이상 드로다운**
  `drawdown_from_hod >= 30%`
* 그리고 Daygainer는 아님 (`is_daygainer=0`)

> Failed Pump는 “사후 정보”로 라벨링해도 OK(라벨은 미래를 봐도 됨).
> 단, **피처는 반드시 t_attempt 이전(또는 t_attempt 직전 윈도우)까지만** 사용.

### 1.4 Neutral Attempt (선택)

Attempt는 있었지만, Daygainer도 Failed Pump도 아닌 케이스(예: +10~+40%로 마감).

* 옵션 1) Stage 1에서 **음성에 포함**(“성공이 아니면 음성”)
* 옵션 2) “중립”으로 분리해 **3‑class**(다만 룰학습이 단순해지려면 옵션1이 현실적)

---

## 2. 데이터 스키마(테이블 설계)

### 2.1 저장/엔진 권장(로컬 PC 최적)

* **원천/피처/라벨**은 `Parquet`(날짜 파티션) 권장
* 질의/조인은 **DuckDB**(로컬 컬럼너) 또는 **Polars**(파이프라인) 추천
* 장중 분봉이 크므로:

  * `minute_bars`는 `trade_date`로 파티셔닝
  * 필요 시 “유니버스(소형주/프리필터)”만 별도 스토어로 관리

---

## 2.2 마스터/캘린더

#### `dim_symbol`

| 컬럼           |     타입 | 설명                        |
| ------------ | -----: | ------------------------- |
| symbol       | STRING | 티커                        |
| exchange     | STRING | 거래소                       |
| sector       | STRING | 섹터(가능하면 point‑in‑time)    |
| industry     | STRING | 산업                        |
| is_active    |   BOOL | 현재 상장 여부                  |
| list_date    |   DATE | 상장일                       |
| delist_date  |   DATE | 상폐일(있으면)                  |
| shares_float | DOUBLE | 유통주식수(가능하면 point‑in‑time) |
| market_cap   | DOUBLE | 시총(가능하면 point‑in‑time)    |

> float/시총은 누수 위험이 있으니 가능하면 날짜 스냅샷 테이블로 분리 추천.

#### `dim_trading_calendar`

| 컬럼               |        타입 | 설명     |
| ---------------- | --------: | ------ |
| trade_date       |      DATE | 거래일    |
| is_open          |      BOOL | 개장 여부  |
| session_open_ts  | TIMESTAMP | 정규장 시작 |
| session_close_ts | TIMESTAMP | 정규장 종료 |

---

## 2.3 원천 가격 데이터

#### `fact_daily_bars` (정규장 일봉)

**PK**: `(symbol, trade_date)`

| 컬럼            |     타입 | 설명            |
| ------------- | -----: | ------------- |
| symbol        | STRING |               |
| trade_date    |   DATE |               |
| open          | DOUBLE |               |
| high          | DOUBLE |               |
| low           | DOUBLE |               |
| close         | DOUBLE |               |
| volume        | DOUBLE |               |
| dollar_volume | DOUBLE | close*volume  |
| vwap          | DOUBLE | (있으면)         |
| adj_factor    | DOUBLE | split/adj(선택) |

#### `fact_minute_bars` (정규장 분봉)

**PK**: `(symbol, trade_date, ts)`

| 컬럼                  |        타입 | 설명      |
| ------------------- | --------: | ------- |
| symbol              |    STRING |         |
| trade_date          |      DATE |         |
| ts                  | TIMESTAMP | 분 타임스탬프 |
| open/high/low/close |    DOUBLE |         |
| volume              |    DOUBLE |         |
| dollar_volume       |    DOUBLE |         |
| vwap                |    DOUBLE | (있으면)   |

#### `fact_premarket_bars` (선택)

프리마켓이 중요하면 따로 저장. 없으면 “프리마켓 피처”는 보류.

---

## 2.4 참조/정규화(누수 방지용)

#### `ref_minute_volume_profile`

**목적**: minute_rvol 계산을 위한 “기대 거래량”
**PK**: `(symbol, minute_of_day, trade_date)` 또는 `(symbol, minute_of_day, asof_date)`

| 컬럼                 |     타입 | 설명                    |
| ------------------ | -----: | --------------------- |
| symbol             | STRING |                       |
| asof_date          |   DATE | 이 날짜 **이전** 20거래일로 계산 |
| minute_of_day      |    INT | 0~389(미국 정규장 390분 가정) |
| exp_volume_20d     | DOUBLE | 기대 거래량(중앙값/평균)        |
| exp_volume_std_20d | DOUBLE | 표준편차(선택)              |

> 이렇게 “asof_date 기준으로만 과거를 사용”하게 만들어야 포인트‑인‑타임이 강제됩니다.

#### `ref_daily_rolling`

**PK**: `(symbol, asof_date)`

| 컬럼                 |     타입 | 설명           |
| ------------------ | -----: | ------------ |
| symbol             | STRING |              |
| asof_date          |   DATE | D‑1을 포함한 과거만 |
| avg_dollar_vol_20d | DOUBLE |              |
| atr_14             | DOUBLE |              |
| rvol_20d           | DOUBLE |              |
| low_20d            | DOUBLE |              |
| high_20d           | DOUBLE |              |
| …                  |        | 필요한 롤링 통계    |

---

## 2.5 라벨/이벤트 테이블

#### `label_day_outcome`

**PK**: `(symbol, trade_date)`

| 컬럼            |     타입 | 설명                  |
| ------------- | -----: | ------------------- |
| symbol        | STRING |                     |
| trade_date    |   DATE |                     |
| is_daygainer  |   BOOL | Daygainer 여부        |
| oc_return     | DOUBLE | (close-open)/open   |
| dollar_volume | DOUBLE |                     |
| price_ok      |   BOOL | price>=0.1          |
| liquidity_ok  |   BOOL | dollar_volume>=500k |

#### `event_attempt`

**PK**: `(symbol, trade_date, attempt_id)`

| 컬럼                 |        타입 | 설명                     |
| ------------------ | --------: | ---------------------- |
| symbol             |    STRING |                        |
| trade_date         |      DATE |                        |
| attempt_id         |       INT | 1,2,…                  |
| t_attempt          | TIMESTAMP | Attempt trigger 시점     |
| trig_minute_rvol   |    DOUBLE | 트리거 당시 minute_rvol     |
| trig_ret_5m        |    DOUBLE | 트리거 당시 5분 수익률          |
| trig_breakout_flag |      BOOL | 박스 돌파 여부               |
| attempt_type       |    STRING | “VOL+RET”, “VOL+VWAP”… |

#### `label_attempt_outcome`

**PK**: `(symbol, trade_date, attempt_id)`

| 컬럼                |     타입 | 설명              |
| ----------------- | -----: | --------------- |
| is_success        |   BOOL | (=is_daygainer) |
| is_failed_pump    |   BOOL | 실패펌프            |
| neutral_attempt   |   BOOL | 중립(선택)          |
| hod_after_attempt | DOUBLE | 사후 계산           |
| max_drawdown_pct  | DOUBLE | 사후 계산           |

---

## 2.6 피처 테이블(포인트‑인‑타임 기준 “asof”)

#### Stage 0용: `feat_d1_asof`

**PK**: `(symbol, trade_date)` (trade_date는 “예측 대상 날짜 D”)

| 컬럼            |     타입 | 설명                               |
| ------------- | -----: | -------------------------------- |
| symbol        | STRING |                                  |
| trade_date    |   DATE | 예측 대상 D                          |
| asof_date     |   DATE | D‑1                              |
| …             |        | D‑1까지의 일봉 기반 피처(모멘텀/변동성/수축/괴리 등) |
| market_regime | STRING | (있으면)                            |
| dow           |    INT | 0~4                              |

> `feat_d1_asof.trade_date = D`, `asof_date = D-1`로 강제하면 누수 방지에 매우 좋습니다.

#### Stage 1용: `feat_intraday_at_attempt`

**PK**: `(symbol, trade_date, attempt_id)`

| 컬럼                   |        타입 | 설명                        |
| -------------------- | --------: | ------------------------- |
| t_attempt            | TIMESTAMP | 이벤트 시점                    |
| win_15m_ret          |    DOUBLE | t_attempt 직전 15분 수익률      |
| win_60m_range        |    DOUBLE | 직전 60분 range              |
| win_60m_vol_zmax     |    DOUBLE | 직전 60분 거래량 z max          |
| vwap_dist            |    DOUBLE | close−vwap 비율             |
| rvol_spike_count_30m |       INT | 직전 30분 spike 수            |
| accel_price          |    DOUBLE | 가격 가속                     |
| accel_vol            |    DOUBLE | 거래량 가속                    |
| …                    |           | “t_attempt 이전만” 계산된 분봉 피처 |
| (옵션) d1_*            |           | D‑1 피처 일부 조인              |

---

## 2.7 ML 학습용 “예제 테이블”(권장: 물리 테이블로 저장)

모델 학습/재현성을 위해 “라벨+피처를 한 곳에 모아 스냅샷”을 남기는 것을 추천합니다.

#### `ml_stage0_examples`

**PK**: `(symbol, trade_date)`

* `X = feat_d1_asof.* (+ premarket)`
* `y = has_attempt` (attempt가 1개 이상이면 1)

#### `ml_stage1_examples`

**PK**: `(symbol, trade_date, attempt_id)`

* `X = feat_intraday_at_attempt.* (+ 일부 d1)`
* `y = is_success` (혹은 `is_failed_pump`와 별도 실험)

---

## 3. 샘플링 레시피(positive/negative 생성 규칙)

### 3.1 Stage 0 (Attempt 예측) — “일 단위”

#### 3.1.1 Positive 정의

* `has_attempt=1`인 (symbol, D) 전부
* `label_day_outcome.liquidity_ok=1`, `price_ok=1` 필터 적용(원문 조건 유지)

#### 3.1.2 Negative 정의(중요: 운영 분포를 반영)

운영에서 스캐너는 “유니버스 전체”를 보게 되므로, 학습도 아래 두 부류를 섞는 것을 추천합니다.

* **Neg‑A (Easy)**: Attempt 없음 (`has_attempt=0`)
* **Neg‑B (Hard)**: 약한 스파이크/관심은 있었지만 Attempt 기준 미달

  * 예: `max(minute_rvol) in [1.5, RVOL_TRIG)` 또는 `ret_5m`만 충족

#### 3.1.3 샘플링 비율(학습 vs 평가 분리)

* **학습용 다운샘플링**(예시):

  * Pos : Neg‑A : Neg‑B = 1 : 10 : 10 (총 1:20)
* **평가/리포트**:

  * 반드시 “하루 전체 유니버스”로 **Recall@N / Candidates/day** 계산

#### 3.1.4 날짜/그룹 분할

* Split은 **trade_date 그룹 기준** (같은 날짜가 train/valid에 동시에 들어가면 안 됨)
* 권장:

  * Train: 2021–2024
  * Test(OOS): 2025
  * (가능하면) Embargo: 경계 ±5거래일 제외(미세 누수 방지)

---

### 3.2 Stage 1 (Success vs Fail) — “이벤트 단위”

#### 3.2.1 Positive

* `has_attempt=1` AND `is_daygainer=1`
* 사용할 이벤트는 기본적으로 `attempt_id=1`(가장 이른 Attempt)

  * 이유: “가장 빠른 리드타임”에 맞추고, 샘플 독립성 증가

#### 3.2.2 Negative

* 1순위: `is_failed_pump=1` (정의가 명확한 하드 네거티브)
* 2순위(선택): neutral_attempt 포함

  * “성공이 아니면 모두 음성”으로 단순화하고 싶으면 포함
  * 다만 룰이 과하게 보수적으로 변할 수 있어, **실험 플래그로 분리** 권장:

    * 실험 A: Neg = failed_pump만
    * 실험 B: Neg = failed_pump + neutral

#### 3.2.3 클래스 불균형 처리

* Stage1은 보통 Pos가 매우 희소
* 방법:

  * 샘플링(예: 1:5~1:10) + 클래스 가중치
  * 또는 “하루 알림 예산”을 목표로 threshold/룰을 튜닝(운영 관점)

---

### 3.3 Attempt 이벤트 검출 알고리즘(구현 레시피)

아래는 백테스터/파이프라인에 바로 넣기 쉬운 형태입니다(파라미터화).

1. 분봉에 대해 `minute_of_day` 계산
2. `exp_volume_20d(symbol, minute_of_day, asof=D)`를 조인
3. `minute_rvol = volume / exp_volume_20d`
4. 후보 분 t에 대해:

   * `minute_rvol(t) >= RVOL_TRIG`
   * AND `[ret_5m(t) >= P_TRIG OR breakout_flag(t)=1]`
5. 트리거 발생 시 `attempt_id` 부여

   * 기본: 하루 첫 트리거만 저장(또는 최소 간격 30분 쿨다운으로 다중 이벤트 저장)

---

## 4. 피처 설계(최소 구현 → 확장)

### 4.1 Stage 0 (D‑1/장전) 피처 묶음(예시)

* 변동성 수축/박스:

  * `atr_pctile`, `bb_width_pctile`, `keltner_squeeze_flag`, `tight_range_intensity`
* 거래량/관심:

  * `rvol_20d`, `dollar_vol_20d`, `volume_dryup_score`
* 가격 레벨:

  * `dist_to_20d_low`, `dist_to_52w_high`, `close_vs_ma20`, `gap_history`
* 모멘텀/괴리:

  * `rsi_5`, `rsi_14`, `rsi_div = rsi_5 - rsi_14`
  * `macd_div`, `ma_5_20_div`
* 메타:

  * `dow`, `market_regime`(있으면), 섹터 모멘텀(가능하면)

> Stage 0는 “Attempt 리콜”이 목적이므로 **너무 타이트한 타이밍 지표보다 ‘준비 상태’ 지표**가 유리합니다.

---

### 4.2 Stage 1 (Attempt 시점) 피처 묶음(예시)

**반드시 t_attempt 이전만 사용**

* 윈도우 기반(15/30/60/120m):

  * `ret_15m, ret_60m`, `range_60m`, `high_low_ratio`
  * `vol_zmax_60m`, `spike_count_30m`
  * `price_accel`, `vol_accel`
* 미세구조:

  * `vwap_dist`, `above_vwap_ratio_30m`
  * `micro_pullback_depth`(트리거 직전 눌림 깊이)
* 이벤트 정렬:

  * `first_anomaly_timing` = (t_attempt - first_spike_ts)
* (옵션) Stage0 요약 피처 일부:

  * `tight_range_intensity`, `atr_pctile`, `dist_to_20d_low`

---

## 5. 룰 학습/추출 방법 — **RuleFit 선택(택1)**

### 5.1 RuleFit을 고른 이유(이 프로젝트에 맞는 점)

* 최종 산출물이 “스캐너 필터 룰”이므로,
  **트리 기반 룰(조건절)**을 만들고 **L1로 희소화**해 “몇 개 룰만 남기는” 방식이 잘 맞습니다.
* SHAP→서로게이트 트리보다, RuleFit은 애초에 “룰을 구성 요소로” 학습하므로

  * 룰 리스트가 자연스럽게 나오고
  * 계수/기여도로 우선순위를 매기기 쉽습니다.
* 로컬 하이엔드 PC에서 충분히 돌아갑니다(데이터가 수만~수십만 샘플이어도 현실적).

---

### 5.2 RuleFit 학습 파이프라인(Stage0/Stage1 공통)

#### 입력

* Stage0: `ml_stage0_examples` (y=has_attempt)
* Stage1: `ml_stage1_examples` (y=is_success)

#### 전처리(권장)

* 결측은 “명시적” 처리:

  * 수치형: median 대체 + `is_missing_*` 플래그 추가(룰이 결측을 조건으로 쓰는 경우가 실제로 있음)
* 과도한 스케일 차이는 RuleFit 내부에서 크게 문제는 아니지만,

  * 일부 구현체는 표준화가 도움이 될 수 있음(선택)

#### Rule 생성(트리 앙상블)

* 얕은 트리 여러 개로 룰 후보 생성:

  * depth 2~4 권장(룰이 너무 복잡해지는 것 방지)
  * subsample/colsample로 다양성 확보

#### 룰 선택(희소 선형 모델)

* 생성된 룰(0/1) + 원본 피처를 함께 넣고
* **L1 로지스틱(또는 ElasticNet)**으로 중요 룰만 남김

---

### 5.3 룰을 “Scanner Filter”로 변환하는 규칙(매우 중요)

RuleFit 결과는 보통 “룰 여러 개의 가중합” 형태입니다. 운영 룰로 내리려면 아래 절차가 필요합니다.

1. **룰 후보 정렬**

   * (A) 절대계수 |coef| 큰 순
   * (B) 해당 룰이 커버하는 샘플 수(지나치게 희소한 룰 제외)
   * (C) 연도별 안정성(2021/2022/… 분할로 부호/효과가 일관한지)

2. **룰 셋을 “OR of ANDs” 형태로 정리**

   * 예:

     * Rule1: `(tight_range_intensity>0.72) AND (rvol_20d>2.8) AND (dist_to_20d_low<-0.12)`
     * Rule2: `(atr_pctile<0.2) AND (premarket_rvol>5) AND (gap_pct>0.08)`
   * 최종 스캐너는 `Rule1 OR Rule2 OR Rule3 …`

3. **운영 제약으로 컷 튜닝**

   * Stage0: “Candidates/day ≈ 100~200”을 맞추도록 룰 수/임계값 조정
   * Stage1: “Alerts/day ≈ 20~50” 같은 예산에 맞춰 조정

4. **룰 최소화**

   * 룰 수가 늘수록 운영/설명 비용이 커짐
   * 목표: Stage0는 5~15개 룰, Stage1은 3~10개 룰 정도부터 시작 권장

---

### 5.4 룰 품질 검증(필수)

* **일 단위 지표**로 검증:

  * Stage0: Recall@200, Recall@100, Candidates/day 분포
  * Stage1: Alerts/day, Success rate among alerts, 평균 리드타임
* **레짐/연도별 성능**:

  * 2021/2022/2023/2024/2025로 나눠 룰의 일관성 체크
* **티커 누수 방지 리포트**(가능하면):

  * “본 적 없는 티커”에서 성능(간단히 ticker‑group split 한번)

---

## 6. 백테스터(antigravity) 통합 체크리스트

### 6.1 데이터 생성 순서(재현성)

1. 원천 적재: daily/minute/premarket
2. `ref_*` 생성(rolling, volume profile) — **asof_date 기준으로만**
3. Attempt 이벤트 탐지 → `event_attempt`
4. day 라벨/attempt outcome 라벨 생성
5. Stage0/Stage1 피처 생성(각각 asof 기준 강제)
6. `ml_stage*_examples` 스냅샷 저장(모델 버전과 함께)

### 6.2 운영 시뮬레이션(가장 중요한 “제품형 백테스트”)

* 매 거래일 D에 대해:

  1. Stage0 룰/점수로 Top‑N 후보 선정
  2. 장중 분봉 진행하면서 Attempt trigger 발생 시 Stage1 룰 적용(경보)
  3. 알림 예산/쿨다운 적용
  4. EOD에 라벨로 성과 집계

---

## 7. 구현 스니펫(개념 코드)

### 7.1 Attempt 이벤트 검출(개념)

```python
# for each (symbol, trade_date):
# minute_df: ts, close, volume, minute_of_day
minute_df = minute_df.join(ref_profile, on=["symbol","asof_date","minute_of_day"])
minute_df["minute_rvol"] = minute_df["volume"] / minute_df["exp_volume_20d"]

minute_df["ret_5m"] = minute_df["close"].pct_change(5)
minute_df["breakout_flag"] = minute_df["close"] > minute_df["close"].rolling(60).max().shift(1)

trigger = (minute_df["minute_rvol"] >= RVOL_TRIG) & (
    (minute_df["ret_5m"] >= P_TRIG) | (minute_df["breakout_flag"])
)

t_attempt = minute_df.loc[trigger, "ts"].min()  # earliest attempt
```

### 7.2 Stage0 평가 지표(일 단위)

```python
# per day: sort all symbols by score, take topN, compute recall of has_attempt==1
recall_at_n = hits / total_attempts_that_day
```

---

## 8. “바로 다음 액션” 권장(가장 효율 좋은 순서)

1. **event_attempt + label_attempt_outcome**를 먼저 완성
2. Stage0: `has_attempt` 예측을 “일 단위 Recall@N”으로 리포팅 체계부터 고정
3. Stage1: `attempt_id=1`만으로 success vs failed_pump 실험 A부터
4. RuleFit으로 룰을 뽑고, **Candidates/day / Alerts/day 예산**에 맞춰 룰을 줄이기
5. 마지막에 neutral을 포함한 실험 B, 그리고 Stage2 정책(쿨다운/레짐별 θ) 정교화

---

## 부록 A. 테이블 요약(ER 관점)

* `fact_daily_bars` → `ref_daily_rolling` → `feat_d1_asof` → `ml_stage0_examples`
* `fact_minute_bars` + `ref_minute_volume_profile` → `event_attempt`
* `event_attempt` + `fact_minute_bars` → `feat_intraday_at_attempt` → `ml_stage1_examples`
* `label_day_outcome`는 daygainer 정의의 기준 테이블
* `label_attempt_outcome`는 attempt 성공/실패/중립 라벨 테이블

---

원하면, 위 스키마를 그대로 쓰되 **당신이 이미 구현해둔 백테스터 내부 데이터 구조(파케이 컬럼명/타임존/분봉 해상도/프리마켓 유무)**에 맞춰서:

* 컬럼명까지 포함한 **실제 SQL DDL 버전(duckdb 기준)**
* Attempt trigger 파라미터( RVOL_TRIG, P_TRIG, breakout 정의 )의 **초기값 세트 + 민감도 실험 계획**
* RuleFit 결과를 “최종 IF‑THEN 룰”로 내리는 **자동 룰 컴파일러 포맷(JSON/YAML)**

까지 한 번에 이어서 문서화해드릴게요.
