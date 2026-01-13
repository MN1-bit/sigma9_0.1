# Strategy Candidates 비교분석 보고서

> 분석 대상: `perp.md`, `gem.md`, `anth.md`, `cgpt.md`
> 분석일: 2026-01-11

---

## 1. 공통점 (Commonalities)

| 항목 | 공통 내용 |
|------|----------|
| **시장 철학** | 펀더멘털보다 **유동성/수급/오더플로우**가 가격을 결정한다는 전제 |
| **VWAP 중심** | 모든 문서가 VWAP을 **핵심 기준선**으로 사용 (위=Bullish, 아래=Bearish) |
| **종목 선정** | Low Float + High RVOL + Gap% + Catalyst 조합이 공통 필터 |
| **시간대 전략** | 장 초반(9:30~10:30) = 핵심 수익 구간, 점심시간 = Dead Zone/매매 금지 |
| **리스크 관리** | 물타기(Averaging Down) **절대 금지**, 당일 손실 한도 설정 |
| **홀딩 원칙** | Day Trading Only, 오버나잇 금지 (희석/오퍼링 리스크) |
| **데이터 Tier** | Tier 1: Level 2/Tape/Volume, Tier 2: 뉴스/숏이자, Tier 3: SEC Filing/고급 분석 |

---

## 2. 차이점 (Key Differences)

| 구분 | Perplexity | Gemini | Anthropic | ChatGPT |
|------|------------|--------|-----------|---------|
| **가격대** | $2~$10 (특히 $3~$8) | 언급 없음 | 언급 없음 | 언급 없음 |
| **Float 기준** | 언급 없음 | <10M ⭐⭐⭐⭐⭐ | <20M | 언급 없음 |
| **RVOL 기준** | ≥3x | >5x | >5x | 상대적 급증 |
| **Gap% 기준** | 언급 없음 | >20% | >20% | 언급 없음 |
| **핵심 플레이북** | 프론트사이드 모멘텀 + 리버설 | LULD Halt + Short Squeeze + Gap&Go | VWAP Reclaim + PDHB + HOD Break | 7개 세분화 패턴 |
| **숏 전략** | 패러볼릭 피크 리버설 숏 허용 | Short Squeeze **롱** 중심 | 언급 적음 | 언급 없음 |
| **포지션 사이징** | 0.5~1R 고정 | 1~2% 리스크 | ATR 기반 동적 | R 기준 동적 |
| **스케일링** | 30~50% → 추가 진입 | 1/3씩 분할 매도 | 33% × 3단계 | 패턴별 개별 정의 |
| **고유 개념** | HTF/LTF 구분 | Float Rotation, Dilution Checker | Float Rotation Theory, Pain Trade | EV 스코어링, 4단 시스템 |

---

## 3. 필수 데이터 비교 (Required Data)

### 3.1 Tier 1: 필수 데이터

| 데이터 | Perp | Gem | Anth | CGPT |
|--------|:----:|:---:|:----:|:----:|
| **Level 2 / Order Book** | ✅ | ✅ | ✅ | ✅ |
| **Time & Sales (Tape)** | ✅ | ✅ | ✅ | ✅ |
| **VWAP** | ✅ | ✅ | ✅ | ✅ |
| **OHLCV/가격 데이터** | ✅ | ✅ | ✅ | ✅ |
| **실시간 거래량** | ✅ | ✅ | ✅ | ✅ |
| **Float (유통 주식 수)** | ❌ | ✅ | ✅ | ❌ |
| **데이게이너 리스트** | ✅ | ❌ | ❌ | ❌ |

### 3.2 Tier 2: 엣지 강화 데이터

| 데이터 | Perp | Gem | Anth | CGPT |
|--------|:----:|:---:|:----:|:----:|
| **뉴스/Catalyst** | ✅ | ✅ | ✅ | ✅ |
| **Short Interest** | ❌ | ✅ | ✅ | ❌ |
| **섹터 모멘텀** | ✅ | ❌ | ❌ | ❌ |
| **Float Rotation** | ❌ | ✅ | ✅ | ❌ |
| **Options Flow** | ❌ | ❌ | ✅ | ❌ |
| **희석 이벤트 탐지** | ❌ | ❌ | ❌ | ✅ |
| **RelVol/상대거래량** | ❌ | ✅ | ✅ | ✅ |

### 3.3 Tier 3: 고급 분석 데이터

| 데이터 | Perp | Gem | Anth | CGPT |
|--------|:----:|:---:|:----:|:----:|
| **SEC Filings** | ❌ | ✅ | ✅ | ❌ |
| **ATM Offering 조항** | ❌ | ✅ | ❌ | ❌ |
| **MMID (마켓메이커)** | ❌ | ✅ | ❌ | ❌ |
| **FTD (Failure-to-Deliver)** | ❌ | ❌ | ✅ | ❌ |
| **Dark Pool Prints** | ❌ | ❌ | ✅ | ❌ |
| **Social Sentiment** | ❌ | ❌ | ✅ | ❌ |
| **슬리피지 프로파일** | ❌ | ❌ | ❌ | ✅ |

