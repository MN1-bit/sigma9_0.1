Sigma9 × Nautilus Research/Backtest 이식 아키텍처 기획안 v0.1
0) 목표 / 범위
목표

연구(Research): “전조를 정의하지 않고” 데이터에서 전조 후보 패턴을 자동 발굴

백테스트(Backtest): 발굴/학습된 신호를 시간흐름(누수 0) + 주문/체결 시뮬로 검증

운영 이식: 검증된 결과물을 **Sigma9 실시간 스캐너/점수(ScoringStrategy)**에 모듈식으로 주입

범위(이번 이식에서 “안 하는 것”)

Nautilus의 라이브 트레이딩/IB 어댑터는 사용하지 않음

이유: 최근 릴리즈에서도 Python 3.14에서 [ib] extra가 upstream 호환성 문제로 unavailable로 공지됨

따라서 라이브는 지금처럼 ib_insync + TWS로 유지 

archt

법무/라이선스 참고(중요)

NautilusTrader 라이선스는 LGPL-3.0입니다.
→ “엔진을 라이브러리로 깊게 임베드”하기보다, 별도 프로세스/컨테이너 서비스 형태로 붙이면(IPC/HTTP로 연결) 법적/배포 리스크가 훨씬 줄어듭니다.

1) 현재 Sigma9 구조에서 “어디에 붙이는가”

Sigma9는 이미

FastAPI + WebSocket,

Massive WS(틱/바) + Snapshot,

TickDispatcher 중심 분배,

DI Container로 모듈 주입,

Parquet 레이크(일봉/1m/1h) + indicators/scores 캐시,

R-4 백테스트/피처 파이프라인 스크립트들
을 갖고 있습니다. 

archt

 

archt

 

archt

따라서 붙이는 위치는 2곳입니다.

오프라인(로컬 PC 중심): “NautilusLab(연구+백테스트) 서브시스템”

온라인(서버/스캐너): “ML Inference 플러그인(ScoringStrategy 구현체)”

2) 전체 구성도(개념)
flowchart TB
  subgraph Sigma9["Sigma9 기존 (AWS EC2)"]
    WS["MassiveWebSocketClient"]
    DISP["TickDispatcher"]
    STRAT["SeismographStrategy / ScoringStrategy"]
    SCAN["RealtimeScanner"]
    MON["IgnitionMonitor"]
    PQ["ParquetManager + DataRepository"]
    API["FastAPI + WebSocket"]
    REG["Model/Artifact Registry (버전 고정)"]
  end

  subgraph LocalPC["로컬 PC: NautilusLab (Research + Backtest only)"]
    NB["Jupyter/Notebook Research Workspace"]
    DS["Dataset Builder (T0 정렬/윈도우 샘플링)"]
    DISC["Discovery (Anomaly/Embedding/Clustering)"]
    VAL["Validation (OOS + Utility Metrics)"]
    DIST["Distill (룰/설명/게이트 추출)"]
    NBT["Nautilus BacktestNode/Engine"]
    ADP["Parquet→Nautilus Data Adapter (스트리밍)"]
    OUT["Results Exporter (trades/metrics/alerts)"]
  end

  WS --> DISP --> STRAT --> SCAN --> API
  MON --> API
  PQ --> STRAT
  PQ --> ADP --> NBT --> OUT --> REG
  NB --> DS --> DISC --> VAL --> DIST --> REG
  REG --> STRAT


Sigma9의 실시간 스트림 구조(AM/T/A 채널, TickDispatcher, Scanner/Monitor)는 그대로 유지합니다. 

archt

 

archt

Nautilus 쪽은 BacktestEngine/BacktestNode를 중심으로 “히스토리컬 데이터 스트림을 흘려 시뮬레이션”하는 커널만 사용합니다.

3) NautilusLab(연구+백테스트) 서브시스템 설계
3.1 왜 Nautilus의 BacktestEngine/Node만 쓰는가

