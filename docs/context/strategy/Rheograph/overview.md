(패치 완성본) r04_strategy_system_overview.md
r04 전략 시스템 오버뷰 v1.1

작성일: 2026-01-12 | 기반: 17개 전략 문서 종합
핵심 원리: 유동성 우선성 (Liquidity Primacy Thesis)

1. 핵심 철학

"개잡주 트레이딩의 본질은 '가격 예측'이 아니라, '실행 가능한 유동성 상태 전이'를 포착하는 것이다."

기존 사고	새로운 사고
엣지 = 예측	엣지 = 필터링 + 손실 구조 설계
모델이 맞추는가?	틀렸을 때 비용 구조는?
언제 진입하나?	언제 진입하지 말아야 하나?
1.1 엣지의 계층 구조 (추가)

1차 엣지(차별화 영역): 실행/적응 (속도, 비용, 심리 통제, 적응 속도)

2차 엣지(공유 지식 영역): 패턴/플레이북 (VWAP Reclaim, HOD Break, Halt 등)

시스템은 2차 엣지를 “상태/게이트/로그”로 재현 가능하게 만들고, 1차 엣지는 **비용·규율·학습(로그)**로 강화합니다.

2. 전체 시스템 아키텍처
┌─────────────────────────────────────────────────────────────────┐
│                     STAGE 1: Universe Filtering                 │
│  [Float < 20M] + [RVOL > 3x] + [Catalyst 있음] + [¬ATM]         │
│                           ↓                                     │
│                      WATCHLIST 등록                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     STAGE 2: Entry Timing                       │
│                                                                 │
│  [구조 조건] ─→ ARMED ─→ [테이프 트리거] ─→ TRIGGERED           │
│       ↓           │              ↓                              │
│  VWAP 상방      Timeout        체결 가속                        │
│  스프레드 축소  Half-Life×0.3  스프레드↓                        │
│  레벨 돌파        ↓                                             │
│                 IDLE                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   4계층 실행 레짐 모니터                         │
│                                                                 │
│  Layer 4: 매크로 상태 ─→ 🟢Green │ 🟡Yellow │ 🔴Red             │
│  Layer 3: 마이크로 상태 ─→ ABSORPTION │ VACUUM │ DISTRIBUTION   │
│  Layer 2: 파생 지표 ─→ tape_accel │ trade_imbalance │ absorption│
│  Layer 1: 원시 지표 ─→ trade_volume │ effective_spread │ VWAP   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   반박 게이트 (Adversarial Gate)                 │
│                                                                 │
│  [시간대] ─→ Dead Zone (11:30-14:00)?          → 🔴 봉쇄        │
│  [Rotation] ─→ FATIGUE 상태?                   → 🟡 경고        │
│  [Half-Life] ─→ 촉매 없음/원인 불명?           → 🔴 봉쇄        │
│  [실행 레짐] ─→ Red 상태?                      → 🔴 봉쇄        │
│  [일일 손실] ─→ 80% 도달?                      → 🟡 사이즈 50%  │
│  [붕괴 경보] ─→ Yellow 이상?                   → 🟡 경고        │
│                           ↓                                     │
│              🟢 All Clear │ 🟡 Warning │ 🔴 Blocked             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      진입/청산 실행                              │
│                                                                 │
│  [🟢 All Clear] ─→ 표준 진입                                    │
│  [🟡 Warning] ─→ 사이즈 축소 or 재검토                          │
│  [🔴 Blocked] ─→ 진입 불가                                      │
│                                                                 │
│  [붕괴 경보 Red] ─→ 즉시 청산 트리거                            │
└─────────────────────────────────────────────────────────────────┘

3. Stage 1: Universe Filtering
필터	임계값	데이터 소스
Float	< 10-20M (정책별)	SEC Edgar, yfinance
RVOL	> 3-5x	자체 계산
Catalyst	존재	News API
ATM Offering	없음	SEC filings

출력: WATCHLIST 등록 + 메타데이터 (Float, RVOL, Catalyst 유형, Half-Life 추정)

3.1 권장 보강 필터 (Scanner 프리셋)

Stage 1은 “예측”이 아니라, 거래 가능한 경기장만 남기는 필터링입니다.

Gap%: ≥ 20% (기본 프리셋)

Price Range: $2~$10 (특히 $3~$8 구간을 우선)

구조 태그: Frontside/Backside (Backside는 신규 롱을 원칙적으로 차단)

Short Interest(선택): 20~50%는 증폭, 50%+는 과열(함정 가능)로 간주

발굴용 입력(선택): 데이게이너 리스트, 섹터 모멘텀

3.2 Dilution 체크 범위 확장 (권장)

Stage 1의 ¬ATM은 최소조건이며, 실제 운영에서는 희석/공급 증가 이벤트를 더 넓게 잡는 것을 권장합니다.

ATM Offering / Shelf(S-3) 효력 / Offering(증자)

전환/워런트/연속 공시 등 “공급 증가” 성격 이벤트(탐지 시: 사이즈 축소 또는 거래 봉쇄)

3.3 데이터 Tier (운영/확장용)

