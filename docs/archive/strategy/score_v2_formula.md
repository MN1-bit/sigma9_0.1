# Score V2 계산 수식

**문서 유형**: 기술 명세  
**작성일**: 2026-01-06

---

## 개요

Score V2는 주식의 **매집(Accumulation) 강도**를 측정하는 연속 점수 시스템입니다.  
Boolean 신호 대신 0~100 스케일의 연속 점수를 반환합니다.

---

## 최종 점수 계산

$$
\text{Score V2} = 100 \times \sum_{i} (w_i \times I_i)
$$

**where:**
- $w_i$ = 신호 $i$의 가중치
- $I_i$ = 신호 $i$의 강도 (0.0 ~ 1.0)

---

## 가중치 (Weights)

| 신호 | 가중치 | 의미 |
|------|--------|------|
| Tight Range | **30%** | VCP 패턴 (변동성 수축) |
| OBV Divergence | **35%** | 스마트 머니 (기관 매집) |
| Accumulation Bar | **25%** | 매집 완료 (고거래량 + 저변동) |
| Volume Dryout | **10%** | 준비 단계 (거래량 고갈) |

---

## 개별 신호 강도 계산

### 1. Tight Range (변동성 수축)

**의미**: ATR(Average True Range)이 수축하는 VCP 패턴 감지

$$
\text{ratio} = \frac{\text{ATR}_5}{\text{ATR}_{20}}
$$

$$
I_{\text{TR}} = \text{clamp}\left(\frac{0.7 - \text{ratio}}{0.4}, 0, 1\right)
$$

| ratio | $I_{\text{TR}}$ |
|-------|-----------------|
| ≤ 0.30 | 1.0 |
| = 0.50 | 0.5 |
| ≥ 0.70 | 0.0 |

---

### 2. OBV Divergence (스마트 머니)

**의미**: 가격은 하락하지만 OBV(On-Balance Volume)는 상승하는 다이버전스 감지

$$
\Delta_{\text{price}} = \frac{C_{n} - C_0}{C_0} \quad (\text{가격 변화율})
$$

$$
\Delta_{\text{OBV}} = \frac{\text{OBV}_{n} - \text{OBV}_0}{\sum V} \quad (\text{OBV 변화율})
$$

**조건**:
- $\Delta_{\text{price}} > 0.02$ (2% 상승) → $I_{\text{OBV}} = 0$ (다이버전스 아님)
- $\Delta_{\text{OBV}} \leq 0$ (OBV 하락) → $I_{\text{OBV}} = 0$ (다이버전스 아님)

**강도 계산**:

$$
I_{\text{OBV}} = \text{clamp}\left(|\Delta_{\text{price}}| \times 10 + \Delta_{\text{OBV}} \times 5, 0, 1\right)
$$

---

### 3. Accumulation Bar (매집 봉)

**의미**: 가격 변동은 작지만 거래량이 폭발적으로 증가한 봉 감지

**조건**:
- 가격 변동률 $> 2.5\%$ → $I_{\text{AB}} = 0$ (매집봉 아님)

**강도 계산**:

$$
\text{ratio} = \frac{V_{\text{today}}}{\text{Avg}(V_{20})}
$$

$$
I_{\text{AB}} = \text{clamp}\left(\frac{\text{ratio} - 2}{3}, 0, 1\right)
$$

| Volume Ratio | $I_{\text{AB}}$ |
|--------------|-----------------|
| ≤ 2.0x | 0.0 |
| = 3.5x | 0.5 |
| ≥ 5.0x | 1.0 |

---

### 4. Volume Dryout (거래량 고갈)

**의미**: 매집 완료 후 거래량이 급감하는 준비 단계 감지

$$
\text{ratio} = \frac{\text{Avg}(V_3)}{\text{Avg}(V_{20})}
$$

$$
I_{\text{VD}} = \text{clamp}\left(1 - \frac{\text{ratio}}{0.4}, 0, 1\right)
$$

| Volume Ratio | $I_{\text{VD}}$ |
|--------------|-----------------|
| ≥ 40% | 0.0 |
| = 20% | 0.5 |
| ≤ 0% | 1.0 |

---

## 예시 계산

| 신호 | 강도 ($I$) | 가중치 ($w$) | 기여도 |
|------|-----------|-------------|--------|
| Tight Range | 0.50 | 0.30 | 0.150 |
| OBV Divergence | 0.80 | 0.35 | 0.280 |
| Accumulation Bar | 0.00 | 0.25 | 0.000 |
| Volume Dryout | 0.60 | 0.10 | 0.060 |
| **합계** | | | **0.490** |

$$
\text{Score V2} = 100 \times 0.490 = \mathbf{49.0}
$$

---

## 특수 케이스

| Score V2 값 | 의미 |
|------------|------|
| **-1** | 신규/IPO 종목 (일봉 데이터 5일 미만) |
| **0** | 매집 신호 없음 |
| **1~100** | 정상 점수 |

---

## 참고

- **clamp(x, min, max)**: $\max(\min, \min(\max, x))$
- **ATR**: True Range의 이동평균
- **OBV**: On-Balance Volume (가격 방향에 따른 누적 거래량)

---

## 알려진 문제

> [!WARNING]
> 현재 구현에서 일부 신호가 0 또는 1만 출력하는 경향이 있음

### OBV Divergence

**문제점**: 대부분 0 또는 1만 출력됨 (중간값 드문)

**원인**:
1. 조건이 너무 엄격함 (가격 하락 + OBV 상승 동시 충족 필요)
2. 조건 미충족 시 즉시 0 반환
3. 조건 충족 시 강도 계산 수식이 쉽게 1.0에 도달

**개선 방안**:
- 조건 완화: `price_change_pct > 0.02` → `> 0.05`
- 점진적 스케일링 도입

---

### Accumulation Bar

**문제점**: 대부분 0 또는 1만 출력됨 (중간값 드문)

**원인**:
1. 거래량 배수 범위가 너무 좁음 (2x~5x)
2. 실제 데이터에서 배수가 2x 미만(→0) 또는 5x 이상(→1)인 경우가 대부분

**개선 방안**:
- 범위 확대: `(ratio - 2) / 3` → `(ratio - 1.5) / 2.5`
- 하한선을 1.5x로 낮추고 상한선을 4x로 조정
