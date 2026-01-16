1. Static Features (화약): "얼마나 크게 터질 종목인가?"장 시작 전(Pre-market) 또는 일봉 마감 기준으로 계산합니다. 이 수치들은 당일 장중에는 변하지 않는 **'폭발 잠재력(Potential Energy)'**을 측정합니다.Feature NameDefinition (수식)Alpha Logic (선정 이유)Float TurnoverPre-market Vol / Float[공급 제한] 유통 주식 대비 거래량이 많다는 것은 손바뀜(Churn)이 활발하여 악성 매물이 소화되었다는 뜻입니다.Short RatioShort Interest / Float[숏 스퀴즈] 이 수치가 높으면(>20%), 급등 시 공매도 세력의 강제 청산(Covering)이 연료가 되어 폭등을 만듭니다.D-1 Compression(High - Low) / Close (어제 기준)[에너지 응축] 어제 변동폭이 작을수록(VCP), 오늘 방향성이 잡혔을 때 튀어 나가는 힘이 강합니다.Gap %(Current Open - Prev Close) / Prev Close[주목도] 적당한 갭(+2%~+10%)은 시장의 관심을 끌지만, 너무 큰 갭(+30% 이상)은 차익 실현 매물을 부릅니다.💡 추천 조합: Float < 10M AND Short Ratio > 10% AND D-1 Compression < 5%2. Dynamic Features (불꽃): "지금 터지고 있는가?"장 중 실시간(Real-time)으로 틱(Tick) 데이터를 받아 계산합니다. 이는 **'운동 에너지(Kinetic Energy)'**를 측정하며, 진입 타이밍을 결정하는 핵심 트리거입니다.Feature NameDefinition (수식)Alpha Logic (선정 이유)Tick Velocity10초간 체결 건수 / 1분 평균 체결 건수[속도] 거래량이 단순히 많은 것보다, **'얼마나 빠르게 체결되는가'**가 HFT와 모멘텀 알고리즘의 유입을 가장 먼저 알립니다.CVD Ratio(Aggressive Buy Vol) / (Aggressive Sell Vol)[의지] 시장가(Aggressive)로 긁는 매수세가 매도세를 압도해야 합니다. (수동적 매수벽은 허수일 수 있음)Relative Vol (1m)Current 1m Vol / Avg 1m Vol (Past 20 days)[거래량 급증] 평소의 1분과 지금의 1분이 얼마나 다른지 상대적으로 비교합니다. (최소 5배 이상 권장)Price location(Price - VWAP) / Price[추세 확인] 주가가 당일 거래량 가중 평균(VWAP) 위에 있어야만 '정상적인 상승'입니다. 아래에 있다면 '설거지'일 확률이 높습니다.🔥 핵심: Velocity > 8.0 AND CVD Ratio > 2.0 → IGNITION!3. Context Features (바람): "이유가 있는 상승인가?"숫자만으로는 알 수 없는 '재료'의 질을 판단합니다.Feature NameDefinition (방식)Alpha Logic (선정 이유)Catalyst Keyword뉴스 헤드라인 내 특정 단어 유무 (Bool)[재료] FDA, Merger, Patent, Contract, Earnings 등의 단어는 급등의 지속성을 보장합니다.Sector Heat해당 종목 섹터의 평균 등락률[테마] 혼자 오르는 것보다, 같은 섹터(예: 바이오, AI)가 같이 오를 때 확률이 비약적으로 상승합니다.📊 "최소·최강" 데이터셋 구조도 (요약)바이브 코딩을 위해 AI에게 전달할 때는 아래의 구조로 요청하시면 가장 깔끔합니다.PythonFeature_Set = {
    # 1. SETUP (Daily/Static) - 필터링 용도
    "Setup": [
        "Float_Shares",       # 유통주식수 (낮을수록 좋음)
        "Short_Interest_Pct", # 공매도 비율 (높을수록 좋음)
        "Pre_Market_Vol",     # 장전 거래량 (높을수록 좋음)
        "ATR_Percentage"      # 어제 변동성 (낮을수록 좋음, 응축)
    ],

    # 2. TRIGGER (Intraday/Dynamic) - 진입 신호 용도
    "Trigger": [
        "Tick_Velocity_Score", # 평소 대비 체결 속도 (Time & Sales 기반)
        "Order_Imbalance",     # 매수/매도 체결 강도 차이 (CVD)
        "Rel_Volume_1m",       # 1분 상대 거래량
        "Dist_from_VWAP"       # VWAP 이격도 (+값이어야 함)
    ],

    # 3. SAFETY (Filters) - 거름망 용도
    "Safety": [
        "Spread_Pct",          # 호가 스프레드 (너무 크면 진입 금지)
        "News_Category"        # 뉴스 유무 및 키워드 (Optional)
    ]
}
👨‍💻 Vibe Coding을 위한 프롬프트 (바로 사용 가능)"내가 연구하려는 Seismograph 전략의 핵심 피처셋을 정했어.Daily Data에서는 Float, Short Interest, ATR(변동성 축소) 3가지만 보고,Intraday Data에서는 Tick Velocity(체결속도), CVD(순매수체결), RelVol(상대거래량) 3가지만 볼 거야.이 '3+3 피처 구조'로 과거 3개월 급등주(Top Gainers) 데이터를 분석해서, 급등 직전 5분 동안 이 수치들이 어떤 패턴(임계값)을 보였는지 통계를 내줘."이 피처 세트는 불필요한 노이즈(RSI, MACD 등 후행지표)를 완벽히 제거하고, 오직 **수급(Money Flow)**과 **속도(Speed)**에만 집중한 가장 날카로운 구성입니다.