Tier 1 (필수): Level 2/Order Book, Time&Sales(Tape), VWAP, OHLCV, 실시간 거래량

Tier 2 (엣지 강화): 뉴스·Catalyst, Short Interest, 섹터 모멘텀, Float Rotation, Options Flow, 희석 이벤트 탐지, RelVol

Tier 3 (고급/선택): SEC Filings, ATM 조항, MMID, FTD, Dark Pool Prints, Social Sentiment, 슬리피지 프로파일

3.4 Stage 1 출력 메타데이터 (로그/학습 최소셋)

float, rvol, gap%, price, catalyst_type, half_life_est, short_interest(선택), policy_name

목적: “어떤 필터가 언제/왜 망가졌는지”를 사후 학습 가능하게 만들기 위함

4. Stage 2: Entry Timing
4.0 Context(경기장) 지정: HTF → LTF + Frontside/Backside

HTF 레벨(경기장): 전일 고저/시가, 프리마켓 고저, VWAP 같은 “큰 레벨” 안에서만 LTF 트리거를 탐색합니다.

태깅(운영 제한): Frontside/Backside, 랭킹 이탈, 거래대금 고갈 등으로 ‘자리’를 제한하면 카드 수가 많아도 실행은 제한되고 과최적화 위험이 줄어듭니다.

기본 룰: Backside에서는 신규 롱을 원칙적으로 차단(필요 시, 별도 리버설/숏 모듈로 분리).

4.1 ARMED 상태 FSM
IDLE → [구조 충족] → ARMED → [테이프 트리거] → TRIGGERED → IN_POSITION
                        ↓ [Timeout 또는 Red 전환]
                      IDLE (기회 소멸)

4.2 ARMED 진입 조건
조건	판정 기준
VWAP 상방	price > VWAP
체결 가속	tape_accel > 0
스프레드 안정	effective_spread ≤ baseline
레벨 돌파	price > HOD or PMH
4.3 Half-Life 기반 Timeout
촉매 유형	Half-Life	Timeout	트레일링 강도
FDA 승인	수 시간	30분	느슨
계약 발표	1-3시간	15분	중간
테마 편승	30분-1시간	5분	공격적
원인 불명	수 분	1분	극공격/봉쇄

공식화(권장):

ARMED_Timeout = min(15분, half_life × 0.3)

Trailing_Strength = f(half_life) (Half-Life가 길수록 트레일링을 느슨하게)

Entry_Size = base_size × half_life_score

Half-Life는 “뉴스 텍스트”만으로 고정하기보다, 초기 시장 반응 강도로 동적으로 보정할 수 있어야 합니다.

4.4 플레이북 라이브러리 (MVP 6 + 확장)

MVP(권장 6)

VWAP Reclaim

HOD Break (압축 + 유동성 개선 + 체결 가속 “3요소” 동시충족)

First Pullback / Bull Flag

Gap & Go / ORB / PMH 돌파

Halt Reopen (LULD)

Washout Reversal (고점 피크·급락 후 반전)

확장 카드(필요 시)

PDHB(전일 고가 돌파), HOD Absorption, FRD Bounce(멀티데이), SSR Play

Short Squeeze, Parabolic Peak Reversal(숏) 등은 별도 리스크 프로파일로 격리 권장

5. 4계층 실행 레짐 모니터
Layer 1: 원시 지표
지표	계산	데이터
trade_volume	Σ(size) / Δt	Time & Sales
effective_spread	2 ×	price - mid
bid/ask_volume	방향별 체결량	T&S + Lee-Ready
Layer 2: 파생 지표
지표	계산	의미
tape_accel	d(velocity)/dt	체결 가속도
trade_imbalance	(bid-ask)/total	방향 불균형
absorption_ratio	Tick Proxy (MVP)	흡수 효율
rotation_velocity	d(cumVol/Float)/dt	Float 회전 속도
rotation_accel	d(velocity)/dt	회전 가속도
Layer 3: 마이크로 상태
상태	조건	의미
ABSORPTION	대량체결 + 가격유지	받아주고 있음
VACUUM	tape_accel↑ + ask↓	유동성 고갈
DISTRIBUTION	imbalance < -0.3	분배 중
EXHAUSTION	tape_accel↓ + spread↑	소진
Layer 4: 매크로 상태
상태	합성 조건	행동
🟢 Green	ABSORPTION ∨ VACUUM	진입 허용
🟡 Yellow	DISTRIBUTION ∨ EXHAUSTION	진입 주의
🔴 Red	PANIC ∨ spread > critical	진입 차단

합성 로직(권장 형태):

🟢 Green: (ABSORPTION OR VACUUM) AND NOT (DISTRIBUTION OR EXHAUSTION)

🟡 Yellow: DISTRIBUTION OR EXHAUSTION

🔴 Red: PANIC OR spread > critical

구현 요점(권장):

샘플링: 100~500ms

히스테리시스: 0.5~2초 (상태 튐 방지)

“호가 스냅샷”보다 **effective_spread(체결 기반)**을 우선(스푸핑 내성).
단, absorption_ratio의 정교화는 L2(리필 속도 등)가 필요할 수 있으므로 MVP는 Tick Proxy로 시작합니다.

