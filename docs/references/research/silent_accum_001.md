### 1번 의견:

0) 큰 원리: “흡수(Absorption) + 누적(Accumulation) + 은폐(Execution Style) + 검증(Confirmation)”

매집은 보통 아래 4가지가 함께 나타날 때 강해집니다.

흡수: 팔리는 물량이 있는데도 가격이 무너지지 않는다

누적: 시간이 지날수록 매수 우위가 누적된다(자금흐름 지표가 선행)

은폐: VWAP 주변, 장중 고르게, 마감/옥션 등 “기관 스타일”로 집행된다

검증: 옵션/숏/오프익스체인지/공시(지연) 등이 같은 방향의 힌트를 준다

이 원리를 패턴 공식으로 분해합니다.

1) 기본 프레임: 4단 레이어 합성(AND 구조)

스캐너는 아래를 “곱(AND)” 구조로 보시면 됩니다.
(어느 하나라도 무너지면 매집 시나리오 신뢰도가 급락)

핵심 탐지 패턴(메타 공식)

ACCUM_SIGNAL = Universe_OK ∧ Absorption ∧ Accumulation ∧ Execution_Style ∧ Confirmation ∧ Risk_Filters_OK

Universe_OK: “기관이 들어올 수 있는 종목 구조”

Absorption: “매도 압력 흡수”가 보이는가

Accumulation: “누적 자금흐름이 가격보다 선행”하는가

Execution_Style: “기관형 집행 흔적”이 있는가

Confirmation: 옵션/숏/오프익스체인지/지연 공시가 같은 방향인가

Risk_Filters_OK: 공급(희석)·이벤트가 시그널을 왜곡하지 않는가

이제 각 모듈을 ‘패턴’으로 설계합니다.

2) Universe_OK (유니버스 게이트)

목표: 잡음 많은 종목을 제거하고 “매집이 성립 가능한 전장”만 남김.

Universe_OK 패턴

Liquidity_OK: “거래대금/유동성이 충분”

Float_Structure_OK: “플로트가 너무 비정상적으로 작거나(작전성) 혹은 너무 큰데(지수/ETF처럼) 미세신호가 희석되는 상황이 아님”

Spread_OK(가능 시): “스프레드가 과도하지 않음”

Listing_OK: “정상 거래소/정상 종목”

Universe_OK = Liquidity_OK ∧ Float_Structure_OK ∧ Listing_OK ∧ (Spread_OK optional)

3) Absorption (핵심 1: ‘가격 하방 경직 + 거래 발생’)

목표: “팔리는 물량이 있는데 가격이 안 밀리는” 구간을 포착.

Absorption 패턴(개념)

Sell_Pressure_Present: “거래가 실제로 많이 발생(유의미한 체결/거래량 증가)”

Price_Not_Down: “그럼에도 저점이 지켜지거나, 하락이 제한됨”

Down_Vol_Weak: “하락 구간의 변동성/거래 강도가 상대적으로 약함”

Bid_Support(가능 시): “호가/스프레드에서 매수 지지가 관찰”

Absorption = Sell_Pressure_Present ∧ Price_Not_Down ∧ Down_Vol_Weak ∧ (Bid_Support optional)

이 Absorption이 매집 탐지의 ‘심장’입니다.
거래가 없는데 가격이 유지되는 건 의미가 약하고,
거래가 많은데 가격이 안 무너지는 것이 강합니다.

4) Accumulation (핵심 2: ‘자금흐름 누적’이 가격보다 선행)

목표: “가격은 횡보/완만하지만, 수급지표는 먼저 올라간다”를 포착.

Accumulation 패턴(개념)

Flow_Up: OBV/ADL/CMF/MFI 등 “누적 지표가 상승 방향”

Price_Base_or_GentleUp: 가격은 바닥권 횡보 또는 완만 상승

Up_Day_Dominance: 상승일에 거래가 실리고, 하락일에는 거래가 덜 실리는 비대칭

Accumulation = Flow_Up ∧ Price_Base_or_GentleUp ∧ Up_Day_Dominance

핵심은 **“가격보다 수급이 먼저 움직이는 선행성”**입니다.

5) Execution_Style (핵심 3: 기관형 집행 흔적)

목표: “기관이 흔히 쓰는 방식(VWAP/분산 집행/옥션 활용)”의 냄새를 잡기.

Execution_Style 패턴(개념)

VWAP_Anchoring: 가격이 VWAP 주변에서 “지지/방어”되는 느낌(분봉 기준)

Distributed_Participation: 장중 특정 한 방이 아니라 “시간 분산형” 거래 형태

Close_Strength / Auction_Footprint(가능 시): 마감/옥션에서 유의미한 체결 + 종가 강세

Execution_Style = VWAP_Anchoring ∧ Distributed_Participation ∧ (Close_Strength optional)