Nautilus 문서상 백테스트는 데이터 스트림을 BacktestEngine에 흘려서 구성요소(Cache/MessageBus/Portfolio/Strategies/Execution 등)로 시뮬레이션하며, High-level(BacktestNode) / Low-level(BacktestEngine) 2단 API를 제공합니다.
→ 우리는 여기서 **BacktestNode(배치/실험 관리)**를 기본으로 쓰고, 필요할 때만 **BacktestEngine(세밀 제어)**로 내려갑니다.

3.2 핵심 모듈
(A) Parquet→Nautilus Data Adapter

Sigma9는 이미 Parquet 레이크(일봉/all_daily, 1m/1h, indicators/scores 캐시)를 갖고 있습니다. 

archt

 

archt

Nautilus는 BacktestEngine에 Data 객체 리스트를 넣거나, 대규모 데이터는 스트리밍(이터레이터) 방식으로 적재해 성능을 확보하는 패턴을 문서로 안내합니다(정렬 계약/검증 포함).

기획 포인트

“Sigma9 Parquet 스키마”를 **Nautilus domain data(Bar/Quote/Trade 등)**로 변환하는 어댑터 1개를 만든 뒤,

백테스트는 어댑터가 내보내는 스트림만 받게 해서, 데이터 레이어를 깔끔히 분리합니다.

(B) Backtest Harness (BacktestNode)

여러 설정(전략 파라미터/슬리피지/수수료/게이트)을 한 번에 돌려야 하므로 BacktestNode를 중심으로 구성합니다.

(C) Results Exporter

산출물은 “시각화”보다 재현 가능한 파일/메타데이터가 핵심입니다.

trades, fills, equity curve, alert timestamps

utility metrics(알림 예산 하에서 Precision@K, lead time, tail loss 등)

Exporter는 Sigma9의 data/parquet/scores/ 또는 별도 artifacts/로 저장(버전 포함)하게 설계합니다. 

archt

3.3 Research Workspace

Nautilus는 “파이썬 스크립트 또는 Jupyter notebook으로 백테스트/라이브를 수행”하는 접근을 공식 문서로 안내하며, JupyterLab 도커 이미지도 제공합니다.
→ Sigma9의 R-4 스크립트(build_*, eda_features.py)를 노트북/리서치 워크스페이스에서 그대로 재사용하거나, DS/ML 파이프라인으로 흡수합니다. 

archt

4) ML 워크플로우(추천안) — “전조 정의 금지” 버전

핵심: 전조를 사람이 정의하지 않고, (1) 이상 패턴을 먼저 “발견” → (2) 미래 성과로 “검증” → (3) 운영 가능한 규칙으로 “증류” → (4) 스캐너에 배포

4.1 Discovery: 전조 후보 자동 발굴

입력: “T0 기준 정렬된 pre-window(예: T0-30m~T0-5m)”의 시계열(가격/활동성/스프레드/임팩트 등)

출력: candidate events(서프라이즈 높은 순간) + latent embedding + cluster id

산출물(버전 고정)

cluster_centroids 또는 HDBSCAN 모델

feature_spec(윈도우 정의, 세션 규칙, 정규화 방식)

“이 후보는 어떤 패턴 그룹인지”를 알 수 있는 ID

4.2 Validation: OOS 검증 (여기서 진짜/가짜 갈림)

같은 클러스터라도 OOS에서

성공률(P(success|cluster))

lead time 분포

알림 빈도(하루 N개 제한 하에서)

실패 tail loss
를 보고 살아남는 클러스터만 채택합니다.

4.3 Distill: 운영 가능한 형태로 증류

운영(실시간 스캐너)에서 중요한 건 “최고 성능”보다:

설명 가능

디버그 가능

계산 가벼움

누수/정합성 유지
입니다.

따라서 distill 단계에서:

“클러스터 멤버십 점수 + 2~3개 게이트(Tradeability/Spread/Activity)” 형태로 압축

또는 경량 모델(XGBoost류)로 “클러스터→최종 점수”를 맵핑하고 상위 기여 피처를 노출

5) Sigma9 온라인(실시간) 이식: “MLScoringStrategy” 플러그인