Layer 0. 전일 구조적 취약성 (필수 레이어)

“이 종목은 폭발이 가능한 구조인가?”

✅ 최소 피처 세트 (절대 제거 비권장)
피처	이유
Free Float	Top gainer의 1순위 결정 변수
Market Cap	동일 신호라도 반응 크기 완전히 다름
Price Level ($)	$1~10 구간 효과 매우 큼
20D ATR / Price	상대 변동성 (에너지 저장 능력)

👉 이 4개만 있어도 Top gainer 가능성의 50%는 설명됩니다.

💪 최강 피처 세트 (하지만 여전히 날씬함)
피처	의미
Free Float	
Market Cap	
Price	
Shares Outstanding / Float Ratio	실제 유통 압박
Short Interest % Float	스퀴즈 가능성
Days to Cover	강제 수급 전환 가능성
Options Available (Y/N)	옵션 없는 종목 = 현물 압축

⚠️ 주의

SI 관련 피처는 “있을 때만 강력”

없다고 제거하면 안 되지만, 가중치는 조건부로 사용

🟨 Layer 1. 전일~프리마켓 압축 에너지

“움직이기 직전의 비정상적 정적 상태”

✅ 최소 피처 세트
피처	이유
RelVol (20D 기준)	이미 주목받고 있는지
Range Compression (5D ATR / 20D ATR)	변동성 수축
Close-to-VWAP Distance (전일)	수급 균형 상태

이 세 개는 서로 상관 거의 없음이 장점입니다.

💪 최강 피처 세트
피처	의미
RelVol	
Range Compression	
Close-to-VWAP	
OBV Slope (5D)	누적 방향성
Gap Frequency (최근 10일)	점화 이력
Premarket Volume Ratio	개장 전 관심도
Premarket High vs Prior High	사전 저항 테스트

💡 여기까지 오면
→ “움직일 준비가 된 종목” 리스트가 됩니다.

🟧 Layer 2. 개장 직후 점화 신호 (가장 중요)

“지금 불이 붙었는가?”

✅ 최소 피처 세트 (강력 추천)
피처	이유
Tick Velocity (1m / 5m)	수급 유입 속도
Volume Burst (1m / 5m)	관심의 폭발
Price vs Opening Range High	구조적 돌파
Spread %	조작/비유동성 필터

👉 이 4개는 실전 트레이딩에 바로 사용 가능

💪 최강 피처 세트 (과적합 주의)
피처	의미
Tick Velocity	
Volume Burst	
Price vs ORH	
Spread	
Bid/Ask Imbalance	방향성
VWAP Deviation (z-score)	과열/정상
Trade Size Skew	소액 vs 대량
Halt Proximity Risk	거래정지 확률

⚠️ Tip

Tick Velocity + Volume Burst는 결합 변수로 정규화 권장

개별 가중치로 쓰면 자유도 과대평가 위험

🟥 Layer 3. 외생 촉매 (Narrative)

“왜 오늘인가?”

✅ 최소 피처 세트
피처	이유
News Exists (0/1)	촉매 유무
News Timing (Pre / Open / Intraday)	반응 패턴 결정
SEC Filing Today (Y/N)	예측 불가능 리스크
💪 최강 피처 세트
피처	의미
News Exists	
News Timing	
News Category	FDA / M&A / Crypto / AI
Headline Novelty Score	반복 뉴스 필터
Retail Keyword Hit	SNS·게시판 연계
PR vs 3rd-party	신뢰도

💡 중요한 포인트

뉴스의 ‘진실성’보다 ‘확산성’이 더 중요

