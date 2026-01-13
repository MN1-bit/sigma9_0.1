(패치 완성본) regime_monitor_plan.v2.md
Rheograph 전략 엔진 구현 계획서

작성일: 2026-01-12 | 예상: P0 30h, P1 20h, P2 15h, V2 16h
전략명: Rheograph (유동성 흐름 기록기)
기반: r04_strategy_system_overview.md, r04-03~06

1. 목표

r04 시리즈 전략 문서에서 도출된 Liquidity Primacy Thesis를 시스템에 구현:

"개잡주 트레이딩의 본질은 '가격 예측'이 아니라, '실행 가능한 유동성 상태 전이'를 포착하는 것이다."

구현 범위
우선순위	모듈	예상 시간
🔴 P0	로그 체계, 실행 레짐 모니터, 자동 손절	30h
🟡 P1	Stage 1 스캐너, 반박 게이트 UI, 시간대 스케줄러	20h
🟢 P2	붕괴 경보, Rotation 위상 분류기	15h
🔵 V2	L2 Enhancement (Databento $199/월)	16h
2. 레이어 체크

 레이어 규칙 위반 없음 (strategies → data 방향만 사용)

 순환 의존성 없음 (ScoringStrategy 인터페이스 활용)

 DI Container 등록 필요: 예 (RheographMonitor, RotationTracker, AdversarialGate)

레이어 의존성
backend.api
    ↓
backend.core
    ↓
backend.strategies ← 신규 regime 모듈 위치
    ↓
backend.data


신규 의존성:

backend.strategies.regime → backend.data.massive_ws_client (Quote 스트림)

backend.strategies.regime → backend.models (TickData, QuoteData)

3. 변경 파일
3.1 신규 파일
파일	예상 라인	설명
backend/models/quote.py	80	QuoteData 모델 + Lee-Ready
backend/strategies/regime/__init__.py	30	패키지 초기화
backend/strategies/regime/models.py	100	Layer 1-4 데이터 모델
backend/strategies/regime/raw_metrics.py	150	Layer 1 계산기
backend/strategies/regime/derived_metrics.py	180	Layer 2 계산기 (Tick Proxy)
backend/strategies/regime/micro_state.py	150	Layer 3 FSM
backend/strategies/regime/macro_state.py	80	Layer 4 합성
backend/strategies/regime/rotation_tracker.py	120	Rotation 가속도
backend/strategies/regime/adversarial_gate.py	150	6조건 반박 게이트
backend/strategies/regime/collapse_warning.py	100	붕괴 예고 시스템
backend/strategies/regime/adaptive_stream.py	180	틱 폭발 시 1초봉 전환
backend/strategies/regime/monitor.py	200	RheographMonitor 통합
backend/core/logging/trade_logger.py	150	상태 전이 로그
frontend/gui/widgets/traffic_light.py	100	신호등 UI

총 신규: 14개 파일, ~1,770줄

3.2 수정 파일
파일	변경	설명
backend/data/massive_ws_client.py	+25	on_quote 콜백, Q채널 파싱
backend/models/__init__.py	+3	QuoteData export
backend/container.py	+20	Rheograph DI 등록
backend/startup/realtime.py	+10	핸들러 연결
4. 실행 단계
P0: 핵심 인프라 (30h)
Step 0: 로그 체계 (8h)

backend/core/logging/trade_logger.py

Stage 1/ARMED/Entry/Exit 로그 포맷

Step 1: Massive Q 채널 + Lee-Ready (2h)

backend/models/quote.py

massive_ws_client.py Q채널 파싱

Step 2: AdaptiveStreamManager (2h)

backend/strategies/regime/adaptive_stream.py

100ms 집계, 500틱/초 폭발 시 A채널 전환

Step 3: Layer 1-2 계산기 (4h)

raw_metrics.py: trade_volume, effective_spread

derived_metrics.py: tape_accel, Tick Proxy absorption

Step 4: Layer 3-4 FSM (4h)

micro_state.py: ABSORPTION, VACUUM, DISTRIBUTION, EXHAUSTION

macro_state.py: Green/Yellow/Red 합성

Step 5: Rotation Tracker (3h)

rotation_tracker.py: FUEL/TRANSITION/FATIGUE

Step 6: 자동 손절 연동 (4h)

붕괴 경보 Red → 청산 트리거

기존 IBKR trailing stop 활용

Step 7: Container 등록 (1h)

container.py: RheographMonitor 등록

Step 8: Traffic Light UI (2h)

frontend/gui/widgets/traffic_light.py

5. 기존 솔루션 검색 결과
솔루션	출처	채택 여부	사유
transitions	PyPI	✅ 채택	13상태 + 19전이, 조건부 전이, on_enter/on_exit 콜백 필요
python-statemachine	PyPI	❌ 미채택	transitions보다 기능 제한
finplot	PyPI	✅ 채택 (기존)	차트 라이브러리
transitions 채택 근거

FSM 복잡도 분석:

FSM	상태 수	전이 규칙	복잡도
MicroState	6	~10개	복합 조건 (AND/OR)
Rotation	3	4개	지속 시간 조건
Entry Stage 2	4	5개	Timeout, Half-Life
총합	13상태	~19전이	entry/exit 콜백 필수

transitions 장점:

선언적 전이 정의 (딕셔너리)

자동 콜백 on_enter_STATE / on_exit_STATE

