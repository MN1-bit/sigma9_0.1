# Ignition Score 계산 수식

**문서 유형**: 기술 명세  
**작성일**: 2026-01-06

---

## 개요

Ignition Score는 **실시간 폭발 신호**를 측정하는 점수입니다.  
틱 데이터 및 분봉 데이터를 분석하여 급등 직전의 신호를 감지합니다.

---

## 최종 점수 계산

$$
\text{Ignition Score} = \sum_{i} (w_i \times I_i)
$$

**where:**
- $w_i$ = 신호 $i$의 가중치 (총합 100%)
- $I_i$ = 신호 $i$의 강도 (0.0 ~ 1.0)

---

## 가중치 (Weights)

| 신호 | 가중치 | 조건 | 의미 |
|------|--------|------|------|
| Tick Velocity | **35%** | 10초 체결 > 1분 평균 × 8 | 체결 속도 폭발 |
| Volume Burst | **30%** | 1분 거래량 > 5분 평균 × 6 | 거래량 폭발 |
| Price Break | **20%** | 현재가 > 박스권 상단 + 0.5% | 박스권 돌파 |
| Buy Pressure | **15%** | 매수/매도 비율 > 1.8 | 매수 우세 |

---

## 개별 신호 강도 계산

### 1. Tick Velocity (체결 속도)

**의미**: 갑자기 체결이 빨라지는 것을 감지

$$
\text{Ticks}_{10s} = \text{최근 10초 체결 횟수}
$$

$$
\text{Avg}_{10s} = \frac{\text{Ticks}_{60s}}{60} \times 10
$$

**점수 기준**:
| 조건 | $I_{\text{TV}}$ |
|------|-----------------|
| $\text{Ticks}_{10s} > \text{Avg}_{10s} \times 8$ | 1.0 |
| $\text{Ticks}_{10s} > \text{Avg}_{10s} \times 4$ | 0.5 |
| 그 외 | 0.0 |

---

### 2. Volume Burst (거래량 폭발)

**의미**: 갑자기 거래량이 폭발하는 것을 감지

$$
V_{\text{1m}} = \text{최근 1분 거래량}
$$

$$
\bar{V}_{\text{5m}} = \text{이전 5분 평균 거래량}
$$

**점수 기준**:
| 조건 | $I_{\text{VB}}$ |
|------|-----------------|
| $V_{\text{1m}} > \bar{V}_{\text{5m}} \times 6$ | 1.0 |
| $V_{\text{1m}} > \bar{V}_{\text{5m}} \times 3$ | 0.5 |
| 그 외 | 0.0 |

---

### 3. Price Break (가격 돌파)

**의미**: 박스권(횡보 구간)을 돌파하는 것을 감지

$$
P_{\text{current}} = \text{현재가}
$$

$$
\text{Breakout Level} = \text{Box}_{\text{high}} \times (1 + 0.005)
$$

**점수 기준**:
| 조건 | $I_{\text{PB}}$ |
|------|-----------------|
| $P_{\text{current}} > \text{Breakout Level}$ | 1.0 |
| $P_{\text{current}} > \text{Box}_{\text{high}}$ | 0.5 |
| 그 외 | 0.0 |

---

### 4. Buy Pressure (매수 압력)

**의미**: 매수가 매도보다 압도적으로 많은지 감지

$$
\text{Ratio} = \frac{V_{\text{buy}}}{V_{\text{sell}}} \quad (\text{최근 60초 기준})
$$

**점수 기준**:
| 조건 | $I_{\text{BP}}$ |
|------|-----------------|
| $\text{Ratio} > 1.8$ | 1.0 |
| $\text{Ratio} > 0.9$ | 0.5 |
| 그 외 | 0.0 |

---

## 예시 계산

| 신호 | 강도 ($I$) | 가중치 ($w$) | 기여도 |
|------|-----------|-------------|--------|
| Tick Velocity | 1.0 | 35 | 35.0 |
| Volume Burst | 0.5 | 30 | 15.0 |
| Price Break | 1.0 | 20 | 20.0 |
| Buy Pressure | 0.5 | 15 | 7.5 |
| **합계** | | | **77.5** |

$$
\text{Ignition Score} = \mathbf{77.5}
$$

---

## 임계값 (Threshold)

| 조건 | 동작 |
|------|------|
| **Ignition Score ≥ 70** | 🔥 Tier 2 Hot Zone 승격 / 진입 신호 |
| **Ignition Score < 70** | 대기 (모니터링 계속) |

---

## Score V2와의 차이점

| 항목 | Score V2 | Ignition Score |
|------|----------|----------------|
| **데이터 소스** | 일봉 (Daily) | 틱 + 분봉 (실시간) |
| **측정 대상** | 매집 강도 | 폭발 신호 |
| **갱신 주기** | 1일 1회 | 실시간 (틱마다) |
| **사용 목적** | Watchlist 우선순위 | 진입 타이밍 결정 |

---

## 알려진 문제

> [!WARNING]
> 현재 구현에서 각 신호가 0, 0.5, 1.0만 출력함 (연속 스케일 아님)

**원인**:
- 조건 충족 시 1.0, 절반 충족 시 0.5, 미충족 시 0.0의 3단계만 존재
- 임계값 기반 step function 사용

**개선 방안**:
- 선형 보간 도입으로 연속 스케일 구현
- 예: `intensity = clamp((ratio - threshold/2) / threshold, 0, 1)`