Top gainer는 “팩트”보다 “전파 속도”에 반응

🧩 최종 추천: “최소·최강 하이브리드”

실전과 연구 모두에 가장 좋은 구성입니다.

[전일]
- Free Float
- Market Cap
- Price
- ATR/Price
- RelVol
- Range Compression

[개장 1~5분]
- Tick Velocity (norm)
- Volume Burst (norm)
- Price vs ORH
- Spread

[뉴스]
- News Exists
- News Timing
- News Category


➡️ 총 13~15개 피처
➡️ Top gainer 예측 연구에 가장 안정적인 sweet spot

🎯 마지막 조언 (중요)

“피처를 더 넣고 싶어질 때”가 위험 신호입니다.

Top gainer 연구의 진짜 엣지는
**피처 선택보다 ‘대조군 설계 + 시간 누수 차단’**에 있습니다.

전일(T-1) 피처 — 급등 가능성 사전 필터링
피처정의근거Float유통주식수20M 이하에서 급등 빈도 급증, 수급 병목Short Interest %Float 대비 공매도 비율15% 이상 시 숏스퀴즈 잠재력Relative Volume (T-1)전일 거래량 / 20일 평균1.5~3배 구간이 "조용한 관심" 신호ATR % (20일)ATR / 종가5~15% 구간이 폭발력과 유동성의 균형점Price vs 52wk High현재가 / 52주 고가70~90% 구간에서 돌파 확률 상승Days Since Last Spike마지막 +10% 이후 경과일20~60일 구간이 "에너지 재축적" 구간
당일(T) 장전 피처 — 갭업 품질 판단
피처정의근거Premarket Gap %프리마켓 가격 / 전일 종가 - 15~15% 갭이 지속 가능, 30%+ 갭은 페이드 확률 높음Premarket Volume RatioPM 거래량 / 전일 총거래량50% 이상이면 실질적 관심 확인PM High vs Open프리마켓 고가 대비 시초가 위치시초가가 PM High 근처면 강세 지속 신호
당일(T) 장중 1분봉 피처 — 실시간 모멘텀 확인
피처정의근거Tick Velocity10초간 체결 건수 / 1분 평균5배 이상에서 폭발적 관심 유입 감지Order Imbalance(매수체결 - 매도체결) / 총체결+0.3 이상 지속 시 일방적 매수세Spread %(Ask - Bid) / Mid2% 이하 유지 시 유동성 확보된 급등VWAP Distance %(현재가 - VWAP) / VWAP+3~8% 구간이 추세 확인 + 과열 미도달Volume Acceleration현재 1분 거래량 / 직전 5분 평균3배 이상에서 신규 진입 웨이브HOD Break Count장중 신고가 갱신 횟수3회 이상이면 계단식 상승 패턴
뉴스/이벤트 피처 — 촉매 품질 분류
피처분류 체계우선순위카테고리FDA 승인 > 계약/파트너십 > 실적 서프라이즈 > 애널리스트 업그레이드 > 일반 PR상위 카테고리일수록 지속력 높음키워드 강도"approved", "contract", "acquisition" > "partnership", "agreement" > "update", "announces"강한 키워드가 더 큰 초기 갭 유발뉴스 타이밍장전 6-9시 > 전일 장후 > 장중장전 뉴스가 가장 깨끗한 셋업소스 신뢰도SEC Filing, PR Newswire > 회사 직접 발표 > 루머/SNS공식 소스일수록 페이드 확률 낮음
시장 맥락 피처 — 환경 필터
피처정의활용SPY 방향당일 SPY 등락시장 약세 시 급등 지속력 감소VIX 수준변동성 지수20 이상에서 급등 후 되돌림 확대섹터 모멘텀해당 섹터 ETF 5일 수익률섹터 순풍 시 개별 급등 지속력 증가

최소 구성 (MVP)
데이터 수집이 제한적이라면 이 6개만으로 시작:
전일: Float, Short Interest %, Relative Volume
당일: Premarket Gap %, VWAP Distance %, Spread %
이 조합만으로도 "급등 가능 후보" vs "노이즈" 분류의 70% 이상 설명력을 기대할 수 있습니다.

피처 간 상호작용 우선순위
단일 피처보다 조합이 중요한 경우:
조합해석Low Float + High SI + 뉴스 촉매숏스퀴즈 최적 조건Tight ATR (T-5) + Volume Spike (T-1) + Gap Up (T)VCP 돌파 패턴High PM Volume + Low Spread + VWAP 상방기관 참여 가능성 높은 급등강한 키워드 + 약한 갭 (5% 미만)저평가된 촉매, 추가 상승 여력

