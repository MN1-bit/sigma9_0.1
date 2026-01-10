# 🎓 Research: Z-Score 최적 Timeframe 토론

> **주제**: Z-Score (zenV/zenP) 계산에 최적인 Timeframe은 무엇인가?  
> **작성일**: 2026-01-02  
> **형식**: 학술 토론 (정립, 반론, 심판)

---

## 📋 배경

현재 구현된 Z-Score는 **20일 일봉(Daily)** 기반이다. 그러나 Sigma9 전략은 **장중 단타(Intraday Day Trading)** 머신이므로, 분봉 기반이 더 적합할 수 있다는 의문이 제기되었다.

### 현재 구현 (Step 4.A.3)
```python
# backend/core/zscore_calculator.py
# 20일 일봉 기반
lookback = 20  # 20 trading days
zenV = (today_volume - avg_20d_volume) / std_20d_volume
zenP = (today_change - avg_20d_change) / std_20d_change
```

### 전략 특성 (MPlan.md)
| Phase | Timeframe | 용도 |
|-------|-----------|------|
| Phase 1: Setup | **20일 일봉** | Accumulation Stage Detection |
| Phase 2: Trigger | **10초~5분** | Ignition Detection |
| Phase 3: Harvest | **실시간 틱** | Trailing Stop |

---

## 🎤 토론

---

### 🔵 **정립 (Proposition)**: 일봉(Daily) 기반이 맞다

> **발언자**: 데일리 애널리스트 (Daily Analyst)

#### 주장 1: 전략 설계와 일치

MPlan.md의 핵심 컨셉은 **"장기적 매집(Accumulation) → 단기적 폭발(Ignition)"** 이다.

```
Phase 1 (Setup): 20일 기준 매집 탐지 → Daily
Phase 2 (Trigger): 실시간 폭발 탐지 → Tick/Minute
```

Z-Score는 **Phase 1의 매집 강도**를 측정하는 지표이므로, 일봉 기반이 맞다.

#### 주장 2: 통계적 유의성

| Timeframe | 샘플 수 (1달) | 신뢰도 |
|-----------|---------------|--------|
| 1분봉 | ~6,000개 (390분×15일) | 높음 |
| 5분봉 | ~1,200개 | 중간 |
| 일봉 | ~20개 | **적절** |

20일 일봉은 **약 1달간의 트레이딩 패턴**을 반영하며, 이는 "세력의 매집 기간"과 일치한다. 분봉은 너무 짧아서 **노이즈**가 많다.

#### 주장 3: 계산 효율성

| Timeframe | API 호출 | DB 크기 |
|-----------|----------|---------|
| 일봉 | 1회/종목 (Grouped Daily) | 작음 |
| 5분봉 | 연속 호출 필요 | 크게 증가 |
| 1분봉 | **API 제한 위험** | 매우 큼 |

Polygon.io Free Tier는 API 호출 제한이 있으므로, 일봉이 현실적이다.

#### 주장 4: masterplan 명시적 정의

MPlan.md Line 446-447:
```markdown
**Z-Score 지표**:
- **zenV** (Normalized Volume): `(current_volume - avg_20d) / std_20d`
- **zenP** (Normalized Price): `(current_price - avg_20d) / std_20d`
```

설계 문서에 이미 **20일(일봉)** 기준으로 명시되어 있다.

---

### 🔴 **반론 (Opposition)**: 분봉(Minute) 기반이어야 한다

> **발언자**: 인트라데이 트레이더 (Intraday Trader)

#### 반론 1: 전략 목적과의 불일치

Sigma9는 **장중 단타 머신**이다. 진입 결정은 **10초~5분** 창에서 이루어진다.

```
Ignition 조건 (MPlan.md 4.1):
- Tick Velocity: 10초 체결 > 1분 평균의 8×
- Volume Burst: 1분 거래량 > 5분 평균의 6×
```

10초, 1분, 5분 단위로 폭발을 탐지하면서, Z-Score만 20일 기준? **시간축 불일치(Temporal Mismatch)**가 발생한다.

#### 반론 2: 매집 vs 폭발의 혼동

Z-Score의 목적이 **"매집 강도"** 측정이라면, 그건 이미 **Accumulation Score** 가 하고 있다.

```python
# 기존 매집 점수 (Step 2.2)
accumulation_score = calculate_watchlist_score()  # 20일 일봉 기반
```

Z-Score (zenV/zenP)가 **Tier 2 Hot Zone**에서 사용된다면, 이는 **"오늘 장중의 이상 징후"** 를 탐지해야 한다. 따라서 **당일 분봉** 기반이 맞다.

