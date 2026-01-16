# MaxCapSizingModule 명세서

> **버전**: v1.0
> **작성일**: 2026-01-14
> **기반 문서**: `sizing_logic_discussion.md` (84턴 토론 합의 결과)

---

## 1. 모듈 개요

### 목적
**"가격에 영향을 주지 않는 최대 주문 수량"** 을 계산한다.

### 호출 시점
- 진입 신호 발생 시 **1회**
- 추가매수 신호 발생 시 **별도 1회**
- 포지션 보유 중 재계산 **하지 않음**

### 출력
- `Q_max_shares`: 최대 주문 가능 주수 (정수)
- `L`: 업데이트된 유동성 속도 (다음 호출에 전달)

---

## 2. 입력 인터페이스

```python
def calculate_max_size(
    bid: float,           # 최우선 매수 호가
    ask: float,           # 최우선 매도 호가
    mid: float,           # (bid + ask) / 2
    last_price: float,    # 마지막 체결가
    last_size: int,       # 마지막 체결 수량 (주)
    dt: float,            # 마지막 체결로부터 경과 시간 (초)
    L_prev: float,        # 이전 유동성 속도 ($/초)
    Float: int,           # 유통 주식 수
    tod: str,             # 시간대 코드 ("OPN", "DEAD" 등)
    current_position: int = 0  # 현재 보유 주수 (추가매수 시)
) -> tuple[int, float]:
    """
    Returns:
        Q_max_shares: 최대 주문 가능 주수 (0이면 거래 금지)
        L: 업데이트된 유동성 속도
    """
```

---

## 3. 설정 파라미터

### 3.1 시간 파라미터

| 이름 | 기본값 | 단위 | 설명 |
|------|--------|------|------|
| `TAU_IN` | 4 | 초 | 진입 실행 시간창 |
| `TAU_OUT` | 2 | 초 | 청산 실행 시간창 |
| `EMA_HALF_LIFE` | 5 | 초 | L 계산용 EMA 반감기 |

### 3.2 임팩트 예산

| 이름 | 기본값 | 단위 | 설명 |
|------|--------|------|------|
| `B_IN_BPS` | 12 | bps | 진입 시 허용 슬리피지 |
| `B_OUT_BPS` | 10 | bps | 청산 시 허용 슬리피지 |

### 3.3 마찰 계수

| 이름 | 기본값 | 단위 | 설명 |
|------|--------|------|------|
| `KAPPA_FLOOR_BPS` | 100 | bps | 마찰 최소값 |
| `K_SPR` | 4 | 배수 | 스프레드 → κ 변환 계수 |

### 3.4 패닉 할인

| 이름 | 기본값 | 설명 |
|------|--------|------|
| `PANIC_DISCOUNT` | 0.4 | 급락 시 유동성 감소율 |

### 3.5 하드 게이트

| 이름 | 기본값 | 단위 | 설명 |
|------|--------|------|------|
| `SPREAD_HARD_MAX_BPS` | 200 | bps | 스프레드 상한 (초과 시 봉쇄) |
| `L_MIN_DOLLAR_PER_SEC` | 100 | $/s | 유동성 하한 (미달 시 봉쇄) |
| `Q_MIN_SHARES` | 100 | 주 | 최소 주문 수량 |
| `NOTIONAL_MIN` | 500 | $ | 최소 주문 금액 |

### 3.6 플로트 캡

| 이름 | 기본값 | 설명 |
|------|--------|------|
| `PHI` | 0.002 | 유통주식 대비 최대 비중 (0.2%) |

### 3.7 시간대 배수

| 코드 | 시간대 | 배수 |
|------|--------|------|
| `PRE` | 장전 (04:00-09:30) | 0.3 |
| `OPN` | 개장 (09:30-10:00) | 1.3 |
| `MID1` | 오전 (10:00-11:30) | 1.0 |
| `DEAD` | 점심 (11:30-14:00) | 0.5 |
| `MID2` | 오후 (14:00-15:30) | 0.8 |
| `CLO` | 마감 (15:30-16:00) | 1.2 |
| `AH` | 장후 (16:00-20:00) | 0.2 |

---

## 4. 알고리즘

### 4.1 의사코드

