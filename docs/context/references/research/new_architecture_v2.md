# 🏗️ Sigma9 Architecture V2: "The Pre-Ignition Hunter"

> **Core Philosophy**: "Catch the spark before the fire."
> **Objective**: 오늘 폭발할 종목을 감지하여 **미리 진입(Pre-positioning)**하고, 폭발 시 **수확(Harvest)**한다.
> **Anti-Pattern**: 이미 폭발한 뒤에 따라 들어가는 뇌동매매(Chasing)를 금지한다.

---

## 1. The Broken Premise (V1 문제점)

기존 V1 아키텍처는 "단타 기계"라는 명분 아래 **Ignition(폭발)**에만 너무 집중했습니다.
하지만 10~20% 급등한 뒤에 들어가는 것은 리스크가 크고 먹을 폭이 적습니다.

> **"진정한 엣지(Edge)는 남들이 모를 때(Quiet) 진입해서, 남들이 열광할 때(Loud) 파는 것이다."**

---

## 2. The New Workflow: "Scout & Strike"

아키텍처를 **3단계 진입/청산 프로세스**로 재설계합니다.

```mermaid
graph LR
    A[Market Open] -->|Scanning| B(Z-Score Divergence)
    B -->|Trigger 1| C{Scout Entry}
    C -->|Wait/Monitor| D{Ignition?}
    D -->|Yes (Explosion)| E[Add Position & Harvest]
    D -->|No (False Alarm)| F[Time-Stop Exit]
```

### Phase 1: The Ambush (매복) - "Scout Entry"
*   **Trigger**: **Real-time Daily Z-Score Divergence**
    *   `zenV (Volume) > 2.0` (거래량은 이미 터졌다)
    *   `zenP (Price) < 0.5` (가격은 아직 안 올랐다)
*   **Action**: **정찰병 투입 (Scout Entry)**
    *   전체 시드의 30%만 진입.
    *   **근거**: "거래량이 터졌는데 가격이 안 오른다는 건, 누군가 물량을 흡수하고 있다는 강력한 징후(Accumulation)다. 곧 가격이 따라갈 것이다."

### Phase 2: The Confirmation (확인) - "Pyramiding"
*   **Trigger**: **Ignition Score > 70**
    *   Tick Velocity 급증, Price Breakout 발생.
*   **Action**: **본대 투입 (Add Position)**
    *   나머지 시드 70% 투입 (불타기).
    *   평단가는 높아지지만, **상승 확신**이 생긴 시점이므로 리스크는 낮다.

### Phase 3: The Harvest (수확) - "Trailing Stop"
*   **Trigger**: Trailing Stop or Target Hit
*   **Action**: 전량 청산.

---

## 3. Technical Requirements (기술적 요구사항)

이 전략을 실행하기 위해 **"Real-time Daily Z-Score"**가 핵심 엔진이 됩니다.

### A. Real-time Daily Z-Score Engine (New Core)
별도의 Intraday Z-Score를 만들지 않고, **Daily 데이터의 실시간성**을 극대화합니다.

1.  **Baseline (기준선)**: `avg_20d`, `std_20d` (장 시작 전 고정)
2.  **Live Inputs (실시간)**:
    *   `today_volume_realtime`: 1분마다 T 채널 집계 or Polygon Snapshot
    *   `elapsed_ratio`: 장 진행률 (0.0 ~ 1.0)
3.  **Time-Normalized Formula**:
    *   단순히 `(today - avg) / std`로 하면 장 초반에 수치가 너무 낮게 나옴.
    *   **Time-Projection**: "지금 속도라면 장 마감 때 얼마가 될까?"를 예측하여 Z-Score 계산.
    *   `projected_volume = current_volume / elapsed_ratio`
    *   `zenV_projected = (projected_volume - avg_20d) / std_20d`

### B. The Sniper Scanner (Monitoring)
모든 종목을 다 계산할 수 없으므로, **"Smart Sampling"** 전략을 사용합니다.

1.  **Broad Scan (1000개)**: 개장 직전, 전일 기준 잠재력 있는 1000개 로딩.
2.  **Active Scan (100개)**: 장중 `top_gainers`나 `volume_leaders`에 뜨는 종목을 실시간으로 가져와서 **즉시 Z-Score 계산**.
3.  **Target Lock (Watchlist)**: `zenV > 2.0` & `zenP < 0.5` 발견 시 즉시 Watchlist 등록 및 알림.

---

## 4. Implementation Roadmap (Re-alignment)

이 아키텍처를 구현하기 위해 기존 계획을 수정합니다.

### Step 1: Z-Score Engine Upgrade
*   [ ] `ZScoreCalculator`에 **Time-Projection Logic** 추가. (`calculate_projected_zscore`)
*   [ ] `MarketDB`와 연동하여 실시간 `today_volume` 주입 구조 확보.

### Step 2: Divergence Scanner
*   [ ] **Scanner**가 주기적으로(1분) `Snapshot API`를 호출하여 전체 시장의 Volume/Price 확인.
*   [ ] 조건 만족 시 `PotentialCandidate` 생성.

### Step 3: Execution Logic Update (Scout Strategy)
*   [ ] `TradingEngine`에 "Scout Entry" 모드 추가. (Ignition 없이도 Z-Score만으로 진입 가능하도록)

---

## 5. Why This is Better

1.  **철학적 일치**: "폭발 전에 산다"는 Sigma9의 존재 이유를 충족.
2.  **수익률 극대화**: 급등 초입(바닥)에서 잡으므로 R/R(손익비)가 압도적으로 좋음.
3.  **심리적 안정**: 급등하는 말에 올라타는 공포(FOMO)가 아니라, 미리 길목을 지키는(Sniper) 매매.

> **"We don't chase the explosion. We light the fuse."**
> **(우리는 폭발을 쫓지 않는다. 우리가 도화선에 불을 붙인다.)**