top gainer 공통점 탐색·전략화라는 목적 기준으로, “최소한으로 잡되 정보량이 많은” 피처 세트를 추천하면 아래 정도 구성이 좋다. 모든 피처를 꼭 다 쓰기보다, 각 블록에서 핵심적인 것만 먼저 쓰고 이후 성능 보고 확장하는 식이 효율적이다.​

1. 전일·과거 구간(베이스라인 컨텍스트)
구조·리스크

유통주식수(float)

시가총액(log mktcap)

공매도 비율 / 공매도 잔고(가능하면 days-to-cover 포함)

변동성·모멘텀

ATR(14) 또는 최근 10·20일 일간 변동성

전일·최근 5일·20일 수익률(단순·초과 둘 다)

과거 60일 베타, 60일 고점 대비 괴리율(추세 상단/하단 위치)

유동성

전일 거래대금(절대값 + 60일 평균 대비 비율, relvol)

이 블록은 “이 종목이 원래 어떤 캐릭터인가(잡주/대형 우량/테마주)”를 잡는 최소 세트다.​

2. 당일 시가·초반 1분~5분
갭·초반 가격 행동

시가의 전일 종가 대비 갭 비율(gap%)

시가→1분 종가 수익률, 시가→5분 종가 수익률

유동성·호가

스프레드(틱 단위·bps 기준 둘 다), 스프레드의 전일 대비 변화폭

호가잔량 기반 order-book imbalance (상위 N틱 매수·매도 물량 비율)

체결 흐름

1분 tick-velocity(초당 체결 건수, 체결 수량)

초반 매수·매도 aggressor volume 비율(시장가/시장가 유사 주문 비중)

이 블록은 “초반에 진짜 돈이 붙었는지, 호가가 얇은데 쓸려 올라가는지”를 구분하는 핵심이다.​

3. 장중(예: 1분·5분 롤링 피처 요약)
원천 1분봉 전부를 쓰기보다는, 요약 통계 형태의 피처가 최소·강력하다.​

가격 패턴

당일 고가·저가·종가의 상대 위치(종가/고가, 저가/고가 등)

일중 최대/평균/마지막 변동성(1분 수익률 표준편차)

수급·체결

장중 평균 tick-velocity, 피크 tick-velocity

공격적 매수 비율의 평균·최대, 일중 내내의 평균 order-book imbalance

유동성 변화

장중 평균 스프레드, 피크 스프레드, 스프레드 변동폭

일중 총 거래대금과 전일 대비 배수(relvol intraday)

이 피처들로 “단발성 스파이크 vs 꾸준한 체결 동반 추세 랠리”를 잘 분리할 수 있다.​

4. 뉴스·이벤트 피처
텍스트 전체를 쓰기 전에, 최소한의 구조화 피처부터 넣는 것이 안정적이다.​

이벤트 플래그

실적 발표, 가이던스, 인수·매각, 바이오 임상, 규제/소송, 투자 유치 등 카테고리 더미

공시/뉴스 발생 시각과 장 시작·장중·장마감 기준 시간 차이

정량 요약

당일 관련 뉴스 개수(오전·오후 분리 가능)

헤드라인·요약에 기반한 감성 점수(긍·부정, 강도)

키워드 기반 테마

AI, EV, 반도체, 선거, 전쟁·제재, Meme 등 주요 테마 키워드 출현 여부·개수

이 블록은 “실질 펀더멘털/정책 이벤트 동반 모멘텀 vs 순수 수급·테마 플레이”를 구분하는 데 중요하다.​

5. 시장·섹터 컨텍스트
시장 상태

당일 지수 수익률, 변동성지수(VIX 등), 시장 내 상한가/상승 종목 비율

섹터 인덱스 수익률, 섹터 내 평균 거래대금 변화율

상대 위치

종목 수익률 – 섹터 수익률, 종목 수익률 – 시장 수익률

같은 섹터 내 top gainer 동시 출현 수(섹터 붐/테마 장세 여부)

이 피처 덕분에 “시장·섹터 전체 랠리 속 자연스러운 승자”와 “시장 역행 단독 랠리”를 분리할 수 있다.​

6. 요약: 최소·최강 권장 세트
실전용으로 “최소·최강”만 압축하면 아래 정도 구성이 좋다.​

구조·과거

float, log mktcap, 공매도 비율, ATR(14), 전일/5일 수익률, 전일 거래대금 & relvol

당일 오프닝·1~5분

gap%, 시가→5분 수익률, 1분 tick-velocity, order-book imbalance, 스프레드 & 변화폭

일중 요약