6. Rotation 가속도 기반 상태 (r04-03)
상태	조건	의미
FUEL	accel > +θ	회전 가속, 연료 상태
TRANSITION		accel
FATIGUE	accel < -θ (N초 지속)	회전 둔화, 피로
7. 붕괴 예고 시스템 (Collapse Warning)
[원인] rotation_accel < 0 (FATIGUE)
  AND
[증상] spread↑ OR tape_accel < 0 (실행 레짐 악화)
  →
⚠️ "분배/덤프 임박" 경보

경보	조건	행동
⚠️ Yellow	원인 OR 증상	신규 진입 금지
🔴 Red	원인 AND 증상	즉시 청산

운영 노트(추가):

원인+증상 AND는 Precision을 올리지만 Recall이 떨어질 수 있으므로, 미탐(경보 미발생 붕괴) 케이스를 별도로 로깅/리뷰합니다.

경보는 늦으면 의미가 줄어드므로, “경보 발생 → 청산 모듈 반응”을 **이벤트 기반(Pub/Sub + CEP 합성)**으로 설계하고, end-to-end 지연 목표를 <100ms 수준으로 둡니다.

8. Moderators (효과 조절자)
Moderator	효과 증폭	효과 반전
시간대	09:30-10:30	11:30-14:00 Dead Zone
Rotation	FUEL 상태	FATIGUE 상태
Short Interest	20-50%	50%+ (과열)
Half-Life	강한 촉매	원인 불명
9. 공격성 동적 조절 (Regime-Based)
9.1 시장 레짐
레짐	지표	공격성
Bull	데이게이너 다수	1.5x
Neutral	혼조	1.0x
Chop	휩소 빈발	0.5x
Bear	데이루저 우세	0.3x
9.2 정책 분리
정책	Float	리버설	오버나잇
Aggressive	20M	허용	선택적
Standard	10M	금지	금지
Conservative	5M	금지	금지
10. 손실 구조 설계

"모델이 맞추는가 아니라, 틀렸을 때 비용 구조가 핵심"

자동 손절 시스템 필수 (심리적으로 안 지켜짐)

Half-Kelly 또는 1/4 Kelly 사이징

일일 손실 한도 80% 도달 시 사이즈 50% 감소

(권장) 트레이드당 리스크: 0.5~1R

(권장) 스케일 인 규칙: 추가 진입을 하더라도 “총 R”이 1R을 넘지 않게 유지

(권장) 연속 손절 제어: 동일 패턴에서 연속 3회 손절 시, 해당 패턴은 당일 중지

(권장) 데일리 스탑(하드스탑): -3R(또는 -3%) 도달 시 당일 거래 중단

절대 금지(운영 규칙): 물타기(Averaging Down) / 손절 라인 불명확 진입

11. 구현 우선순위
우선순위	모듈
🔴 P0	로그 체계 (상태 전이 기록)
🔴 P0	실행 레짐 모니터
🔴 P0	자동 손절 시스템
🟡 P1	반박 게이트 UI (신호등)
🟡 P1	시간대 스케줄러 (임계값 스케줄링)
🟡 P1	Stage 1 스캐너 (Float/RVOL/Gap/Catalyst/Dilution)
🟢 P2	붕괴 경보 시스템 (원인+증상 AND)
🟢 P2	Rotation 위상 분류기 (가속도)
🟢 P2	레짐 분류기 (공격성 배수/Policy 자동 전환)
🔵 P3	Half-Life 추정기 (촉매 분류 → 시간 정책)
🔵 P3	QCA 기반 룰 최적화 (룰 최소화기)
11.1 로그 필수 항목 (최소)
시점	기록 항목
Stage 1 통과	모든 필터 조건 값, 타임스탬프
ARMED 진입	촉매 유형, Half-Life 추정, Timeout
ARMED 종료	종료 사유 (Timeout/Trigger/Red 전환)
Entry	실행 레짐 스냅샷, Stage 2 트리거 조건
Exit	청산 사유, P&L, 붕괴 경보 여부
12. MVP 데이터 요구 (r04-05/06 결론)
데이터	MVP 해결책	V2 (L2 추가)
trade	Massive T	-
NBBO	Massive Q	-
trade_side	Lee-Ready (85-90%)	-
absorption	Tick Proxy	L2 기반
Float	yfinance (분기별)	SEC Edgar
Catalyst	News API	NLP/분류 ML
Adaptive Order	❌	L2 → 최적가
Dynamic Exit	❌	L2 → 저항 확인
13. 참조 문서 계층
레벨	문서	내용
L0	r04-04	시스템 아키텍처
L0	r04-03	QTS 피드백 통합
L1	r04-05	데이터 밴더 선정
L1	r04-06	L2 알파 토론
L2	r04-02	방법론 토론
L2	r04-01	50턴 토론
L3	r03-*	전략 융합
L3	r02-*	플레이북 비교
L4	anth/cgpt/gem/perp	원본 플레이북

작성일: 2026-01-12
버전: v1.1