#### 반론 3: 실시간 반응성

MPlan.md Line 130:
```markdown
| **Z-Score (zenV/zenP)** | 20일 통계 기반 | Tick 마다 재계산 |
```

"Tick 마다 재계산"하려면, **기준선(평균, 표준편차)** 이 분봉 기반이어야 의미가 있다.

- 일봉 기반: 오늘 하루 동안 zenV가 **거의 변하지 않음** (분자만 변동)
- 분봉 기반: 장중 이상 거래량 발생 시 **즉각 zenV 스파이크**

#### 반론 4: zenV-zenP Divergence 전략 적합성

Step 4.A.4의 목표:
> "High zenV + Low zenP" 조합을 **매집 신호**로 탐지

이 신호가 **당일 장중에 발생**해야 진입에 유용하다. 20일 일봉 기반이면:
- 어제 이미 "매집 완료"된 종목만 포착
- 오늘 막 매집이 시작되는 종목은 **탐지 불가**

---

### ⚖️ **심판 (Arbiter's Verdict)**

> **발언자**: 시스템 아키텍트

#### 핵심 질문
> Z-Score가 측정하려는 것은 **장기적 매집**인가, **단기적 이상 징후**인가?

#### 분석

| 관점 | 일봉 (Daily) | 분봉 (Minute) |
|------|--------------|---------------|
| **측정 대상** | 세력의 장기 매집 | 장중 이상 거래 |
| **시간 축** | 과거 20일 | 당일 장중 |
| **Ignition과의 관계** | 독립적 (배경 정보) | 동기화 (실시간 트리거) |
| **계산 비용** | 낮음 | 높음 (API 제한 주의) |
| **노이즈** | 적음 | 많음 |

#### 결론: **Hybrid Approach (하이브리드)**

**두 지표 모두 유효하지만, 용도가 다르다.**

```
┌─────────────────────────────────────────────────────────────┐
│                    Z-SCORE DUAL TIER                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 zenV_D / zenP_D (Daily)                                 │
│  ├── 용도: 장기 매집 확인 (Phase 1 연장선)                    │
│  ├── 계산: Tier 2 승격 시 1회                                │
│  └── 해석: "이 종목이 최근 20일간 매집 중인가?"               │
│                                                             │
│  ⚡ zenV_M / zenP_M (Intraday - 5분봉 × 78개)                │
│  ├── 용도: 장중 이상 징후 탐지 (Phase 2 보조)                 │
│  ├── 계산: Tier 2 종목만 1분 주기 갱신                       │
│  └── 해석: "오늘 장중 이상한 거래가 발생 중인가?"             │
│                                                             │
│  🔥 Divergence Signal                                        │
│  └── 조건: zenV_M >= 2.0 AND zenP_M < 1.0 (분봉 기반)        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📌 최종 권고안

### Tier 1: Daily Z-Score (현재 구현 유지)
```python
# 매집 배경 점수 (Tier 2 승격 시 1회 계산)
zenV_D = (today_volume - avg_20d_volume) / std_20d_volume
zenP_D = (today_change - avg_20d_change) / std_20d_change
```
- **용도**: 장기 매집 확인
- **갱신 주기**: 하루 1회 또는 Tier 2 승격 시

### Tier 2: Intraday Z-Score (신규 구현 제안)
```python
# 장중 이상 징후 (Tier 2 전용, 1분 주기 갱신)
lookback = 78  # 5분봉 × 78 = 약 6.5시간 (장중 전체)
zenV_M = (current_5m_volume - avg_intraday_vol) / std_intraday_vol
zenP_M = (current_5m_change - avg_intraday_change) / std_intraday_change
```
- **용도**: 장중 이상 거래 탐지
- **갱신 주기**: 1분 또는 5분

### UI 표시 제안
```
Tier 2 테이블 컬럼:
Ticker | Price | Chg% | zenV(D) | zenP(D) | zenV(M) | zenP(M) | Ign | Acc
            ↑            ↑                   ↑
        실시간      일봉 배경점수       분봉 실시간
