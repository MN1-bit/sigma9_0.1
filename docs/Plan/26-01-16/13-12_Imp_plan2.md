아래는 요청하신 내용을 **Sigma9의 실제 코드 구조(backend/container.py, core/tick_dispatcher.py, strategies/seismograph/strategy.py, DI Container, 데이터 스트림 A/T/AM, Parquet 레이크)**에 **정확히 맞춰** “SSOT 문서” 스타일로 구체화한 설계안입니다.   

---

# SSOT: NautilusLab(Research+Backtest) + ML Overlay 이식 설계 v0.2

**문서 번호**: ML-NT-SSOT-001
**작성일**: 2026-01-16
**대상 시스템**: Sigma9 v3.7 
**목표**:

1. NautilusTrader는 **연구+백테스트만** 사용(라이브/IB 어댑터 제외)
2. ML은 **발견(Discovery)→검증(Validation)→증류(Distill)→배포(Deploy)** 워크플로우로 운영
3. Sigma9 런타임은 기존 구조(RealtimeScanner, IgnitionMonitor, TickDispatcher, SeismographStrategy/ScoringStrategy)를 유지하며 **전략 플러그인 형태로 이식**

---

## 1. 불변 조건(기존 구조 유지)

### 1.1 런타임 이벤트 흐름 불변

* Massive WS `on_tick(T.*)` → TickBroadcaster → TickDispatcher.dispatch() → `strategy_tick_handler → SeismographStrategy.on_tick()` 흐름은 유지합니다. 
* RealtimeScanner의 1초 폴링 → 신규 gainers 탐지 → `SeismographStrategy.calculate_watchlist_score_detailed()` 호출 흐름 유지. 
* IgnitionMonitor의 1초 폴링 → snapshot 조회 → `SeismographStrategy.calculate_ignition_score()` 흐름 유지. 

### 1.2 DI Container 불변(확장만)

* DI Container는 Config/DataRepository/ParquetManager/ScoringStrategy/RealtimeScanner/IgnitionMonitor 등을 주입하는 구조를 유지하고, 여기에 ML 관련 의존성을 “추가 주입”합니다. 
* ScoringStrategy 인터페이스 추출로 순환 의존성을 해결한 구조는 그대로 따릅니다. 

### 1.3 데이터 레이크/채널 불변

* Parquet 레이크(일봉/1m/1h, indicators, scores 캐시) 구조 유지. 
* 실시간 채널 특성 유지: `A.*`(1초), `T.*`(틱), `AM.*`(1분). 

---

## 2. 추가될 클래스/모듈 목록(파일 트리)

### 2.1 설계 의도

* **런타임(backend/)**: “ML 추론 + 온라인 피처 빌더 + 아티팩트 로딩”만 추가
* **오프라인 Lab(lab/nautilus_lab/)**: “데이터셋 생성 + discovery + validation + nautilus backtest” 수행 후 **아티팩트(manifest + 모델/클러스터 파일)**를 `data/artifacts/`로 배출
* **전략 플러그인(backend/strategies/)**: 기존 seismograph를 건드리지 않고, **ML Overlay 버전 전략을 새 플러그인으로 추가**

> 기존 모듈 구조는 `backend/core`, `backend/models`, `backend/strategies`, `config/`, `data/`로 이미 정리되어 있습니다. 

---

### 2.2 최종 파일 트리(추가분 강조)