```python
def calculate_max_size(bid, ask, mid, last_price, last_size, dt, 
                       L_prev, Float, tod, current_position=0):
    
    # === Step 1: 스프레드 계산 ===
    spread_bps = (ask - bid) / mid * 10000
    
    # === Step 2: 유동성 속도 L 업데이트 (EMA) ===
    trade_notional = last_price * last_size
    rate = trade_notional / dt if dt > 0 else 0
    alpha = 1 - exp(-dt / EMA_HALF_LIFE)
    L = alpha * rate + (1 - alpha) * L_prev
    
    # === Step 3: 하드 게이트 ===
    if spread_bps > SPREAD_HARD_MAX_BPS:
        return 0, L  # 스프레드 과대 → 봉쇄
    if L < L_MIN_DOLLAR_PER_SEC:
        return 0, L  # 유동성 부족 → 봉쇄
    
    # === Step 4: 마찰 계수 κ ===
    kappa = max(KAPPA_FLOOR_BPS, K_SPR * spread_bps)
    
    # === Step 5: 시간대 배수 ===
    tod_mult = TOD_MULT.get(tod, 1.0)
    
    # === Step 6: 예상 거래량 ===
    V_in = L * TAU_IN * tod_mult
    V_out = L * TAU_OUT * PANIC_DISCOUNT * tod_mult
    
    # === Step 7: 사이즈 계산 (Square-root law 역산) ===
    Q_in = V_in * (B_IN_BPS / kappa) ** 2
    Q_out = V_out * (B_OUT_BPS / kappa) ** 2
    
    # === Step 8: 플로트 캡 ===
    Q_float_cap = PHI * Float * last_price
    
    # === Step 9: 현재 포지션 차감 (추가매수 시) ===
    current_notional = current_position * last_price
    Q_remaining_cap = max(0, Q_float_cap - current_notional)
    
    # === Step 10: 최종 사이즈 ===
    Q_max_notional = min(Q_in, Q_out, Q_remaining_cap)
    Q_max_shares = int(Q_max_notional / last_price)
    
    # === Step 11: 최소 사이즈 게이트 ===
    if Q_max_shares < Q_MIN_SHARES:
        return 0, L
    if Q_max_notional < NOTIONAL_MIN:
        return 0, L
    
    return Q_max_shares, L
```

---

## 5. 동작 원칙

### 5.1 호출 규칙

| 상황 | 동작 |
|------|------|
| 첫 진입 신호 | `calculate_max_size(current_position=0)` → Q1 확정 |
| 포지션 보유 중 | **재호출 금지** (Q1 유지) |
| 추가매수 신호 | `calculate_max_size(current_position=Q1)` → Q2 계산 |
| 청산 | SizingModule 범위 밖 (ExitModule 담당) |

### 5.2 총 포지션 제한

```
Q_total = Q1 + Q2 + ... ≤ PHI × Float
```

- 추가매수 시 `current_position` 파라미터로 기존 보유분 전달
- 모듈 내부에서 플로트 캡 초과 방지

---

## 6. 반환값 해석

| Q_max_shares | 의미 |
|--------------|------|
| 0 | **거래 금지** (게이트 위반 또는 사이즈 과소) |
| > 0 | 해당 주수까지 진입 가능 |

---

## 7. 상태 관리

### 7.1 모듈 내부 상태
- **없음** (Stateless)
- `L` 값은 외부에서 관리하고 호출 시 전달

### 7.2 외부 상태 (Position 클래스)

```python
class Position:
    ticker: str
    entries: list[Entry]  # 진입 기록
    
@dataclass
class Entry:
    timestamp: datetime
    shares: int
    price: float
    sizing_context: dict  # {L, kappa, spread_bps, ...}
```

---

## 8. 로깅 명세

### 8.1 호출 시 기록

```python
sizing_log = {
    "timestamp": datetime,
    "ticker": str,
    "type": str,  # "initial" | "addon"
    "inputs": {
        "spread_bps": float,
        "L": float,
        "tod": str,
        "current_position": int,
    },
    "computed": {
        "kappa": float,
        "V_in": float,
        "V_out": float,
        "Q_in": float,
        "Q_out": float,
        "Q_float_cap": float,
    },
    "output": {
        "Q_max_shares": int,
        "blocked": bool,
        "block_reason": str | None,  # "spread" | "liquidity" | "size_too_small"
    }
}
```

### 8.2 캘리브레이션용 추가 로그

체결 완료 후 기록:
- `fill_time_sec`: 실제 체결 소요 시간
- `slippage_bps`: 실제 슬리피지
- `actual_shares`: 실제 체결 수량

---

## 9. 캘리브레이션

### 9.1 κ 업데이트 (주간)

```python
kappa_obs = slippage_bps / sqrt(Q_filled / V_actual)
kappa_new = percentile(kappa_obs_list, 80)
```

### 9.2 panic_discount 업데이트 (주간)

```python
panic_obs = actual_exit_volume / expected_volume
panic_new = percentile(panic_obs_list, 30)  # 보수적
```

---

## 10. 테스트 케이스

### 10.1 정상 케이스

```python
# AAPL, 유동성 충분
result, L = calculate_max_size(
    bid=149.95, ask=150.05, mid=150.0,
    last_price=150.0, last_size=500, dt=0.1,
    L_prev=100000, Float=16000000, tod="MID1"
)
assert result > 0
```

### 10.2 봉쇄 케이스 - 스프레드 과대

```python
# 스프레드 3%
result, L = calculate_max_size(
    bid=10.0, ask=10.30, mid=10.15, ...
)
assert result == 0
```

### 10.3 봉쇄 케이스 - 유동성 부족

```python
# L = $50/s (< $100/s)
result, L = calculate_max_size(..., L_prev=50, ...)
assert result == 0
```

### 10.4 추가매수 케이스

```python
# 첫 진입 후 추가매수
Q1, L = calculate_max_size(..., current_position=0)
Q2, L = calculate_max_size(..., current_position=Q1)
assert Q2 < Q1  # 플로트 캡 차감됨
```

---

*문서 끝*
