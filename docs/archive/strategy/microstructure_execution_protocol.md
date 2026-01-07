네, 가능합니다. 아래는 **"Microstructure Execution Protocol (MEP)"**를 **Scan → Watchlist → Execution → Update → Exit** 파이프라인으로 **규칙(Standards/Criteria)** 형태로 정리한 것입니다.

---

# 0) Protocol Definitions

## State Machine (Status)

* **S0 = Ignore** (Garbage)
* **S1 = Watch** (Potential)
* **S2 = Prime** (Imminent)
* **S3 = EntryWindow** (Trigger Available)
* **S4 = InPosition** (Active)
* **S5 = Cooldown** (Penalty Box)

## Key Inputs (The 8 Micro-Factors)

1.  **RelVol / $VolVelocity** (Liquidity Surge)
2.  **Volatility Regime** (Gap% or ATR/Range)
3.  **OFI (Order Flow Imbalance) / Depth**
4.  **Tick-Velocity** (Frequency)
5.  **Key Levels** (PMH, HOD, VWAP, Round Numbers)
6.  **Spread Compression** (Cost Reduction)
7.  **Spread%** (Immediate Cost)
8.  **ChasePenalty** (Volatility Overheat Metrics)

## Update Cycle

*   **Base Cycle**: 5s (Scanning)
*   **Prime Cycle**: 1s (Monitoring)
*   **Execution Cycle**: Tick-based (Triggering)

---

# 1) SCAN 규칙 (Universe → Candidates)

## 목적

* “애초에 안 뛸 확률이 큰 종목”을 **가벼운 비용으로 제거**하고,
* Watch 후보를 최소화

## 입력

* (1) RelVol/$VolVelocity
* (2) 갭% 또는 ATR/Range 레짐

## 규칙

### SCAN-1: 유동성/관심 필터

* **RelVol 또는 $VolVelocity**가 “평소 대비 유의미하게 높아야” 후보
* 수용기준(개념): 상위 퍼센타일/지정 임계치 이상

### SCAN-2: 움직일 체질 필터

* **갭% 또는 ATR/Range 레짐**이 “낮지 않아야” 후보
* 수용기준: 당일 레인지가 매우 낮거나 갭/변동성 레짐이 죽어있으면 제외

### SCAN-3: 거래 불능 필터(초경량)

* Spread%가 “극단적으로 큰” 종목은 제외(초기부터 비용 폭탄)

## 출력

* **Candidates 리스트**(S1=Watch로 넘김)

---

# 2) WATCHLIST 규칙 (Candidates → Watch/Prime 전환)

## 목적

* 후보를 “지금 곧 터질 가능성” 순으로 정렬하고,
* 미시구조 임박(λ₂)을 감지하면 Prime으로 올림

## 입력

* (3) OFI/Depth
* (4) Tick-velocity
* (7) Spread%
* (8) ChasePenalty

## 규칙

### WATCH-1: Watch 진입(상태 S1)

* SCAN 통과 종목은 기본 S1

### WATCH-2: Prime 진입(상태 S2)

* **OFI/Depth 상승 + Tick-velocity 상승**이 동시 발생하면 “임박”
* 단, **지속조건** 필수:

  * 둘 중 하나가 스파이크로 1회 튄 건 무시
  * 수용기준(개념): “연속 K회(예: 3~5틱) 또는 T초 이상 유지”

### WATCH-3: Prime 유지/해제(히스테리시스)

* Prime 유지 임계치(낮은 기준)와 Prime 진입 임계치(높은 기준)를 분리
* OFI/Depth나 TickVel이 일정 수준 아래로 내려가면 S1로 복귀

### WATCH-4: 거래가능성 게이트(미리 차단)

* Prime 상태라도 아래면 EntryWindow로 못 감:

  * Spread% 과다(비용)
  * ChasePenalty 과다(추격 과열)

## 출력

* **Watchlist(정렬)**: Ready(임박) 높은 순
* Prime 종목은 1초 업데이트로 승격

---

# 3) ORDER (BUY) 규칙 (EntryWindow에서만 발동)

## 목적

* “돌파 직전/초입”의 **먹을 수 있는 창**에서만 진입

## 입력

* (5) 핵심 레벨(1~2개)
* (6) Spread 축소
* (3)(4) 임박 유지(OFI/Depth, TickVel)
* (7)(8) 비용/과열 필터