### 3.4 문서별 데이터 특화 영역

| 문서 | 특화 영역 | 핵심 데이터 |
|------|----------|------------|
| **Gemini** | 희석 리스크 방어 | SEC/ATM 오퍼링 + MMID 분석 |
| **Anthropic** | 기관 행동 추적 | FTD/Dark Pool/Social |
| **ChatGPT** | 실행 비용 최적화 | 희석 이벤트 + 슬리피지 |
| **Perplexity** | 종목 발굴 | 데이게이너 리스트 + 섹터 모멘텀 |

---

## 4. 문서별 특이사항 (Notable Points)

### 4.1 Perplexity (`perp.md`)

- 가장 **구체적인 가격대**($2~$10) 제시
- **숏 전략**(패러볼릭 피크 리버설)을 플레이북에 포함한 **유일한 문서**
- HTF(일봉)/LTF(1~5분봉) **멀티타임프레임** 관점 강조
- 플레이북 패턴이 2개로 가장 단순

### 4.2 Gemini (`gem.md`)

- **Float Rotation** 개념을 가장 상세히 설명
  - 예: 유통물량 100만주 + 거래량 1,000만주 = 10회전
- **Dilution Checker** 시스템 제안
  - SEC EDGAR 크롤링으로 ATM 오퍼링 리스크 자동 체크
- **MMID(마켓 메이커 코드)** 분석 언급 (CDRG, NITE 등)
- 유일하게 **시총 기준** 명시 ($50M~$300M)
- 시스템 구현 관점에서 가장 구체적인 기술 가이드 제공

### 4.3 Anthropic (`anth.md`)

- **테이블/다이어그램 형식**이 가장 체계적 (ASCII 아트 시스템 플로우)
- **Float Rotation Theory**: N회 회전 → 참가자 피로도 → 반전 확률 상승
- **Pain Trade** 개념: "대다수가 틀리는 방향이 결국 실현됨"
- **SSR Trigger Play** 언급: -10% 하락 → SSR 발동 → 숏커버 랠리
- Python 코드 예시로 **ATR 기반 동적 사이징** 제시
- 엣지 유형을 4가지로 분류 (정보/실행/심리/리스크 비대칭)

### 4.4 ChatGPT (`cgpt.md`)

- 가장 **많은 플레이북 패턴** (7개 vs 2~4개)
- **"규칙카드 0"** 개념 (거래 자격 체크리스트)
- **EV(기대값) 스코어링** 개념 도입
- **4단 시스템 구현** 제안:
  1. 룰 기반 후보군
  2. EV 스코어링
  3. 금지 게이트
  4. 신호 저장
- **희석 리스크 점검**을 종목 선정 단계에서 강조
- 금지 조건이 **각 플레이북별로 세분화**되어 가장 상세

---

## 4. 종합 인사이트

### 4.1 통합 시 핵심 기반

모든 문서가 공통으로 사용하는 핵심 요소:
- **VWAP** (핵심 기준선)
- **Level 2 / Tape Reading** (오더플로우)
- **Catalyst** (촉매/서사)
- **리스크 관리** (물타기 금지, 데일리 스탑)

### 4.2 문서별 강점 및 채택 고려사항

| 문서 | 강점 | 채택 시 고려사항 |
|------|------|-----------------|
| **Perplexity** | 멀티타임프레임 관점, 숏 전략 포함 | 가격대 기준 구체적, 양방향 전략 |
| **Gemini** | Float Rotation, Dilution Check 등 **데이터 인프라** 관점 | 시스템 구현 가이드로 활용 |
| **Anthropic** | **리스크 분류 체계화**, 구조적 프레임워크 | 개념 정립 및 교육용 |
| **ChatGPT** | **실행 가능성 필터링**, EV 계산, 비용 이후 기대값 | 가장 세분화된 플레이북 |

### 4.3 권장 통합 방향

1. **철학/원칙**: 4개 문서 공통 요소 + Anthropic의 비대칭 분류
2. **종목 선정**: Gemini의 Float/RVOL 기준 + ChatGPT의 희석 리스크 체크
3. **플레이북**: ChatGPT의 7개 패턴을 기반으로, Perplexity의 숏 전략 추가
4. **시스템 구현**: Gemini의 Dilution Checker + ChatGPT의 4단 시스템
5. **리스크 관리**: Anthropic의 스탑 유형 분류 채택

---

## 5. 참조 문서

- [perp.md](./perp.md) - Perplexity 전략서
- [gem.md](./gem.md) - Gemini Pro 전략서
- [anth.md](./anth.md) - Anthropic 전략서
- [cgpt.md](./cgpt.md) - ChatGPT 전략서