조건부 전이 conditions=

상태 다이어그램 자동 생성

히스테리시스 구현 용이

6. 데이터 요구 (r04-05/06 결론)
데이터	MVP 해결책	V2 (L2)
trade	Massive T (기존)	-
NBBO	Massive Q 추가	-
trade_side	Lee-Ready 추론 (85-90%)	-
absorption	Tick Proxy	L2 기반
Float	yfinance (분기별)	SEC Edgar
7. 핵심 로직 요약 (r04-04)
7.1 4계층 상태 인식
Layer 4: 🟢Green │ 🟡Yellow │ 🔴Red
Layer 3: ABSORPTION │ VACUUM │ DISTRIBUTION │ EXHAUSTION
Layer 2: tape_accel │ trade_imbalance │ absorption_ratio
Layer 1: trade_volume │ effective_spread │ VWAP

7.2 Stage 2 Entry FSM
IDLE → [구조 충족] → ARMED → [테이프 트리거] → TRIGGERED
                        ↓ [Timeout = min(15분, half_life×0.3)]
                      IDLE

7.3 반박 게이트 6조건
조건	위반 시
시간대 (11:30-14:00)	🔴 봉쇄
Rotation FATIGUE	🟡 경고
촉매 없음	🔴 봉쇄
실행 레짐 Red	🔴 봉쇄
일일 손실 80%	🟡 사이즈 50%
붕괴 경보	🟡 경고
8. Verification Plan
8.1 단위 테스트
pytest tests/strategies/regime/ -v --tb=short

8.2 통합 테스트
pytest tests/integration/test_rheograph_pipeline.py -v

8.3 수동 검증

급등 종목 → 🟢 Green

횡보 종목 → 🟡 Yellow

급락 종목 → 🔴 Red

붕괴 경보 Red → 즉시 청산

9. 참조 문서
문서	역할
r04_strategy_system_overview.md	시스템 오버뷰
r04-04-strategy-architecture.md	아키텍처 상세
r04-03.md	QTS 피드백, Rotation 가속도
r04-05-data-vendor-discussion.md	밴더 선정
r04-06-L2-alpha-discussion.md	L2 MVP/V2 결정
10. 비기능 요구사항 (NFR) / 성능 예산 (추가)

샘플링 권장: 100~500ms (내부 집계/계산), 상태 히스테리시스 0.5~2초 (상태 튐 방지)

E2E 지연 목표(경보→청산 트리거): <100ms 수준 (이벤트 기반 연결)

데이터 트레이드오프:

MVP는 effective_spread(체결 기반) 중심으로 “실행 레짐”을 판정 (스푸핑 내성)

absorption_ratio 정교화는 L2(리필 속도 등)가 필요할 수 있으므로, MVP는 Tick Proxy로 시작하고 V2에서 강화

11. Policy/Threshold 설정 구조 (추가)

임계값/허용 시간대/필터 스트릭트니스를 Policy 객체로 캡슐화하여 런타임 교체 가능하게 설계

레짐 분류기 도입 시: “세션 시작 시 정책 선택”과 “자동 정책 전환”을 모두 지원 (둘 다 필요)

12. 로그 스키마 (최소 필드) (추가)
시점	기록 항목
Stage 1 통과	모든 필터 조건 값, 타임스탬프
ARMED 진입	촉매 유형, Half-Life 추정, Timeout
ARMED 종료	종료 사유 (Timeout/Trigger/Red 전환)
Entry	실행 레짐 스냅샷, Stage 2 트리거 조건
Exit	청산 사유, P&L, 붕괴 경보 여부

운영 중에는 “게이트 통과 vs 차단”의 성과 비교가 필수입니다. (막기만 잘하면 수익도 0이 될 수 있음)

13. 이벤트/메시지 설계 (Pub/Sub) (추가)

상태 계산 모듈들은 서로 느슨하게 결합(독립 계산)하고, 합성은 이벤트로 처리

권장 이벤트 스트림:

regime.micro_state.changed

regime.macro_state.changed

regime.rotation_state.changed

regime.collapse_warning.raised (Yellow/Red)

gate.decision (AllClear/Warning/Blocked)

붕괴 경보는 Rotation Accel 스트림과 Execution Regime 스트림을 별도 계산 후, CEP(Complex Event Processing)로 “원인+증상”을 합성하는 구조를 권장

14. 운영/검증 지표 (추가)

상태 분포: 종목/세션별 Green·Yellow·Red 체류 시간

전이 품질: 상태 튐(초당 전이 횟수), 히스테리시스 효과

게이트 효용: Blocked로 막은 케이스 vs AllClear 진입 케이스의 사후 성과(P&L, MFE/MAE)

경보 효용: 경보 Red 발생 후 실제 붕괴(슬리피지 확대/하락) 재현율 + 미탐 케이스 로그

15. P3+ 로드맵 메모 (추가)

Half-Life 추정기: 촉매 유형별 경험적 분포 수집 + 초기 반응 강도로 동적 보정 필요

레짐 분류기: “장 시작 전 예측 분류” + “일중 레짐 전환 감지” 모두 필요

QCA 룰 최적화: 룰 생성기가 아니라 룰 최소화기로 활용 (필요조건 AND / 충분조건 OR)

작성일: 2026-01-12
버전: v3.1 (IMP-planning 준수)