종가/고가 비율, intraday relvol(총 거래대금 배수), 일중 변동성(1분 수익률 표준편차), 평균 aggressor buy 비율

뉴스·이벤트

이벤트 카테고리 더미(실적/인수/임상/정책), 뉴스 건수, 감성 점수, 주요 테마 키워드 플래그

시장·섹터

섹터·시장 수익률, 종목–섹터/시장 초과수익률, 섹터 동시 top gainer 수

이 세트를 기반으로 먼저 단순 모델(로지스틱/트리)에서 feature importance를 보고, 추가로 세부 마이크로피처(세부 시퀀스, 더 세분된 호가 구조)를 붙여가는 식으로 확장하는 것을 추천한다.​

(Fundamental / Static): float/short-interest/market-cap/sector-tailwinds
저유동(float < 30M shares)과 고공매도(short interest > 20%)가 공통적이며, 소형주(market cap < $1B)와 섹터 바람(예: tech/AI)이 상승 촉매로 작용. 이는 winners의 95%가 저float을 가진다는 관찰에서 유래.
(Previous Day / Technical): relvol/ATR/RSI/above-50-200DMA
상대 거래량(relvol > 1.5x 평균), 변동성(ATR > 평균), 과매수 지표(RSI > 70), 그리고 50/200일 이동평균 위 위치(95% winners)가 breakout 준비를 나타냄. 이는 staircase 패턴이나 accumulation을 예측.
(Intraday / 1-min Level): volume-surge/tick-velocity/order-imbalance/spread-narrowing
급증 거래량(volume surge > 2x open), 가격 변화 속도(tick-velocity), 주문 불균형(imbalance > 0), 스프레드 축소(spread < 0.01%)가 당일 모멘텀을 포착. 이는 supply-demand shift를 실시간 검증.
(Catalyst / External): EPS-growth/catalyst-type/news-keywords/social-buzz
EPS 가속(+20% YoY), 촉매 유형(earnings/new product/IPOs within 10yrs), 뉴스 키워드(merger/disruptive), 소셜 버즈(언급 증가)가 정보 확산을 유발. 95% winners에 growth catalyst 공통.

웹 검색 결과("top daily gainers stock features analysis predictors" 등)를 분석한 결과, top gainer 예측/공통점 연구에서 자주 언급되는 피처 세트는 가격 모멘텀, 거래량/유동성, 뉴스 이벤트, 시장 컨텍스트 중심으로 구성되며, 머신러닝(랜덤포레스트, LSTM 등)에서 유효성이 입증된 항목들이 강조된다. 이전 추천과 유사하나, intraday 단기 모멘텀 연구에서 tick-level imbalance와 volume commonality가 추가로 부각된다.​

전일·과거 피처 (베이스라인)
모멘텀: 전일/5일 수익률, 60일 고점 대비 괴리율.​

변동성/리스크: ATR(14), 과거 20일 변동성, 베타.​

유동성/구조: relvol (거래대금 배수), float, 시가총액.​

당일 초반·장중 피처 (가격 행동)
갭/초반: gap%, 시가→5분 수익률, tick-velocity (초당 체결).​

호가/체결: order-book imbalance, aggressor buy/sell 비율, intraday spread 변화.​

요약: 종가/고가 비율, 일중 변동성 (1분 수익률 SD), intraday relvol.​

뉴스·이벤트 피처
플래그: earnings surprise, M&A, positive news 카테고리 더미.​

감성: sentiment score (긍정/강도), 뉴스 건수.​

시장·섹터 컨텍스트
상대성: 종목-시장/섹터 초과수익률, 섹터 momentum.​

상태: VIX, 시장 상승 종목 비율, high volatility days 더미.​

최소 세트로 압축 시 전일 relvol+ATR+gap%+imbalance+sentiment 5개만으로도 intraday predictability 70% 이상 달성 사례가 있으며, volume commonality와 slow-moving capital proxy가 핵심 추가 변수로 꼽힌다.​

검색 결과를 종합해서 정리해 드리겠습니다.