```text
Sigma9-0.1/
├── backend/
│   ├── container.py
│   ├── core/
│   │   ├── interfaces/
│   │   │   ├── scoring.py                      # 기존
│   │   │   ├── artifact_registry.py            # [NEW] 아티팩트 로딩 인터페이스
│   │   │   └── feature_builder.py              # [NEW] 온라인 피처 빌더 인터페이스
│   │   │
│   │   ├── ml/
│   │   │   ├── artifact_registry_fs.py         # [NEW] 파일시스템 기반 Registry 구현
│   │   │   ├── online_feature_builder.py       # [NEW] T/A/AM 입력 → window feature
│   │   │   ├── ml_inference.py                 # [NEW] 모델/클러스터 로드 + score()
│   │   │   ├── ml_gate.py                      # [NEW] tradeability/예산/쿨다운 gate
│   │   │   └── schema_hash.py                  # [NEW] feature_spec 정합성 해시/검증
│   │   │
│   │   └── backtest/
│   │       ├── nautilus_bridge.py              # [NEW] NautilusLab 결과를 Sigma9 report로 변환(옵션)
│   │       └── metrics.py                      # [NEW] Alert/LeadTime/Utility 공통 지표
│   │
│   ├── models/
│   │   ├── backtest.py                          # 기존
│   │   ├── feature_spec.py                      # [NEW] FeatureSpec 모델(입력 계약)
│   │   ├── artifact_manifest.py                 # [NEW] ArtifactManifest 모델(출력 계약)
│   │   └── experiment.py                        # [NEW] BacktestRunConfig 모델(실험 정의)
│   │
│   └── strategies/
│       ├── seismograph/                         # 기존
│       └── seismograph_ml/                      # [NEW] ML Overlay 전략 플러그인
│           ├── strategy.py                       # [NEW] SeismographMLStrategy (ScoringStrategy 구현)
│           ├── models.py                         # [NEW] 전략 전용 모델(알림/근거 등)
│           └── scoring/
│               ├── overlay.py                    # [NEW] base score + ml score 결합 로직
│               └── explain.py                    # [NEW] 근거(Top features/cluster) 요약
│
├── config/
│   ├── strategy.yaml                             # 기존(가정: 전략 선택/설정)
│   ├── feature_specs/                            # [NEW] FeatureSpec SSOT 입력
│   │   └── FS_*.yaml
│   └── backtest_runs/                            # [NEW] Backtest run config 템플릿/실행 정의
│       └── RUN_*.yaml
│
├── lab/
│   └── nautilus_lab/                             # [NEW] 오프라인 Research+Backtest 서브시스템
│       ├── README.md
│       ├── pipelines/
│       │   ├── build_dataset.py                  # T0 정렬/윈도우 샘플링
│       │   ├── discovery.py                      # 임베딩/클러스터링/이상탐지
│       │   ├── validation.py                     # OOS/유틸리티/선정
│       │   ├── distill.py                        # 룰/threshold/경량화
│       │   └── export_artifacts.py               # manifest + 파일 배출
│       ├── backtest/
│       │   ├── run_nautilus.py                   # Nautilus Backtest 실행기(배치)
│       │   ├── adapters/
│       │   │   ├── parquet_stream.py             # Parquet → 스트림(시간정렬 계약)
│       │   │   └── sigma9_domain.py              # Tick/Bar/Quote 매핑
│       │   └── evaluators/
│       │       ├── alert_metrics.py              # Alert rate/Precision@K/lead time
│       │       └── utility_metrics.py            # 슬리피지 포함 EV/리스크
│       └── configs/
│           ├── feature_specs/                    # (옵션) config/feature_specs 미러
│           └── backtest_runs/                    # (옵션) config/backtest_runs 미러
│
└── data/                                         # Git 제외 런타임 데이터 :contentReference[oaicite:12]{index=12}
    ├── parquet/                                  # 기존(일봉/1m/1h/indicators/scores) :contentReference[oaicite:13]{index=13}
    └── artifacts/                                # [NEW] Lab 산출물 저장소(모델/클러스터/manifest)
        ├── manifests/
        │   └── ART_*.json
        ├── feature_specs_snapshot/
        │   └── FS_*.yaml                         # 실험 당시 스냅샷(불변성)
        └── payloads/
            └── ART_*/
                ├── model.bin / model.pkl / model.onnx
                ├── clusters.bin
                ├── thresholds.json
                └── explainers.json
```

**수용 기준(파일 트리)**

* `backend/`는 런타임 추론에 필요한 최소 모듈만 추가되고, 기존 Scanner/Monitor/TickDispatcher 호출 체인 변경이 없습니다. 
* ML Overlay는 **새 전략 플러그인(backend/strategies/seismograph_ml)**로 들어가며, 기존 `seismograph/`를 “기본 전략”으로 유지합니다. 

---

## 3. 데이터 계약(입출력 스키마)

### 3.1 FeatureSpec (입력 SSOT) — `config/feature_specs/FS_*.yaml`

#### 3.1.1 목적

* **온라인/오프라인 피처 산출을 완전히 동일**하게 만들기 위한 “단일 진실(Single Source of Truth)”
* TickDispatcher에서 들어오는 이벤트(`T.*`, `A.*`, `AM.*`)를 **어떤 윈도우로 집계**하고, 어떤 피처를 만들지, 어떤 정규화를 적용할지 고정  

#### 3.1.2 스키마(필드 정의)