```

---

## ⏱️ 구현 우선순위

| 순위 | 작업 | 근거 |
|------|------|------|
| 1 | **현재 구현 유지** (Daily Z-Score) | 이미 완성, 매집 배경점수로 유용 |
| 2 | Step 4.A.4 Divergence 먼저 구현 | Daily 기반으로도 MVP 가능 |
| 3 | 향후 Intraday Z-Score 추가 | API 제한 및 성능 검토 후 |

---

## 📚 참고문헌

- MPlan.md §3.3 (Accumulation Stage Detection)
- MPlan.md §4.1 (Ignition Conditions)
- MPlan.md §7.4 (Tiered Watchlist System)
- Technical Analysis: Z-Score in Volume Analysis (Investopedia)

---

---

## 🔬 ADDENDUM: 전략 파일 분석 결과 (2026-01-02)

> 📁 분석 대상: `backend/strategies/seismograph.py`

### Ignition Score 시간 범위

전략 파일을 분석한 결과, **Ignition Score는 이미 초단타 시간 범위를 사용**:

| 신호 | 비교 대상 | 시간 범위 | 코드 위치 |
|------|-----------|-----------|-----------|
| **Tick Velocity** | 10초 체결 vs 60초 평균 | 10s / 60s | Line 815-875 |
| **Volume Burst** | 1분 거래량 vs 5분 평균 | 1m / 5m | Line 877-928 |
| **Price Break** | 현재가 vs 박스권 상단 | 실시간 | Line 930-977 |
| **Buy Pressure** | 매수/매도 비율 | 60초 틱 | Line 979-1030 |

### Accumulation Score 시간 범위

매집 점수는 **일봉(Daily) 기반**으로 설계됨:

| 신호 | 비교 대상 | 시간 범위 | 코드 위치 |
|------|-----------|-----------|-----------|
| **Tight Range** | 5일 ATR vs 20일 ATR | 5d / 20d | Line 675-724 |
| **Accumulation Bar** | 당일 거래량 vs 20일 평균 | 1d / 20d | Line 538-582 |
| **OBV Divergence** | 20일 OBV 기울기 | 20d | Line 584-635 |
| **Volume Dry-out** | 3일 평균 vs 20일 평균 | 3d / 20d | Line 637-673 |

### 🎯 결론: ~~Intraday Z-Score 불필요~~ → **재검토 필요**

> ⚠️ **중요 발견**: MPlan.md Line 457-458에 다음 명시:
> ```
> zenV-zenP Divergence 전략:
> "거래량 폭발(zenV > 2.0) + 가격 미반영(zenP < 0.5)" → 진입 시그널
> ```
> 
> **Divergence가 진입 트리거**로 사용된다면, Daily 기반만으로는 **실시간 반응 불가**!

### 수정된 분석

| 구분 | Ignition | Divergence |
|------|----------|------------|
| **역할** | 틱 레벨 폭발 감지 | 매집 완료 신호 |
| **트리거** | ✅ 진입 트리거 | ✅ **진입 트리거** (masterplan) |
| **시간 범위** | 10초~5분 | **?** |

**문제**: Divergence가 진입 트리거라면, `today_volume`이 **장중 실시간으로 갱신**되어야 함!

### 올바른 구현 방향

```
┌─────────────────────────────────────────────────────────────────────┐
│                    수정된 Z-SCORE 시스템                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📊 Daily Z-Score (zenV_D / zenP_D)                                 │
│  ├── 기준선: 과거 20일 일봉 (avg, std) ← 캐시 가능                   │
│  ├── 오늘값: today_volume ← 🔄 1~5분 주기 실시간 갱신               │
│  │           today_change ← 🔄 실시간 가격 반영                     │
│  └── 용도: Divergence 진입 시그널                                   │
│                                                                     │
│  ⚡ Ignition Score                                                   │
│  └── 10초~5분 틱 기반 (기존 유지)                                    │
│                                                                     │
│  🔥 진입 조건 (OR)                                                   │
│  ├── Ignition ≥ 70                                                  │
│  └── Divergence: zenV_D ≥ 2.0 AND zenP_D < 0.5                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 🔴 Intraday Z-Score 여전히 불필요한 이유

**분봉 기반 별도 Z-Score (zenV_M / zenP_M)는 불필요**:
- Daily Z-Score의 `today_volume`을 **실시간 갱신**하면 충분
- 기준선(20일 avg/std)은 일봉 기반 유지
- 오늘값만 실시간 반영 → **"실시간 Daily Z-Score"**

### ✅ 최종 권고안 (수정)

| 항목 | 권고 | 구현 |
|------|------|------|
| Daily Z-Score 기준선 | 20일 일봉 | 1시간 캐시 |
| Daily Z-Score 오늘값 | **실시간 갱신** | 1~5분 주기 |
| 별도 Intraday Z-Score | ❌ 불필요 | - |
| Divergence 진입 | ✅ 구현 필요 | zenV ≥ 2.0 AND zenP < 0.5 |

---

> **"The baseline stays daily (20 days), but today's value updates in real-time.  
> This gives you 'real-time Daily Z-Score' - best of both worlds."**