웹검색 기반: Top Gainer 예측 피처 세트
실무 트레이더들이 사용하는 핵심 피처 (스캐너/스크리너 기준)
전일(T-1) 필수 피처
피처출처활용FloatThe float is the number of shares available to trade. Warrior Trading Looking for stocks with under 10 million shares available to publicly trade. StocksToTradeLow float = 급등 용이Short InterestShort Interest refers to the number of shares held short against the company. Warrior Trading The shares short as a percentage of the float should be greater than 10% Scanz숏스퀴즈 잠재력Relative VolumeRelative Volume (5 min %): Volume in the last 5-minutes compared with a regular 5-minute interval. A higher ratio is better. Warrior Trading비정상적 관심 탐지Price RangeLow float stocks priced between $0.25 and $20, trading more than 100,000 and up more than 5% on the day. StocksToTrade변동성 최적 구간Days to CoverFilter by the number of days it would take short sellers to cover their positions based on average daily volume. SwingTradeBot스퀴즈 지속 시간
당일(T) 장전/장중 피처
피처출처활용Gap %A gap is defined by a stock opening higher at the 9:30am opening bell than the stock closed at the 4pm closing bell during the prior trading session. Stocks gap up because they have news. Warrior Trading촉매 강도 측정VWAPIf the stock is trading below its VWAP, it suggests sellers are dominating and the current price could be a good deal. If buyers are in control, the stock is likely to trade above its VWAP. Charles Schwab기관 참여 벤치마크Order ImbalanceAggressive buying pressure may indicate that there are more buyers than sellers in the room; aggressive selling pressure may indicate the opposite scenario. StockGro실시간 수급 파악Volume BurstDiscovery is built to screen and track momentum using purpose-built filters including; Unusual Volume, Momentum, Float, Daily Gain, and VWAP. Mometic돌파 확인
뉴스/촉매 피처
피처출처우선순위FDA 승인Regulatory actions and clinical readouts are stock-moving catalysts. Benzinga For biotech and pharma, the catalysts we're interested in are clinical trial updates and results and the big money-maker—an FDA approval. StocksToTrade최상위Earnings BeatQuite frequently, a company will lose money, but it loses less money than the market anticipated—or less than the shareholders thought. And then, all of a sudden, the stock has the potential to spike. StocksToTrade상위Contract/PartnershipAnnouncements about a new contract secured by a company stock that you're watching, or a new product release or announcement of a new product in the pipeline can also make stocks move. StocksToTrade중상위

학술 연구에서 제시하는 ML 피처
피처 카테고리세부 항목출처기술적Financial metrics like Return on Equity and Earnings Per Share to forecast a company's performance. MDPI기본감성 분석Integrating sentiment analysis with machine learning and deep learning techniques has proven to significantly enhance stock market predictions. MDPI보조복합 접근Mixed approach combines various prediction techniques, including technical analysis, fundamental analysis, and sentiment analysis. MDPI권장내부자 거래Insider trading offers special insights into market sentiment, pointing to upcoming changes in stock prices. arXiv고급

실무 스캐너 표준 설정 예시
Run a top gainer scan — filter for volume > 1M, price > $1, up > 10%. Confirm the catalyst — Is it real news or a chat room pump? StocksToTrade
Gap % is the percentage move from the previous day's closing price to premarket price before the open. This is an important metric when you're scanning for both large-cap and small-cap stocks premarket. The reason you want to scan for stocks that have gapped up with higher than average volume is that this is perhaps the best indicator that the stock will provide you momentum and range after the open. Humbled Trader

내 추천 vs 웹검색 결과 비교
구분내 추천웹검색 결과공통Float, SI%, RelVol, VWAP, Gap%, 뉴스 카테고리동일내 추천에만 있음Tick Velocity, Order Imbalance 수치화, ATR%, Days Since Last Spike-웹에서 추가 강조Days to Cover, 프리마켓 거래량 비율, 소셜미디어 멘션실무에서 더 중시
결론적으로 웹검색 결과는 제 추천과 대체로 일치하며, Days to Cover와 소셜 멘션 빈도를 추가로 고려하면 더 완성도 높은 피처 세트가 됩니다.