아래는 “표준 스키마”입니다(실파일은 YAML).

```yaml
feature_spec:
  id: "FS_2026-01-16_001"
  version: "1.0.0"
  owner: "sigma9"
  created_at: "2026-01-16T00:00:00+09:00"
  description: "Pre-surge discovery + runtime scoring (multi-resolution)"

  # (A) 시간/세션 규칙
  calendar:
    timezone: "America/New_York"
    sessions: ["pre", "regular", "after"]
    treat_halts_as: "gap"               # gap | forward_fill | drop

  # (B) 입력 소스 매핑 (Sigma9 실시간 채널과 1:1 대응)
  sources:
    tick:
      enabled: true
      stream_channel: "T.*"             # :contentReference[oaicite:18]{index=18}
      fields: ["ts", "price", "size"]
    bar_1s:
      enabled: true
      stream_channel: "A.*"             # :contentReference[oaicite:19]{index=19}
      fields: ["ts", "o", "h", "l", "c", "v"]
    bar_1m:
      enabled: true
      stream_channel: "AM.*"            # :contentReference[oaicite:20]{index=20}
      fields: ["ts", "o", "h", "l", "c", "v"]
    daily:
      enabled: true
      parquet_path: "data/parquet/daily/all_daily.parquet"  # :contentReference[oaicite:21]{index=21}

  # (C) 윈도우 정의 (온라인/오프라인 공통)
  windows:
    - name: "w5s"
      base: "bar_1s"
      length: "5s"
      step: "1s"
    - name: "w15s"
      base: "bar_1s"
      length: "15s"
      step: "1s"
    - name: "w60s"
      base: "bar_1s"
      length: "60s"
      step: "1s"
    - name: "w5m"
      base: "bar_1m"
      length: "5m"
      step: "1m"

  # (D) 피처 패밀리 (전조 정의 금지: '원시/형태' 중심)
  features:
    # 1) 활동성/가속도
    - key: "intensity.trade_count_z"
      window: "w15s"
      op: "zscore"
      input: "tick"
      params: { lookback: "20d_tod" }   # time-of-day baseline

    - key: "intensity.volume_rvol_tod"
      window: "w60s"
      op: "rvol_tod"
      input: "bar_1s"
      params: { lookback_days: 20, baseline: "median" }

    # 2) 가격 경로/임팩트
    - key: "path.return_slope"
      window: "w60s"
      op: "linreg_slope"
      input: "bar_1s"
      params: { on: "close" }

    - key: "impact.ret_over_signed_vol"
      window: "w15s"
      op: "ratio"
      inputs: ["bar_1s.close_return", "tick.signed_volume_proxy"]
      params: { signed_proxy: "lee_ready_if_quote_available_else_tickrule" }

    # 3) 변동성 구조(압축/확대)
    - key: "vol.range_pct"
      window: "w60s"
      op: "range_pct"
      input: "bar_1s"
      params: { use: ["high", "low", "close"] }

  # (E) 정규화/결측/클리핑
  normalization:
    mode: "per_symbol_rolling"          # per_symbol_rolling | global
    lookback: "60d"
    clip:
      method: "winsor"
      p_low: 0.005
      p_high: 0.995
    missing:
      policy: "keep_nan_and_flag"       # keep_nan_and_flag | forward_fill

  # (F) 런타임 게이트(알림 예산/쿨다운은 feature_spec에서 고정 가능)
  runtime_gates:
    tradeability:
      min_dollar_volume_1m: 200000
      max_spread_pct: 2.0
    alert_budget:
      max_alerts_per_day: 60
      symbol_cooldown_sec: 180
```

#### 3.1.3 수용 기준(FeatureSpec)

* `sources.stream_channel`이 Sigma9 실시간 채널(`A.*`, `T.*`, `AM.*`)과 일치해야 합니다. 
* 오프라인(Lab)에서 생성한 피처와 런타임(backend)에서 생성한 피처의 **키/윈도우/정규화가 1:1 동일**해야 합니다(“schema_hash”로 강제).
* 세션/정지 처리 규칙이 고정되어야 합니다(동일 데이터로 실험 결과가 재현).

---

### 3.2 Artifact Manifest (출력 SSOT) — `data/artifacts/manifests/ART_*.json`

#### 3.2.1 목적