세력도 매집하지만, 기관은 특히 VWAP 주변 집행이 많이 나옵니다.
그래서 Execution_Style은 “기관 가능성”을 올려주는 모듈입니다.

6) Confirmation (핵심 4: 다른 시장(옵션/숏/오프익스체인지)과의 합치)

목표: 현물만으로 모호한 구간을 “다른 레이어가 같은 결론을 말하는지”로 확정.

Confirmation은 모듈 중 2개 이상 동시성을 요구하는 게 시너지가 큽니다.

Confirmation 모듈들

Options_Confirm:

콜 쪽 중심의 관심(OI/거래량/구조)이 증가하거나,

방향성 포지셔닝 힌트가 현물 시그널과 충돌하지 않음

Short_Lend_Confirm:

숏 압력/대차 타이트가 존재하는데 가격이 안 밀림(= 흡수 강화)

OffEx_Confirm(가능 시):

오프익스체인지 비중 변화가 “조용한 누적”과 정합

Confirmation 결합 규칙(개념)

Confirmation = (Options_Confirm + Short_Lend_Confirm + OffEx_Confirm) 중 ‘복수 동시 성립’

단일 Confirmation은 오탐이 있습니다.
“옵션+숏” 같이 서로 다른 시장이 같은 방향을 말할 때 강해집니다.

7) Risk_Filters_OK (시그널 왜곡 제거: 공급/이벤트/리밸런싱)

목표: 매집처럼 보이게 만드는 “비매집 요인”을 제거.

Risk_Filters_OK 패턴

No_Dilution_Supply_Shock: 발행/희석/락업/ATM 같은 공급 충격이 지배적이지 않음

Event_Noise_Control: 실적/중대 뉴스 임박 또는 직후로 인한 일회성 변동을 분리 처리

ETF_Rebalance_Filter: ETF/지수 리밸런싱 가능성이 더 큰 상황이면 별도 라벨링

Risk_Filters_OK = No_Dilution_Supply_Shock ∧ Event_Noise_Control ∧ ETF_Rebalance_Filter

8) “최고 시너지” 핵심 패턴 5종(실전에서 잘 맞는 조합)

위 모듈을 기반으로, 특히 시너지가 강한 대표 탐지 패턴 5개를 공식처럼 제시합니다.

패턴 A: “Classic Accumulation Base” (교과서형 매집)

정의: 가격은 눌리거나 횡보하지만, 수급은 계속 올라가는 형태.

Formula

Universe_OK

Absorption

Accumulation

Execution_Style(가산)

Risk_Filters_OK

“바닥에서 물량 받아먹기”의 가장 정석.

패턴 B: “Stealth VWAP Accumulation” (조용한 기관형 누적)

정의: 큰 폭의 상승 없이, VWAP 주변에서 시간 분산형 누적이 계속됨.

Formula

Universe_OK

Absorption(약~중)

Execution_Style(강)

Accumulation(중)

Confirmation(옵션 또는 오프익스체인지 중 1~2개)

“티 안 나게 쌓다가 어느 순간 트리거로 폭발” 후보를 잘 뽑습니다.

패턴 C: “Short-Pressure Absorption” (숏 압력 흡수형)

정의: 숏/대차 압력이 존재하는데도 하방이 안 열리고, 거래가 누적됨.

Formula

Universe_OK

Absorption(강)

Short_Lend_Confirm(필수)

Accumulation(중~강)

Risk_Filters_OK

이 패턴은 이후 “숏커버+추세 전환”으로 이어질 때 파워가 큽니다.

패턴 D: “Options-Led Accumulation” (옵션이 먼저 말하는 매집)

정의: 현물은 조용한데 옵션 포지셔닝이 먼저 변하고, 현물에서 흡수가 뒤따름.

Formula

Universe_OK

Options_Confirm(필수)

Accumulation(중) ← 현물의 누적 지표가 최소한 동행

Absorption(후행 확인)

Risk_Filters_OK

“정보 우위/포지셔닝”이 옵션에서 먼저 보이는 경우를 포착.

패턴 E: “Breakout With Prior Absorption” (진짜 돌파 vs 가짜 돌파 분리)

정의: 돌파 자체가 아니라, 돌파 이전에 “흡수+누적”이 있었는지로 진짜를 가름.

Formula

(Precondition) Absorption + Accumulation이 과거 구간에서 성립

(Trigger) Breakout(가격 구조 신호)

(Validation) RVOL/거래대금이 돌파를 지지

Risk_Filters_OK

“돌파 당일만 보고 추격하는” 오탐을 줄이는 데 최강입니다.

9) 최종 정리: 스캐너의 “결정 규칙(논리만)”

마지막으로, 실전 구현에서 자주 쓰는 “결정 로직”을 개념적으로 제안합니다.