1. Static Features (화약): "얼마나 크게 터질 종목인가?"장 시작 전(Pre-market) 또는 일봉 마감 기준으로 계산합니다. 이 수치들은 당일 장중에는 변하지 않는 **'폭발 잠재력(Potential Energy)'**을 측정합니다.Feature NameDefinition (수식)Alpha Logic (선정 이유)Float TurnoverPre-market Vol / Float[공급 제한] 유통 주식 대비 거래량이 많다는 것은 손바뀜(Churn)이 활발하여 악성 매물이 소화되었다는 뜻입니다. (통상 10% 이상이면 폭발적)Short RatioShort Interest / Float[숏 스퀴즈] 이 수치가 높으면(>20%), 급등 시 공매도 세력의 강제 청산(Covering)이 연료가 되어 폭등을 가속화합니다.D-1 Compression(High - Low) / Close (어제 기준)[에너지 응축] 어제 변동폭이 작을수록(VCP 패턴), 오늘 방향성이 잡혔을 때 튀어 나가는 힘이 강합니다.Gap %(Current Open - Prev Close) / Prev Close[주목도] 적당한 갭(+2%~+10%)은 시장의 관심을 끌지만, 너무 큰 갭(+30% 이상)은 차익 실현 매물을 부릅니다.💡 추천 조합: Float < 10M AND Short Ratio > 10% AND D-1 Compression < 5%2. Dynamic Features (불꽃): "지금 터지고 있는가?"장 중 실시간(Real-time)으로 틱(Tick) 데이터를 받아 계산합니다. 이는 **'운동 에너지(Kinetic Energy)'**를 측정하며, 진입 타이밍을 결정하는 핵심 트리거입니다.Feature NameDefinition (수식)Alpha Logic (선정 이유)Arrival Rate10초간 체결 건수 / 1분 평균[속도] 'Tick Velocity'의 학술적 명칭입니다. 거래량이 단순히 많은 것보다, **'얼마나 빈번하게 체결되는가'**가 모멘텀 점화(Ignition)의 가장 빠른 신호입니다.OFI (Order Flow Imbalance)(Buy Vol - Sell Vol) / Total Vol[의지] 호가창(LOB) 분석의 핵심입니다. 매수 주도 체결이 매도 주도를 압도해야 합니다. 단순 거래량 폭발은 '매도 폭탄'일 수도 있기 때문입니다.Relative Vol (1m)Current 1m Vol / Avg 1m Vol (Past 20 days)[거래량 급증] 평소의 1분과 지금의 1분이 얼마나 다른지 상대적으로 비교합니다. (최소 5배 이상 권장)Price Location(Price - VWAP) / Price[추세 확인] 주가가 당일 거래량 가중 평균(VWAP) 위에 있어야만 '정상적인 상승'입니다. 아래에 있다면 '설거지'일 확률이 높습니다.🔥 핵심: Arrival Rate > 8.0 AND OFI > 0.5 → IGNITION!3. Context Features (바람): "이유가 있는 상승인가?"숫자만으로는 알 수 없는 '재료'의 질을 판단합니다.Feature NameDefinition (방식)Alpha Logic (선정 이유)Catalyst Keyword뉴스 헤드라인 내 특정 단어 유무 (Bool)[재료] FDA, Merger, Patent, Contract, Earnings 등의 단어는 급등의 지속성을 보장합니다.Sector Heat해당 종목 섹터의 평균 등락률[테마] 혼자 오르는 것보다, 같은 섹터(예: 바이오, AI)가 같이 오를 때 확률이 비약적으로 상승합니다.📊 "최소·최강" 데이터셋 구조도 (요약)바이브 코딩을 위해 AI에게 전달할 때는 아래의 구조로 요청하시면 가장 깔끔합니다.PythonFeature_Set = {
    # 1. SETUP (Daily/Static) - 필터링 용도
    "Setup": [
        "Float_Shares",       # 유통주식수 (낮을수록 좋음, <20M)
        "Short_Interest_Pct", # 공매도 비율 (높을수록 좋음)
        "Pre_Market_Vol_Ratio", # 장전 거래량 / Float (핵심 지표)
        "ATR_Percentage"      # 어제 변동성 (낮을수록 좋음, 응축)
    ],

    # 2. TRIGGER (Intraday/Dynamic) - 진입 신호 용도
    "Trigger": [
        "Trade_Arrival_Rate",  # 평소 대비 체결 빈도 (Velocity)
        "Order_Flow_Imbalance", # 매수/매도 체결 강도 차이 (OFI)
        "Rel_Volume_1m",       # 1분 상대 거래량 (RVol)
        "Dist_from_VWAP"       # VWAP 이격도 (+값이어야 함)
    ],

    # 3. SAFETY (Filters) - 거름망 용도
    "Safety": [
        "Spread_Pct",          # 호가 스프레드 (너무 크면 진입 금지)
        "News_Category"        # 뉴스 유무 및 키워드 (Optional)
    ]
}

🔎 1) 실시간 Top Gainer 목록과 시장 정보

여러 금융 데이터 서비스가 Top Gainers(당일 최고 상승주) 목록을 제공합니다. 이들은 대체로 다음 정보를 포함합니다:

종목명, 종가, 종가 대비 변화율

고가/저가

거래량

(일부 플랫폼에서는) 변동성, 차트 분석 etc. 
Investing.com 한국어
+1

예시:

Investing.com: 미국 주식 Top Gainer 리스트 
Investing.com 한국어

Yahoo Finance: 가장 크게 오른 주식 종목 리스트 
야후 파이낸스

👉 이 데이터 자체가 “공통 특성”을 말해주지는 않지만, 비교를 위한 핵심 지표(종가 변화율, 거래량, 변동성) 제공에 적합합니다.