* Lab(Discovery/Validation/Backtest)에서 산출된 “승자 조합”을 **런타임이 안전하게 로드**하기 위한 계약
* 어떤 feature_spec로 만들었고, 어떤 데이터 구간으로 학습/검증했으며, 어떤 파일(모델/클러스터/threshold)을 로드해야 하는지 “단일 문서”로 고정

#### 3.2.2 스키마(필드 정의)

```json
{
  "artifact_manifest": {
    "id": "ART_2026-01-16_001",
    "created_at": "2026-01-16T00:00:00+09:00",
    "producer": {
      "system": "lab/nautilus_lab",
      "git_commit": "abcdef1234",
      "python": "3.12.x",
      "os": "windows"
    },

    "feature_spec_ref": {
      "id": "FS_2026-01-16_001",
      "schema_hash": "sha256:....",
      "snapshot_path": "data/artifacts/feature_specs_snapshot/FS_2026-01-16_001.yaml"
    },

    "dataset_ref": {
      "universe": "us_equities_filtered",
      "time_range": { "start": "2024-01-01", "end": "2025-12-31" },
      "labeling": {
        "anchor": "first_cross_prevclose_pct",
        "anchor_param": 0.10,
        "pre_window": { "start_offset_min": -30, "end_offset_min": -5 }
      },
      "negatives": {
        "type": ["hard_negative", "same_symbol_other_days", "time_of_day_matched"],
        "ratio": 5
      }
    },

    "model": {
      "type": "xgboost|cluster_membership|hybrid",
      "objective": "alert_utility_max",
      "outputs": ["score", "explain_topk", "cluster_id"],
      "thresholds": {
        "global_score_min": 0.72,
        "per_cluster_min": { "C01": 0.65, "C02": 0.80 }
      }
    },

    "performance_oos": {
      "split": { "train_end": "2025-06-30", "test_start": "2025-07-01", "test_end": "2025-12-31" },
      "alert_budget": { "max_alerts_per_day": 60 },
      "metrics": {
        "precision_at_budget": 0.31,
        "median_lead_time_min": 9.0,
        "tail_loss_p95": -0.07,
        "utility_score": 1.42
      }
    },

    "payload": {
      "base_path": "data/artifacts/payloads/ART_2026-01-16_001/",
      "files": [
        { "name": "model.bin", "sha256": "..." },
        { "name": "clusters.bin", "sha256": "..." },
        { "name": "thresholds.json", "sha256": "..." },
        { "name": "explainers.json", "sha256": "..." }
      ]
    },

    "compatibility": {
      "runtime_strategy_plugin": "backend/strategies/seismograph_ml",
      "required_streams": ["A.*", "T.*", "AM.*"],
      "min_bar_history": { "bar_1s": "60s", "bar_1m": "20m", "daily": "60d" }
    }
  }
}
```

#### 3.2.3 수용 기준(Artifact Manifest)

* 런타임은 manifest만 읽고도 **(1) feature_spec 정합성 검증**, **(2) 파일 무결성 검증**, **(3) 전략 플러그인 선택**을 수행할 수 있어야 합니다.
* `compatibility.required_streams`는 Sigma9의 스트림 구성(A/T/AM)에 부합해야 합니다. 

---

## 4. Backtest run config(실험 정의) 표준 템플릿

### 4.1 목적

* Lab에서 Nautilus 백테스트를 돌릴 때 “어떤 데이터/어떤 전략/어떤 아티팩트/어떤 평가 기준”인지 **완전히 재현 가능**하게 고정
* Sigma9는 이미 `core/backtest_engine.py`, `models/backtest.py`, `core/backtest_report.py`가 존재하므로 
  **NautilusLab 결과를 BacktestReport로 변환**할 수 있는 브리지를 옵션으로 둡니다(필수는 아님).

### 4.2 표준 템플릿 — `config/backtest_runs/RUN_*.yaml`