필수 조건(게이트): Universe_OK ∧ Risk_Filters_OK

핵심 신호(둘 다 필요): Absorption ∧ Accumulation

기관 판별 강화(가능 시): Execution_Style

확정(강한 확률 상승): Confirmation 모듈 2개 이상 동시

즉,

CORE = Universe_OK ∧ Risk_Filters_OK ∧ Absorption ∧ Accumulation
BOOST = Execution_Style + Multi-Confirmation
FINAL = CORE ∧ (BOOST가 강할수록 랭킹 상단 배치)





------------------------------------





### 2번 의견:

**핵심 탐지 패턴: [The Compression-Absorption Matrix]**

이 모델은 3가지 논리적 모듈의 곱(Product)으로 구성됩니다. 하나라도 '0'이면 전체가 무효화됩니다.

각 모듈의 논리적 설계는 다음과 같습니다.

 **1. 유동성 흡수 효율 (Liquidity Absorption Efficiency)**

* **개념:** "얼마나 많은 거래량이 터졌는데, 가격은 얼마나 안 움직였는가?"
* **논리(Logic):**


* **작동 원리:**
* 분자(거래량)는 큰데 분모(변동폭)가 작다면, 결과값은 **극대화**됩니다.
* 이는 누군가 매도벽(Sell Wall)을 세워두거나, 쏟아지는 매물을 특정 가격대에서 **'Iceberg Order(빙산 주문)'**로 전부 받아내고 있음을 의미합니다. (개미들은 절대 이렇게 거래하지 못합니다.)



 **2. 흐름과 가격의 괴리 (Flow-Price Divergence)**

* **개념:** "가격의 방향과 돈의 방향이 일치하는가, 반대인가?"
* **논리(Logic):**


* **작동 원리:**
* Price Trend(가격 추세)가 '횡보(0)'하거나 '하락(-)'하는데, OBV(누적 거래량)의 기울기가 '상승(+)'한다면?
* 수식의 결과값은 **양수(+)**로 커집니다.
* 이는 겉으로 보이는 가격은 죽어있지만, 내부적으로는 매수 압력이 매도 압력을 압도하고 있다는 **'에너지 축적'**의 증거입니다.



 **3. 변동성 압축 계수 (Volatility Compression Factor)**

* **개념:** "스프링이 얼마나 꽉 눌려있는가?" (폭발 직전의 고요함)
* **논리(Logic):**


* **작동 원리:**
* 현재 변동성(ATR)이 역사적 평균보다 현저히 낮을수록 결과값은 커집니다.
* 세력은 매집을 완료하기 전, 개미들의 관심을 끄기 위해 의도적으로 주가를 지루하게 만듭니다. 이 **'질식 구간(Suffocation Zone)'**이 포착되어야 합니다.



---

 **최종 시너지 공식 (Concept Formula)**

위 3가지 논리를 통합하면, 우리가 찾는 **'스마트 머니 시그널'**은 다음과 같이 정의됩니다.

 **[패턴 해석 가이드]**

1. **높은 점수 (High Score):**
* 거래량은 폭발하는데 캔들 몸통은 십자형(Doji)에 가깝고 (**흡수**),
* 주가는 바닥을 기는데 보조지표는 고개를 들고 있으며 (**괴리**),
* 최근 며칠간 주가 등락폭이 씨가 말라버린 상태 (**압축**).
* ** 기관이 매집을 끝내고 '점화(Ignition)'를 기다리는 상태.**


2. **낮은 점수 (Low Score):**
* 거래량이 터지면서 장대양봉/음봉이 발생함 (이미 발산됨).
* 거래량과 주가가 같이 움직임 (일반적인 추세).
* 변동성이 이미 큼 (추격 매수의 영역).



**[선택적 부스터 (Optional Booster)]**

여기에 **옵션 시장 데이터**를 필터(Filter)가 아닌 **가중치(Weight)**로 추가합니다.

* **Logic:** 
* 이유: 현물 시장의 매집 패턴이 완성된 상태에서 옵션 시장의 베팅까지 들어온다면 신뢰도는 기하급수적으로 상승합니다.

---