## EntryWindow 정의 (상태 S3)

### BUY-0: EntryWindow 조건

* Prime(S2) 유지 중이며,
* **레벨 근접/접촉/돌파**가 발생하고,
* 동시에 **스프레드가 축소**(또는 최소한 악화되지 않음)
* 그리고 Trade 필터 통과:

  * Spread% 허용 범위
  * ChasePenalty 낮음

## BUY 실행 규칙

### BUY-1: 트리거(진입 시점)

* 레벨 “터치 직전~터치/돌파 초입” 중 **가장 일관된 1개만 선택**

  * 보수적: “돌파 확인(레벨 상단 체결/유지)” 후 진입
  * 공격적: “근접 + 임박 강도 최상”일 때 선진입
* (효율 스윗스팟 추천): **돌파 초입(확인 1틱)**

  * 이유: 너무 이르면 훼이크, 너무 늦으면 비용↑

### BUY-2: 주문 형태(원칙만)

* 비용이 낮을수록(Spread% 낮고 Depth 괜찮으면) 더 공격적으로
* Spread가 크거나 Depth가 얕으면 “체결 우선 vs 가격 우선” 정책을 보수적으로

### BUY-3: 진입 무효 조건(발동 직전 취소)

* 레벨 근접인데 **TickVel이 꺼지거나 OFI/Depth가 꺾이면** 취소
* 스프레드가 갑자기 벌어지면 취소
* ChasePenalty가 급등하면 취소

## 상태 전이

* 체결되면 **S4(InPosition)**
* 실패/훼이크면 **S5(Cooldown)**

---

# 4) UPDATE 규칙 (포지션 보유 중 모니터링)

## 목적

* 시간 기준이 아니라 **강도(λ₂)**와 **과열(ChasePenalty)** 변화로 관리
* “확장 유지”만 먹고, 꺾이면 빠르게 이탈

## 입력

* (3) OFI/Depth
* (4) Tick-velocity
* (8) ChasePenalty
* (5) 레벨 재이탈 여부(돌파 실패 판단)

## 규칙

### UPDATE-1: 유지 조건(상승 지속)

* OFI/Depth가 유지/상승 + TickVel 유지/상승이면 홀드
* (선택) 이익 보호를 위해 점진적으로 리스크 축소

### UPDATE-2: 경고 조건(약화 시작)

* OFI/Depth가 하락 전환하거나,
* TickVel이 급감하거나,
* ChasePenalty가 급등(추격 과열, 변동성 폭발)

### UPDATE-3: 실패 조건(돌파 실패)

* 레벨을 돌파했는데 **재이탈(레벨 아래로 복귀) + 임박 신호 약화**가 같이 나오면 즉시 위험

---

# 5) ORDER (SELL) 규칙 (청산)

## 목적

* “손실 최소 + 기대값 유지”
* **시간 기반 청산 금지**(효율 관점에서 불리)
* 대신 **강도 기반/구조 기반**으로 청산

## SELL-1: 즉시 청산(손절/실패)

* 돌파 실패(레벨 재이탈) AND (OFI/Depth 하락 OR TickVel 급감)
* Spread가 급확대(체결 리스크 급증)
* ChasePenalty 폭발(과열/변동성 폭발로 기대값 붕괴)

## SELL-2: 이익 청산(확장 종료)

* OFI/Depth와 TickVel이 동시에 꺾이는 “확장 종료” 시그널
* 또는 “추격 과열”이 임계치 초과하며 위험 급증

## SELL-3: 트레일(선택)

* 확장이 강할 때는 “강도 유지”를 조건으로 트레일링
* 강도 약화 시 즉시 종료

## 상태 전이

* 청산 후 **S5(Cooldown)**

---

# 6) COOLDOWN 규칙 (과매매 방지, 효율 핵심)

## 목적

* 같은 종목에서 훼이크 반복으로 비용/손실 누적 방지

## 규칙

* 실패/손절 후 일정 기간 **재진입 금지**
* 재진입 허용 조건:

  * 임박(OFI/Depth + TickVel)이 다시 “지속”으로 회복
  * Spread%/ChasePenalty 정상화
  * 레벨 재도전 구조가 새로 형성

---

# 7) 출력/운영 산출물(필수)