Sigma9는 DI Container에 ScoringStrategy 인터페이스를 두고 전략을 주입하는 구조를 이미 가지고 있습니다. 

archt

 

archt


→ 여기에 MLScoringStrategy(또는 HybridScoringStrategy)를 추가합니다.

5.1 Online FeatureBuilder(실시간 피처 생성)

Sigma9는 이미

1초봉(A.), 틱(T.), 1분봉(AM.*) 계층 스트림이 있습니다. 

archt


따라서 Online 피처는 “윈도우 집계(5s/15s/60s)”로 증분 업데이트만 하게 설계합니다.

5.2 Model/Artifact Registry 연동

NautilusLab에서 생성된 산출물(클러스터/모델/threshold/feature_spec)을

Sigma9 서버가 주기적으로(또는 수동) 로드하여

ScoringStrategy.calculate_*()에 반영

Sigma9에는 이미 scores/ 캐시 및 R-4 산출물 저장 관례가 있으므로 그 흐름을 그대로 재사용하는 편이 안전합니다. 

archt

6) 실행/배포 방식(권장)
권장: NautilusLab는 “별도 프로세스/컨테이너”

이유 1) LGPL 리스크를 줄이기 쉬움

이유 2) 실시간 서버와 오프라인 실험이 리소스를 서로 잠식하지 않음

이유 3) 데이터/아티팩트만 공유하면 되므로 결합도가 낮음

데이터 이동(현실적인 2안)

안 A(로컬 중심): 로컬 PC가 Parquet 스냅샷을 주기적으로 rsync/다운받아 실험

안 B(서버 중심): EC2에 NautilusLab 컨테이너를 올리고, 로컬은 GUI/분석만

(사용자께서 “PC ML”을 언급하셨던 맥락이라, 기본은 안 A가 자연스럽습니다.)

7) 단계별 구현 로드맵(모듈식으로 “끊어서” 완성)
Phase 0 — 데이터 어댑터 + 단일 심볼 1m 리플레이 백테스트

수용 기준

Parquet(1m) → Nautilus Data 변환 → BacktestNode 실행 → 결과(trades/metrics) 저장

“동일 입력이면 결과가 완전 재현” (manifest로 버전 고정)

Phase 1 — 멀티심볼 + 스트리밍 로딩(대용량 최적화)

Nautilus는 대규모 적재에서 반복 정렬이 병목이 될 수 있고, 스트리밍/정렬 계약을 명시합니다.
수용 기준

100~1000 심볼 배치 실행이 메모리 폭발 없이 가능(이터레이터/청크)

Phase 2 — Discovery 파이프라인(전조 후보 발굴)

수용 기준

후보 이벤트/클러스터가 생성되고, 클러스터별 성과 분포 리포트가 자동 생성

Phase 3 — Distill + Sigma9 실시간 점수 플러그인(MLScoringStrategy)

수용 기준

실시간 스캐너가 “클러스터 멤버십 기반 알림”을 생성

알림 근거(상위 기여 피처/클러스터 ID) 로그로 추적 가능

Phase 4 — 회귀 테스트/가드레일

수용 기준

레짐별 OOS 성능이 깨지면 자동 경고(최근 N일 성능 드랍)

알림 예산(하루 N개) 강제

8) 리스크 & 대응

데이터 정합성(세션/타임스탬프/누수)

해결: feature_spec를 단일 SSOT로 버전 고정 + “event time vs ingest time” 분리

LGPL(배포/상업화)

해결: NautilusLab를 별도 서비스로 분리(IPC/파일 교환)

IB 어댑터 불안

해결: 라이브는 기존 ib_insync 유지, Nautilus는 연구/백테스트만 사용 

archt

최종 한 줄 요약

Sigma9는 “실시간 스캐너/실행”에 집중(현 구조 유지) 

archt

Nautilus는 “연구 + 백테스트 커널”만 별도 Lab로 떼어 붙임(BacktestNode/Engine)

ML은 발견→검증→증류로 “전조 정의” 없이도 운영 가능한 신호만 이식