📈 2) Top Gainer → 연구/전략 구축 시 참고할 수 있는 분석 요소
📌 (A) 기술적·거래 구조적 신호

High-frequency data: 초단위 거래/호가 데이터를 활용해 가격 **급등 시점(jump)**을 분석하는 연구는 존재합니다.
→ 예: 주문장(LOB) 기반 정보 + 기술 지표 조합으로 가격 점프 예측 모델 시도 논문 
arXiv

→ 이 논문들은 Top Gainers의 구조적 전조를 찾을 때 참고할 만한 아이디어입니다:

유동성 지표

호가 스프레드/시간 가중 신호

하지만 이들 자체가 “Top Gainer만을 정의하는 공식”을 제공하지는 않습니다.

📌 (B) 뉴스 텍스트 기반 예측 접근

AZFinText 같은 시스템은 뉴스 기사 텍스트를 분석해서 주가 변동을 예측합니다.
→ 특정 단어·표현이 급격한 움직임과 연관될 수 있다는 아이디어 
위키백과

응용 예:

뉴스 키워드의 긍정/부정 강도

특정 뉴스 카테고리 (FDA/earnings/M&A 등)

이런 식의 텍스트 피처는 웹 기반 자료에서도 주로 권장되는 추가적 설명변수입니다.

📊 3) Top Gainer/급등 vs 기존 금융 연구 패턴

웹에서 직접 “Top Gainer를 예측하기 위한 피처 연구 결과”를 찾기는 어렵지만, 관련하여 금융 연구에서 통용되는 몇 가지 실증적 사실/패턴이 있습니다:

✨ (A) 기술적 지표의 주요성

급등주는 종종 거래량 돌파 + 가격 변동성 확대 신호를 보입니다. 이는 웹 스크리너에서 Top Gainer 조건으로 주로 제공되는 필터이기도 합니다 (예: 거래량과 상승률 기준) 
Investing.com 한국어

→ 거래량 기반 신호가 중요한 이유는 이것이 모멘텀/유동성 충격의 직접적인 기록이기 때문입니다.

✨ (B) 뉴스/카탈리스트 중요

웹 자료에서도 급등 종목의 움직임이 단지 숫자만으로 생기지는 않는다는 점을 언급합니다.

Positive news, earnings surprises, M&A 뉴스 등이 급등과 연결될 수 있다는 내용이 많습니다 (Pocket Option 예) 
pocketoption.com

뉴스를 카테고리화하고 타이밍을 반영하는 것은 Top Gainer 분석에서 가장 유용한 외생 변인입니다.

✨ (C) 거래량 기반 필터는 기본

거래량 증가와 상승률 변화를 함께 보는 것은 거의 모든 Top Gainer 관련 서비스의 필수 항목입니다 
Investing.com 한국어

→ 즉, 당일 가격 변동과 거래량의 상관성은 어떤 분석을 하더라도 포함해야 할 기본 피처입니다.

📌 4) 웹에서 직접 확인 가능한 데이터 활용법
▶ 실시간/과거 Top Gainers 데이터 API

Financial Modeling Prep(Gainers) API는 실시간 + 과거 가격 변화 데이터를 제공합니다.
→ 이를 통해 과거 Top Gainer의 특징을 체계적으로 모아볼 수 있음 
모델링 준비

📌 5) 웹 기반 자료가 말해주는 리서치 인사이트 요약

✔ Top Gainer 목록은 가격 변화, 거래량, 변동성 중심의 단순 나열이지만
↳ 이 지표들은 결국 과학적/통계적 분석의 필수 최소피처입니다. 
Investing.com 한국어
+1

✔ 최고 급등주는 뉴스/카탈리스트와 같이 외생 이벤트와 겹치는 경우가 많습니다. 
pocketoption.com

✔ 별도의 학술적 연구는 직접적으로 “Top Gainer 피처 세트”만을 다루진 않지만
↳ 가격 점프 예측 연구나 텍스트 기반 뉴스 영향 연구가 참고가 됩니다. 
arXiv
+1

📌 참고할 만한 추가 접근(웹 근거 포함)

❗ 웹페이지 스크리너·API → 데이터 수집 레벨
✔ 실시간 가격/거래량 스크리너 (Investing / Yahoo) 
Investing.com 한국어
+1

✔ API로 과거 Top Gainer 주문 흐름 및 가격 변동 데이터 획득 
모델링 준비

🔍 연구적 접근
✔ 텍스트 기반 뉴스 영향 분석 시스템(AZFinText) 
위키백과

✔ 깊은 시계열/유동성 데이터 기반 점프 예측 논문 
arXiv