* **Scan 리스트**: Prior-lite 기준 통과 종목
* **Watchlist**: Ready(임박) 점수 순 정렬
* **Prime 리스트**: 1초 업데이트 대상
* **EntryWindow 알림**: 진입 가능 창
* **InPosition 모니터**: 강도 약화/실패/과열 경고
* **Cooldown 리스트**: 재진입 금지 종목

---


---

# 🔬 ADDENDUM: Sigma9 Architecture V2 정합성 분석 (2026-01-02)

> **평가 대상**: [trading_rules_sweet_spot.md](./trading_rules_sweet_spot.md) "최고 효율 스윗스팟 규칙"
> **비교 대상**: [new_architecture_v2.md](../references/research/new_architecture_v2.md) "Scout & Strike Philosophy"

이 문서는 Sigma9 Architecture V2의 **"Scout & Strike" 철학**을 구체적인 **전술(Tactics)** 수준에서 완벽하게 보완합니다. 두 문서는 상충하지 않으며, 오히려 필수적인 상호보완 관계에 있습니다.

## 1. 정합성 매핑 (Alignment Mapping)

| Architecture V2 (Strategy) | Sweet Spot Rules (Tactics) | 정합성 평가 |
| :--- | :--- | :--- |
| **Sourcer (Scanning)** | **SCAN 규칙 (1-3)** | ✅ **완벽 일치**<br>- Arch V2의 "Source A/B"가 SCAN-1/2에 해당.<br>- RelVol 및 변동성 필터가 초기 후보군을 효율적으로 압축함. |
| **Ranker (Watchlist)** | **WATCHLIST 규칙 (1-4)** | ✅ **고도화**<br>- Arch V2의 단순 "Ignition Rank"를 "OFI + TickVel" 기반의 **S2(Prime)** 상태로 구체화.<br>- "임박(Ready)" 개념을 도입하여 감시 효율 극대화. |
| **Trigger 1 (Scout)** | **WATCH-2 (Prime 진입)** | 🔄 **보완 필요**<br>- Arch V2의 "Z-Score Divergence" 진입을 이 규칙의 **S2(Prime)** 상태 진입 신호로 매핑 가능.<br>- Divergence를 "임박 신호"의 강력한 근거(OFI 대체재)로 활용 가능. |
| **Trigger 2 (Strike)** | **ORDER-BUY 규칙 (1-3)** | ✅ **완벽 일치**<br>- Arch V2의 "Ignition > 70"을 "레벨 돌파 + 스프레드 축소 + 8요소"로 정밀 타격화.<br>- 뇌동매매를 막고 "확률 높은 돌파"만 골라내는 핵심 필터. |
| **Harvest (Exit)** | **ORDER-SELL 규칙 (1-3)** | ✅ **업그레이드**<br>- 단순 Trailing Stop을 넘어, **"강도 약화(OFI/TickVel 꺾임)"** 시 선제적 청산 가능.<br>- 수익 보존 극대화. |

## 2. 시너지 효과 (Synergy)

이 규칙을 적용함으로써 얻는 Architecture V2의 이점:

1.  **Scout Entry의 정밀도 향상**:
    *   단순히 `zenV-zenP` 숫자만 보고 들어가는 것이 아니라, **SCAN-2(체질 필터)**와 **WATCH-4(거래가능성)**를 통과한 종목만 Scout 진입.
    *   → "가짜 매집(Fake Accumulation)" 필터링.
2.  **Ignition 오작동 방지**:
    *   Ignition Score가 높아도 **Spread% 과다**하거나 **ChasePenalty**가 높으면 진입 차단.
    *   → "고점 추격(Chasing)" 방지.
3.  **자본 효율성 극대화**:
    *   **COOLDOWN 규칙**을 통해, 실패한 종목에 계속 돈을 태우는 것을 방지.
    *   → Arch V2의 "Sniper" 철학(한 발 한 발 신중하게)과 일치.

## 3. 결론 및 권고

> **"Architecture V2가 '무엇(What)'을 할지 정한다면, 이 문서는 '어떻게(How)' 할지를 정의한다."**

*   **채택 여부**: **[승인]**
*   **적용 방안**:
    *   이 규칙을 **Sigma9 Trading Engine의 "Microstructure Filter"** 모듈로 구현.
    *   `Scout Entry`와 `Strike Entry` 실행 전, 이 규칙의 **CHECKLIST**를 통과해야만 주문 발송.
    *   파일명 변경: `trading_rules_sweet_spot.md` (완료)

