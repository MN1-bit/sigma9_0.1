(패치 완성본) r04_strategy_system_overview.md
r04 전략 시스템 오버뷰 v1.1

작성일: 2026-01-12 | 기반: 17개 전략 문서 종합
핵심 원리: 유동성 우선성 (Liquidity Primacy Thesis)

1. 핵심 철학

**타겟**: 마이크로캡/스몰캡($50M~$500M 시총)에서 **급등 신호가 발생한 종목**

### 1.0.1 2트랙 전략 구조

| 구분 | **Early Bird** | **Pullback Sniper** |
|------|---------------|---------------------|
| **철학** | 급등주를 조기에 잡는다 | 첫 눌림목에서 진입 |
| **타이밍** | 9:30~9:45 | 10:00~11:00, 14:00 이후 |
| **스캐너** | Gap + 실시간 RVOL | 누적 RVOL + 조정률 |
| **촉매** | 필수 (Tier 1-2) | 선택적 (Tier 3 허용) |
| **플레이북** | Gap&Go, Halt | VWAP Reclaim, First Pullback |
| **기대 승률** | 30-40% | 50-60% |
| **기대 R/R** | 1:3+ | 1:1.5 |

> **전략 선택 기준**: 동일 종목에서 Early 놓치면 Pullback으로 전환. 둘 다 시도 시 기회비용 충돌.

"개잡주 트레이딩의 본질은 '가격 예측'이 아니라, '실행 가능한 유동성 상태 전이'를 포착하는 것이다."

기존 사고	새로운 사고
엣지 = 예측	엣지 = 필터링 + 손실 구조 설계
모델이 맞추는가?	틀렸을 때 비용 구조는?
언제 진입하나?	언제 진입하지 말아야 하나?

### 1.1 엣지의 계층 구조

**수익 기대 논리 (Edge Rationale)**:
> 마이크로캡 급등주에는 **정보 비대칭**과 **유동성 불균형**이 발생합니다.  
> - 대부분의 참가자는 뉴스나 촉매에 **늦게 반응**하고, 또는 **감정적으로 과반응**합니다.  
> - 우리의 엣지는 ① 이 반응 타이밍 차이와, ② 유동성 상태(흡수/진공/분배)의 전이를 **구조적으로 필터링**하여, **정보 우위 없이도 비용 비대칭(작은 손실, 큰 이득)**을 확보하는 것입니다.  
> - 예측이 아닌, **"진입하지 말아야 할 때"를 거르는 능력**과 **손실 구조 설계**가 기대수익(EV)을 좌우합니다.

**실제 매매 흐름 (Practical Workflow)**:

| 단계 | 행동 | 해설 |
|------|------|------|
| ① 스캔 | **Dollar Float<$100M** + RVOL>3x + Gap>20% + 촉매 | "경기장 선택" - 달러 기준 유동성 필터링 |
| ② 워치리스트 | Frontside 여부, 희석 체크, Half-Life 추정 | "함정 제외" - ATM/희석 종목, Backside 제외 |
| ③ ARMED→진입 | 공통조건(스프레드+레짐) + **플레이북 트리거** | "4.4 플레이북 상세" - 각 플레이북별 진입조건 직접 적용 |
| ④ 포지션 FSM | **HOLDING↔SCALING↔EXITING→FLAT** | "상태 기반 관리" - 아래 FSM 참조 |

**④ 포지션 FSM 상태**:
| 상태 | 의미 | 전이 조건 |
|------|------|----------|
| **HOLDING** | 기본 보유 | 진입 완료, 모니터링 중 |
| **SCALING_OUT** | 분할 익절/손절 | 목표 도달 / 경고 신호 |
| **SCALING_IN** | 추가 매수 | 확인 신호 + Q_max 여유 |
| **EXITING** | 전량 청산 ⚠️ | 손절선/붕괴경보 Red (최우선) |
| **FLAT** | 포지션 없음 | 청산 완료 → 재진입 대기 |

> **핵심 해설**:  
> - **스캔~워치리스트**는 "승률을 높이는 게 아니라, 패배 확률이 높은 경기장을 **제외**"하는 단계입니다.  
> - **ARMED→진입**은 "예측하지 않고, 시장이 **먼저 움직인 후** 따라가는" 확인 매매입니다.  
> - **포지션 FSM**은 "맞으면 크게(SCALING_OUT), 틀리면 작게(EXITING) 잃는 **비용 비대칭**"을 상태로 강제합니다.  
> - **EXITING은 최우선** - 다른 상태에서 언제든 전이 가능, 역전이 불가

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
│  [공통조건] ─→ ARMED ─→ [플레이북 트리거] ─→ IN_POSITION           │
│       ↓           │                                             │
│  스프레드 안정   Timeout                                        │
│  실행레짐 Green  Half-Life×0.3                                   │
│       ↓           ↓                                             │
│       └─────────→ IDLE                                          │
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