---

---

# 🎓 DEBATE 2: 매매 시그널용 Z-Score에 Intraday 기준선이 필요한가?

> **주제**: Daily 기준선 + 실시간 오늘값 vs 완전한 Intraday Z-Score  
> **작성일**: 2026-01-02 11:44  
> **트리거**: 사용자 질문 - "매매 시그널로 쓸거면 빠른 시간프레임의 z-score가 따로 필요하지 않나?"

---

## 📋 논쟁 배경

이전 ADDENDUM에서 다음과 같이 결론 내림:
> "Daily Z-Score의 today_volume을 실시간 갱신하면 충분. 별도 Intraday Z-Score 불필요."

**사용자 반박**:
> "아무리 생각해봐도 매매 시그널로 쓸거면 빠른 시간프레임의 z-score 계산이 따로 필요할 것 같다. 20일 평균이랑 비교하는건 너무 느리다."

---

## 🎤 토론 2

---

### 🔵 **정립 (Proposition)**: Intraday 기준선이 필요하다

> **발언자**: 사용자 (단타 트레이더)

#### 주장 1: 기준선의 민감도 문제

**Daily 기준선의 한계**:
```
zenV = (today_volume - avg_20d) / std_20d
            ↑                    ↑
       실시간 갱신           고정값 (1시간 캐시)
```

20일 avg/std는 **장기 트렌드**를 반영한다. 
오늘 갑자기 거래량이 폭발해도:
- avg_20d = 1,000,000 (20일 평균)
- std_20d = 200,000 (20일 표준편차)
- today_volume = 1,500,000 (오늘 누적)

→ zenV = (1,500,000 - 1,000,000) / 200,000 = **2.5**

**문제**: 장 초반(10:00 AM)에 이미 1.5M 거래됐다면, 이건 **진짜 이상 징후**다!
하지만 20일 기준선은 "어제 하루 전체 거래량"과 비교하므로,
**장 초반의 폭발 신호를 놓칠 수 있다.**

#### 주장 2: 시간 흐름에 따른 왜곡

| 시간 | today_volume | zenV (Daily 기준) | 실제 상황 |
|------|-------------|-------------------|-----------|
| 09:45 | 500K | 2.5 | 🔥 15분 만에 평소 1시간치! |
| 12:00 | 800K | 4.0 | 📈 계속 높음 |
| 15:30 | 1.2M | 6.0 | 📊 하루 평균 초과 |

**장 초반 zenV 2.5** vs **장 마감 zenV 6.0**
→ 같은 "이상 징후 수준"이라도 **시간에 따라 숫자가 달라짐**

**Intraday 기준선**이라면:
```
zenV_M = (current_5m_vol - avg_today_5m) / std_today_5m
```
→ "평소 이 시간대 대비 지금이 이상한가?"를 측정 가능

#### 주장 3: 진입 타이밍의 정밀도

**매매 시그널로 사용한다면**:
- Daily Z-Score: "오늘 하루가 끝나야 의미가 명확함"
- Intraday Z-Score: "지금 이 순간이 비정상인지 즉시 판단"

Ignition은 10초~5분 창을 사용한다. 
Divergence 진입도 **비슷한 시간 해상도**가 필요하다.

#### 주장 4: 기존 Ignition과의 역할 분리

| 지표 | 측정 대상 | 기준선 |
|------|-----------|--------|
| Ignition (Volume Burst) | 1분 vs 5분 평균 | 5분 |
| Divergence (zenV) | 오늘 vs **?** | 20일? Intraday? |

Ignition의 Volume Burst: `1분 거래량 > 5분 평균 × 6`
→ 이미 **분봉 기반 Z-Score와 유사**한 개념!

Divergence가 **Ignition과 다른 인사이트**를 제공하려면,
**다른 시간 범위의 기준선**이 필요하다.

---

### 🔴 **반론 (Opposition)**: Daily 기준선 + 실시간 오늘값으로 충분하다

> **발언자**: 시스템 아키텍트

#### 반론 1: Daily 기준선의 본래 목적

Z-Score Divergence의 **핵심 컨셉**:
> "최근 20일 동안의 정상적인 패턴 대비, 오늘이 비정상인가?"

이 질문에 답하려면 **20일 기준선**이 맞다.
Intraday 기준선은 "오늘 대비 지금"을 비교하므로, **다른 질문**에 답한다.

#### 반론 2: Ignition과의 중복 문제

Intraday Z-Score를 도입하면:
```
zenV_M = (current_5m_vol - avg_today_5m) / std_today_5m
```