```yaml
backtest_run:
  id: "RUN_2026-01-16_001"
  created_at: "2026-01-16T00:00:00+09:00"
  engine: "nautilus"
  mode: "batch"                    # batch | walk_forward

  # (A) 데이터 입력
  data:
    parquet_root: "data/parquet"   # :contentReference[oaicite:25]{index=25}
    daily:
      path: "daily/all_daily.parquet"
    intraday:
      bar_1m:
        path_glob: "1m/{ticker}.parquet"
      bar_1s:
        path_glob: "1s/{ticker}.parquet"         # (없으면 disable)
    universe:
      source: "watchlist|csv|query"
      tickers_csv: "scripts/control_groups.csv"  # (예: R-3 산출물 활용) :contentReference[oaicite:26]{index=26}

  # (B) 전략/피처/아티팩트 결합
  strategy:
    plugin: "seismograph_ml"       # backend/strategies/seismograph_ml :contentReference[oaicite:27]{index=27}
    base_plugin: "seismograph"     # 비교 기준
    params:
      score_version: "v3"
      use_ml_overlay: true
  feature_spec_ref:
    id: "FS_2026-01-16_001"
    path: "config/feature_specs/FS_2026-01-16_001.yaml"
  artifact_ref:
    id: "ART_2026-01-16_001"
    manifest_path: "data/artifacts/manifests/ART_2026-01-16_001.json"

  # (C) 백테스트 구간/스플릿
  time:
    timezone: "America/New_York"
    start: "2025-01-01"
    end: "2025-12-31"
    session_filter: ["pre", "regular"]           # pre만/regular만도 가능
    warmup:
      daily_lookback_days: 60
      intraday_warmup_min: 30

  splits:
    type: "oos_holdout"            # oos_holdout | walk_forward
    train_end: "2025-06-30"
    test_start: "2025-07-01"
    test_end: "2025-12-31"

  # (D) 체결/비용/슬리피지 모델(실전 유틸리티 중심)
  execution:
    fill_model: "next_bar_open|mid|conservative"
    slippage:
      model: "spread_pct_plus"
      params: { spread_mult: 1.0, fixed_bps: 5 }
    commission:
      model: "ib_like"
      params: { per_share: 0.005, min: 1.0 }
    latency:
      feed_ms: 250
      order_ms: 250

  # (E) 평가(알림 중심)
  evaluation:
    alert_budget:
      max_alerts_per_day: 60
      symbol_cooldown_sec: 180
    lead_time:
      target_min: 5
      target_max: 15
    metrics: ["precision_at_budget", "median_lead_time", "tail_loss_p95", "utility_score"]
    baselines:
      - "seismograph_only"
      - "random_budget_matched"

  # (F) 출력/아카이브
  output:
    base_dir: "data/experiments/RUN_2026-01-16_001/"
    write_trades: true
    write_alerts: true
    write_equity_curve: true
    write_sigma9_backtest_report: true          # core/backtest_report 호환 저장(옵션) :contentReference[oaicite:28]{index=28}
```

### 4.3 수용 기준(Backtest run config)

* `strategy.plugin`이 Sigma9의 **전략 플러그인 로더 구조**(backend/strategies 하위 폴더)와 일치해야 합니다. 
* `feature_spec_ref`가 로드되면 런타임/오프라인 모두 **schema_hash**가 일치해야 실행됩니다(불일치 시 즉시 실패).
* 결과물은 최소 `alerts`, `trades`, `metrics`가 저장되어야 하며, 옵션으로 Sigma9의 BacktestReport 형태로 변환 저장할 수 있어야 합니다. 

---

## 5. DI Container에 추가 주입(SSOT 수준 선언)

현재 DI Container 구성은 Config, DataRepository, ParquetManager, ScoringStrategy, RealtimeScanner, IgnitionMonitor, SubscriptionManager 등을 주입합니다. 
여기에 아래 3개를 “추가”합니다.

* `ArtifactRegistry` (FS 기반 구현: `artifact_registry_fs.py`)
* `OnlineFeatureBuilder` (feature_spec 기반 window 집계)
* `MLInference` (manifest 기반 모델/클러스터 로드 + score/explain)

**수용 기준(DI)**

* `ScoringStrategy`는 config에 따라 `seismograph` 또는 `seismograph_ml`로 교체 가능해야 합니다(Scanner/Monitor 호출부 변경 금지). 

---

원하시면 다음 단계로(질문 없이 진행 가능):

1. `SeismographMLStrategy`의 “호출 계약”을 **현재 실제 호출점**(RealtimeScanner/ IgnitionMonitor / TickDispatcher 기준)으로 딱 고정해 드리고 
2. `feature_spec`의 **최소 필수 피처 키 세트(전조 정의 금지 버전)**를 v1로 확정(윈도우/정규화/누수 방지 포함)
3. `artifact_manifest`에서 “클러스터 기반 vs xgboost 기반 vs 하이브리드” 3가지 페이로드 표준을 분리 정의

까지 한 번에 SSOT로 이어서 작성해드리겠습니다.