### 3.0.1 기본 필터
| 필터 | 임계값 | 데이터 소스 |
|------|--------|------------|
| **Dollar Float** | Price × Float < **$50M~$100M** | yfinance (price), SEC Edgar (float) |
| **RVOL** | > 3x (5분 분봉 기준) | 자체 계산 |
| **Catalyst** | Tier 1-3 (아래 참조) | News API |
| ATM Offering | 없음 | SEC filings |

### 3.0.2 RVOL 정의 (명확화)
| RVOL 유형 | 계산 | 적용 전략 |
|----------|------|------------|
| **실시간 RVOL** | 현재 5분 거래량 / 20일 평균 5분 거래량 | Early Bird |
| **누적 RVOL** | 당일 누적 / 20일 평균 | Pullback |

### 3.0.3 촉매 티어링
| Tier | 유형 | 예시 | 사이즈 배수 |
|------|------|------|------------|
| **Tier 1** | 확정된 강력 촉매 | FDA 승인, 계약 체결, 인수합병 | 100% |
| **Tier 2** | 추정 촉매 | 테마 편승, 섹터 모멘텀, 루머 | 50% |
| **Tier 3** | 불명/없음 | 기술적 브레이크아웃, 숙스퀘즈 | Early 봉쇄, Pullback만 허용 |

> **Dollar Float 선택 근거**: 시장 참가자는 "주식 수"가 아니라 "달러 금액"으로 거래합니다.

출력: WATCHLIST 등록 + 메타데이터 (Float, RVOL, Catalyst Tier, Half-Life 추정, 전략 타입)

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
IDLE → [공통조건 충족] → ARMED → [플레이북 트리거] → IN_POSITION
                         ↓ [Timeout 또는 Red 전환]
                       IDLE (기회 소멸)

4.2 ARMED 진입 조건 (공통)

**공통 조건** (모든 플레이북 적용):
| 조건 | 판정 기준 | 비고 |
|------|----------|------|
| 스프레드 안정 | effective_spread ≤ baseline | 유동성 확보 |
| 실행 레짐 | 🟢 Green 또는 🟡 Yellow | 🔴 Red 시 봉쇄 |
| 체결 가속 | tape_accel > 0 (선택) | 모멘텀 확인 |

**플레이북별 조건** (4.4 상세 참조):
| 플레이북 유형 | 진입 조건 |
|--------------|----------|
| Momentum (HOD Break, Gap&Go, Halt) | VWAP 상방 + 레벨 돌파 |
| Reclaim (VWAP Reclaim) | VWAP 하방→상방 돌파 |
| Pullback (Bull Flag) | 조정 후 이전 고점 돌파 |
| Reversal (Washout) | 지지선 + 반전 캔들 |
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

### MVP 핵심 6 플레이북

#### 1️⃣ VWAP Reclaim (VWAP 탈환)
| 항목 | 내용 |
|------|------|
| **상황** | 갭업 후 하락하여 VWAP 아래로 빠졌다가 다시 VWAP 위로 복귀 |
| **진입 조건** | VWAP 상향 돌파 + 거래량 급증 + 스프레드 축소 |
| **논리** | VWAP 아래에서 숏/손절 물량 소화 후, 매수세 우위 전환 확인. "약한 손" 청산 완료 후 재상승 |
| **손절** | VWAP 재이탈 시 즉시 (2-3% 또는 VWAP 하단) |
| **목표** | HOD 재도전 또는 확장 시 1.5~2R |

#### 2️⃣ HOD Break (고가 돌파)
| 항목 | 내용 |
|------|------|
| **상황** | 당일 고점(HOD) 근처에서 압축 후 돌파 시도 |
| **진입 조건** | ① 가격 압축(좁은 레인지) + ② 스프레드 축소(유동성 개선) + ③ 체결 가속(tape_accel>0) **"3요소 동시충족"** |
| **논리** | HOD 위 손절 물량(숏커버+브레이크아웃 매수) 트리거 → 유동성 진공 상태에서 급등 |
| **손절** | HOD 재이탈 또는 직전 압축 저점 (좁게 설정) |
| **목표** | 모멘텀 지속 시 트레일링, 1.5~3R |