이것은 **Ignition의 Volume Burst와 거의 동일**:
```
volume_burst = current_1m_vol > avg_5m_vol × 6
```

**굳이 같은 것을 두 번 계산할 필요가 있는가?**

#### 반론 3: 복잡도 vs 가치

| 구현 | 복잡도 | 추가 가치 |
|------|--------|-----------|
| Daily 기준선 + 실시간 오늘값 | 낮음 | "20일 대비 오늘 이상" |
| Intraday 기준선 추가 | 높음 | Ignition과 유사 |

**ROI(투자 대비 효과)가 낮다.**

#### 반론 4: 시간 정규화로 해결 가능

장 초반 zenV 왜곡 문제는 **시간 정규화**로 해결 가능:
```python
# 장 경과 시간 비율로 정규화
elapsed_ratio = (now - market_open) / trading_hours  # 0.0 ~ 1.0
expected_volume = avg_20d_vol * elapsed_ratio
zenV_normalized = (today_volume - expected_volume) / (std_20d_vol * elapsed_ratio)
```

→ "이 시간까지 **예상 누적 거래량** 대비" 비교

---

### ⚖️ **심판 (Arbiter's Verdict)**

> **발언자**: 제3자 전문가

#### 핵심 질문

**Divergence가 측정하려는 것은 무엇인가?**

| 해석 | 적합한 기준선 | 구현 |
|------|---------------|------|
| A: "20일 대비 오늘 하루" | Daily | 현재 구현 |
| B: "오늘 대비 지금 이 순간" | Intraday | 신규 필요 |
| C: "이 시간대 대비 지금" | 시간 정규화 Daily | 중간 |

#### 분석: 세 가지 옵션

**Option A: Daily 기준선 유지 (현재)**
```
장점: 단순, 이미 구현됨, "장기 매집" 컨셉에 부합
단점: 장 초반/마감 왜곡, 시간 해상도 낮음
```

**Option B: Intraday 기준선 추가**
```
장점: 실시간 민감도, "지금 이 순간" 판단 가능
단점: Ignition과 중복, 복잡도 증가, API 비용
```

**Option C: 시간 정규화 Daily (하이브리드)**
```
장점: Daily 단순성 유지하면서 시간 왜곡 보정
단점: 구현 복잡도 약간 증가
공식: zenV = (today_volume - (avg_20d × elapsed_ratio)) / (std_20d × sqrt(elapsed_ratio))
```

#### 🎯 최종 판정

**Intraday Z-Score는 Ignition과 중복되므로 불필요.**

그러나 **사용자의 우려는 타당**:
- Daily 기준선만으로는 **장 초반 이상 징후 민감도**가 떨어짐

**권고: Option C (시간 정규화 Daily) 채택**

```python
def calculate_zscore_realtime(
    ticker: str,
    today_volume: int,
    today_change: float,
    avg_20d_vol: float,
    std_20d_vol: float,
    elapsed_ratio: float  # 0.0 (장 시작) ~ 1.0 (장 마감)
) -> tuple[float, float]:
    """
    시간 정규화된 Daily Z-Score
    
    장 초반에도 정확한 이상 징후 탐지 가능
    """
    # 이 시간까지 예상 누적 거래량
    expected_vol = avg_20d_vol * elapsed_ratio
    # 비례 표준편차
    adjusted_std = std_20d_vol * math.sqrt(elapsed_ratio)
    
    if adjusted_std > 0:
        zenV = (today_volume - expected_vol) / adjusted_std
    else:
        zenV = 0.0
    
    # zenP도 유사하게 처리
    # ...
    
    return zenV, zenP
```

---

## ✅ 결론 (DEBATE 2)

| 항목 | 결정 | 근거 |
|------|------|------|
| 별도 Intraday Z-Score | ❌ 불필요 | Ignition과 중복 |
| Daily 기준선 | ✅ 유지 | "20일 대비 오늘" 컨셉 |
| 시간 정규화 | ✅ **추가 구현** | 장 초반 민감도 보정 |

### Step 4.A.4 계획 수정

```diff
  Phase A:
    4.A.4.1: Daily Z-Score 실시간 갱신
+           + elapsed_ratio 시간 정규화 추가
    4.A.4.2: DivergenceDetector 클래스 구현
    4.A.4.3: GUI Acc 컬럼 + 매집 신호 시각화

- Phase B: Intraday Z-Score (향후 구현)
+ Phase B: (Intraday Z-Score 제거 - Ignition과 중복)
```

---

> **"The user's concern is valid: early-session sensitivity matters.  
> Solution: Time-normalized Daily Z-Score, not a separate Intraday Z-Score."**