**제언 (Advisor's Note)**

이 논리 구조는 단순히 "거래량 터진 종목"을 찾는 게 아닙니다. **"폭발적인 에너지를 억지로 누르고 있는 뚜껑"**을 찾는 공식입니다.

리테일 퀀트로서 이 로직을 구현할 때 가장 주의할 점은 **'변동폭(Denominator)'이 0에 수렴할 때 발생하는 왜곡**입니다. 따라서 실제 코딩 시에는 '최소 변동폭' 상수를 설정하여 `ZeroDivisionError`를 방지하고 노이즈를 걸러내야 합니다.



### 3번 의견:

기본 철학
매집의 본질은 **"들키지 않고 대량 매수"**다. 따라서 탐지의 핵심은 의도적 은폐의 흔적을 찾는 것이다.

1단계: 기초 이상 신호 (Primary Signals)
A. 거래량-가격 괴리 (Volume-Price Divergence)
VPD = 거래량 추세 방향 ≠ 가격 추세 방향

조건: 가격 횡보 또는 하락 + 거래량 점진적 증가
의미: 누군가 가격을 누르면서 조용히 모으는 중
B. 축적 흐름 확인 (Accumulation Flow)
AF = OBV 추세 > 가격 추세

조건: OBV 신고가 갱신 + 가격은 아직 미갱신
의미: 매수 압력이 가격에 선행하여 축적 중
C. 스마트머니 유입 (Smart Money Inflow)
SMI = 다크풀 비중 증가 ∩ 장 마감 거래량 비중 증가

조건: 다크풀 거래 비율 상승 + 마지막 30분 거래 집중
의미: 기관이 시장 충격 최소화하며 진입

2단계: 확증 신호 (Confirmation Signals)
D. 옵션 시장 선행 (Options Anticipation)
OA = 콜옵션 OI 급증 ∩ 내가격(ITM) 비중 증가

조건: 평소 대비 콜 OI 이상 증가 + ITM 콜 집중
의미: 레버리지 베팅으로 확신 있는 매수세 확인
E. 공매도 압력 해소 (Short Pressure Release)
SPR = Short Interest 감소 ∩ Cost to Borrow 하락

조건: 공매도 잔고 감소 추세 + 대차 비용 안정화
의미: 하방 압력 제거, 상승 저항 감소
F. 공시 기반 검증 (Regulatory Confirmation)
RC = 13F 신규 진입 ∪ 13D 보유 증가 ∪ Form 4 내부자 매수

조건: 최근 분기 기관 신규 매수 또는 내부자 순매수
의미: 지연된 데이터지만 강력한 확증

3단계: 복합 탐지 공식 (Composite Detection Formula)
매집 확률 스코어 (Accumulation Probability Score)
APS = (기초 신호 가중합) × (확증 신호 승수)
구조:
APS = [w₁(VPD) + w₂(AF) + w₃(SMI)] × [1 + α(OA) + β(SPR) + γ(RC)]
      \_________________________/     \____________________________/
           기초 신호 합산                    확증 신호 승수
논리:

기초 신호는 합산: 하나만 있어도 관심, 복수면 강화
확증 신호는 승수: 기초 신호 없으면 무의미, 있으면 확신 증폭


4단계: 시간 차원 필터 (Temporal Filter)
지속성 검증 (Persistence Check)
PC = 신호 지속 기간 ≥ 최소 관찰 기간

조건: 위 신호들이 단발성이 아닌 N일 이상 지속
의미: 노이즈 제거, 진짜 매집은 시간이 걸림
가속도 감지 (Acceleration Detection)
AD = d(APS)/dt > 0 (스코어 상승 추세)

조건: 매집 스코어가 시간에 따라 증가
의미: 매집 강도가 점점 강해지는 중 → 클라이맥스 접근

최종 공식: 통합 매집 탐지 모델
DETECTION_SCORE = APS × PC × (1 + AD)

WHERE:
  APS = [w₁(VPD) + w₂(AF) + w₃(SMI)] × [1 + α(OA) + β(SPR) + γ(RC)]
  PC  = 신호 지속일 / 기준일 (1 이상이면 유효)
  AD  = APS 변화율 (양수면 가속)

신호 간 시너지 매트릭스
              VPD    AF    SMI    OA    SPR    RC
        ┌─────────────────────────────────────────┐
  VPD   │  -     ★★★   ★★★   ★★    ★     ★★   │
  AF    │ ★★★    -     ★★    ★★★   ★★    ★★   │
  SMI   │ ★★★   ★★     -     ★★★   ★     ★    │
  OA    │ ★★    ★★★   ★★★    -     ★★★   ★★   │
  SPR   │ ★     ★★    ★      ★★★   -     ★    │
  RC    │ ★★    ★★    ★      ★★    ★     -    │
        └─────────────────────────────────────────┘

★★★ = 최고 시너지 (같이 나타나면 확신도 급상승)

실전 해석 가이드
스코어 영역해석행동낮음신호 부재 또는 노이즈관망중간초기 매집 가능성관찰 리스트 등록높음매집 진행 중 추정진입 타이밍 모색급상승매집 완료 임박 또는 돌파 준비즉시 대응 준비

이 공식의 핵심은 **"단일 지표 의존 배제"**다. 세력은 하나의 흔적은 숨길 수 있지만, 모든 흔적을 동시에 숨기긴 어렵다.