#### 3️⃣ First Pullback / Bull Flag (첫 눌림목)
| 항목 | 내용 |
|------|------|
| **상황** | 강한 첫 파동 후 첫 번째 조정(깃발/눌림목 형성) |
| **진입 조건** | 조정폭 < 50% 되돌림 + 거래량 감소(건전한 조정) + 이전 고점 돌파 시 |
| **논리** | 첫 조정은 이익실현 매물 소화 구간. 매도세 소진 후 다음 레그 시작 |
| **손절** | 조정 저점 이탈 또는 VWAP 이탈 |
| **목표** | 첫 파동 길이만큼 확장 (측정 목표) |

#### 4️⃣ Gap & Go / ORB / PMH 돌파
| 항목 | 내용 |
|------|------|
| **상황** | 장전 갭업 + 프리마켓 고점(PMH) 또는 시초가 레인지(ORB) 돌파 |
| **진입 조건** | 9:30~10:00 내 PMH/ORB 상향 돌파 + 거래량 폭발 + VWAP 상방 유지 |
| **논리** | 장 초반 유동성 최대 구간에서 모멘텀 형성. 프리마켓 참가자 수익 실현 소화 후 신규 매수세 유입 |
| **손절** | VWAP 이탈 또는 ORB 하단 |
| **목표** | 장 초반 모멘텀 극대화, 1.5~2R 빠른 익절 또는 트레일링 |

#### 5️⃣ Halt Reopen (LULD 정지 후 재개)
| 항목 | 내용 |
|------|------|
| **상황** | 급등으로 LULD 서킷브레이커 발동 후 거래 재개 |
| **진입 조건** | 재개 후 첫 1분 캔들 고점 돌파 + 거래량 지속 + 추가 정지 가능성 인지 |
| **논리** | 정지 중 누적된 매수 주문이 재개 시 폭발. 단, 재개 직후 방향 확인 필수 (하방 재개 시 봉쇄) |
| **손절** | 재개 캔들 저점 이탈 즉시 (매우 타이트) |
| **목표** | 추가 정지 발생 시 홀딩, 1~2R 빠른 스캘핑 |
| **주의** | ⚠️ 고위험 - 사이즈 50% 축소, 슬리피지 예상 2배 |

#### 6️⃣ Washout Reversal (세척 반전)
| 항목 | 내용 |
|------|------|
| **상황** | 급등 후 급락(패닉 세척)하여 지지선까지 하락 후 반전 |
| **진입 조건** | VWAP 또는 주요 지지 터치 + 거래량 스파이크(capitulation) + 반전 캔들 확인 |
| **논리** | 과매도 후 "약한 손" 완전 청산. 손절 물량 소진 시점에서 저가 매수세 유입 |
| **손절** | 지지선 이탈 시 즉시 (세척이 아니라 붕괴) |
| **목표** | VWAP 또는 이전 고점 재도전, 1.5~2R |
| **주의** | ⚠️ 역추세 - 확인 후 진입, Frontside에서만 시도 |

---

### 확장 카드 (필요 시)

| 플레이북 | 간략 설명 |
|----------|-----------|
| PDHB (전일 고가 돌파) | 멀티데이 모멘텀, 당일 촉매 없어도 기술적 돌파 |
| HOD Absorption | HOD에서 대량 매도 흡수 후 돌파 (L2 필요) |
| FRD Bounce | 첫 빨간 날(First Red Day) 반등, 멀티데이 |
| SSR Play | 공매도 제한(SSR) 발동일 숏커버 유도 |

> **⚠️ 별도 격리 권장**: Short Squeeze, Parabolic Peak Reversal(숏) 등은 리스크 프로파일이 다르므로 별도 모듈로 분리

5. 4계층 실행 레짐 모니터
Layer 1: 원시 지표
지표	계산	데이터
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

10.5 MaxCap Sizing System (사이즈 결정 로직)

**핵심 원칙: Exit-First, No-Impact**

> "내가 원할 때 나갈 수 있는 만큼만 들어간다"

청산 가능 물량이 진입 물량의 상한입니다.

**10.5.1 No-Impact 정의**

1. 슬리피지 예산 내 체결: 진입 12 bps, 청산 10 bps 이하
2. 시장 참여율 제한: 전체 거래량의 일정 비율 이하
3. 플로트 점유 제한: 유통 주식의 0.2% 이하

**10.5.2 모듈 구조**

```
┌─────────────────────────────────────────────────┐
│  ┌─────────────┐         ┌─────────────────┐   │
│  │ SizingModule│ ◄─────► │  SizingMonitor  │   │
│  │ (결정)      │         │  (모니터링)      │   │
│  └─────────────┘         └─────────────────┘   │
└─────────────────────────────────────────────────┘
```

| 모듈 | 역할 | 호출 시점 | 출력 |
|------|------|----------|------|
| SizingModule | Q_max 결정 | 진입/추가매수 신호 시 | 주수 |
| SizingMonitor | 리스크 모니터링 | 매분~5초 | 🟢🟡🟠🔴 |

**10.5.3 핵심 계산 흐름**

1. 유동성 속도 (L): EMA로 "1초에 얼마나 거래되나" 추정
2. 마찰 계수 (κ): κ = max(100, 4 × spread_bps)
3. 예상 거래량: V_in = L × 4초, V_out = L × 2초 × 0.4
4. 최대 금액: Q = V × (B/κ)² (Square-root law 역산)
5. 최종: Q_max = min(Q_in, Q_out, Q_float_cap)

**10.5.4 하드 게이트 (즉시 봉쇄)**

| 조건 | 임계값 | 결과 |
|------|--------|------|
| spread > HARD_MAX | 200 bps | Q=0 |
| L < L_MIN | $100/s | Q=0 |
| Q < Q_MIN | 100주 | Q=0 |

**10.5.5 시간대 배수 (ToD Multiplier)**

| 시간대 | 배수 | 비고 |
|--------|------|------|
| 장전 (PRE) | 0.3 | 유동성 적음 |
| 개장 (OPN) | 1.3 | 유동성 폭발 |
| 오전 (MID1) | 1.0 | 기준 |
| 점심 (DEAD) | 0.5 | 데드존 |
| 오후 (MID2) | 0.8 | 조금 적음 |
| 마감 (CLO) | 1.2 | 유동성 증가 |
| 장후 (AH) | 0.2 | 매우 적음 |

**10.5.6 호출 규칙**

- 첫 진입: calculate_max_size(current_position=0)
- 추가매수: calculate_max_size(current_position=기존분)
- 보유 중: **재호출 금지** (기존 Q 유지)
- 청산: SizingModule 호출 안 함 (ExitModule 담당)

**10.5.7 SizingMonitor 리스크 레벨**

| 비율 (보유/Q_max) | 레벨 | 주기 |
|-------------------|------|------|
| < 100% | 🟢 정상 | 1분 |
| 100~150% | 🟡 주의 | 30초 |
| 150~200% | 🟠 경고 | 10초 |
| > 200% | 🔴 위험 | 5초 |

**자동 청산 없음** - 경고만 표시, 사용자가 결정

**10.5.8 파라미터 (config)**

```
TAU_IN = 4s, TAU_OUT = 2s
B_IN = 12 bps, B_OUT = 10 bps
KAPPA_FLOOR = 100 bps, K_SPR = 4
PANIC_DISCOUNT = 0.4
PHI = 0.002 (Float 0.2%)
```

**10.5.9 캘리브레이션 (주간)**

- κ: slippage_bps / √(Q/V)의 80분위수로 상향
- panic_discount: 실제 청산 유동성 / 예상 유동성의 30분위수

자세한 명세: `maxcap_module/maxcap_sizing_system_overview.md`

11. 구현 우선순위
우선순위	모듈
🔴 P0	로그 체계 (상태 전이 기록)
🔴 P0	실행 레짐 모니터
🔴 P0	자동 손절 시스템
� P0	SizingModule (MaxCap 사이즈 결정)
�🟡 P1	반박 게이트 UI (신호등)
🟡 P1	시간대 스케줄러 (임계값 스케줄링)
🟡 P1	Stage 1 스캐너 (Float/RVOL/Gap/Catalyst/Dilution)
🟡 P1	SizingMonitor (리스크 레벨 표시)
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
Sizing 호출	spread_bps, L, κ, Q_max, 게이트 결과
Entry	실행 레짐 스냅샷, Stage 2 트리거 조건, 체결 수량
Exit	청산 사유, P&L, 붕괴 경보 여부, 슬리피지
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
L0	maxcap_module/*	MaxCap Sizing 명세 (127턴 토론)
L1	r04-05	데이터 밴더 선정
L1	r04-06	L2 알파 토론
L2	r04-02	방법론 토론
L2	r04-01	50턴 토론
L3	r03-*	전략 융합
L3	r02-*	플레이북 비교
L4	anth/cgpt/gem/perp	원본 플레이북

작성일: 2026-01-14 (최종 수정)
버전: v1.2 (MaxCap Sizing 추가)

