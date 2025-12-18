# Step 3.2: Risk Manager & Position Sizing 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 3 (Execution & Management)  
> **목표**: Kelly Criterion 기반 포지션 사이징 및 Loss Limit 구현

---

## 1. 배경 및 목적

`masterplan.md` Section 10~11에 정의된 **Risk Management**를 구현합니다.

- **Position Sizing**: Kelly Criterion으로 최적 포지션 크기 계산
- **Loss Limits**: 일일/주간 손실 한도 도달 시 자동 정지
- **Kill Switch**: 긴급 청산 기능 (모든 주문 취소 + 전량 청산)

---

## 2. 마스터플랜 요구사항

### 2.1 Position Limits (Section 11.1)

| Parameter | Value |
|-----------|-------|
| Max Position Size | 계좌의 100% |
| Max Concurrent Positions | 3개 |
| Max Daily Trades | 50회 |

### 2.2 Loss Limits (Section 11.2)

| Parameter | Value | Action |
|-----------|-------|--------|
| Per-Trade Stop | -5.0% | OCA Stop Loss |
| Daily Loss Limit | -3% | 봇 자동 정지 |
| Weekly Loss Limit | -10% | 수동 리뷰 |

### 2.3 Kill Switch (Section 11.3)

- 버튼 클릭 시: 모든 미체결 취소 + 전 포지션 청산
- 자동 트리거: Daily Loss Limit 도달 시
- 로깅: 모든 발동 이력 기록

---

## 3. Proposed Changes

### 3.1 Backend Core

#### [NEW] [risk_manager.py](file:///d:/Codes/Sigma9-0.1/backend/core/risk_manager.py)

```
RiskManager
├── __init__(connector, config)
│
├── calculate_position_size(symbol, entry_price) → int
│   └── Kelly Criterion 또는 고정비율 계산
│
├── check_daily_limit() → bool
│   └── 일일 손실 한도 체크 (-3%)
│
├── check_weekly_limit() → bool
│   └── 주간 손실 한도 체크 (-10%)
│
├── is_trading_allowed() → bool
│   └── 거래 가능 여부 (한도, 포지션 수 체크)
│
├── kill_switch() → dict
│   └── 전량 청산 + 모든 주문 취소
│
├── get_daily_pnl() → float
│   └── 금일 실현 손익 계산
│
└── get_account_status() → dict
    └── 계좌 상태 요약
```

#### [NEW] [risk_config.py](file:///d:/Codes/Sigma9-0.1/backend/core/risk_config.py)

리스크 설정 데이터클래스:

| Field | Default | Description |
|-------|---------|-------------|
| `max_position_pct` | 10.0 | 포지션당 최대 비율 (%) |
| `max_positions` | 3 | 최대 동시 포지션 수 |
| `daily_loss_limit_pct` | -3.0 | 일일 손실 한도 (%) |
| `weekly_loss_limit_pct` | -10.0 | 주간 손실 한도 (%) |
| `max_daily_trades` | 50 | 일일 최대 거래 횟수 |
| `use_kelly` | False | Kelly Criterion 사용 여부 |

---

### 3.2 Tests

#### [NEW] [test_risk_manager.py](file:///d:/Codes/Sigma9-0.1/tests/test_risk_manager.py)

| 테스트 | 검증 내용 |
|--------|----------|
| `test_position_size_fixed` | 고정비율 포지션 사이징 |
| `test_daily_loss_check` | 일일 손실 한도 체크 |
| `test_weekly_loss_check` | 주간 손실 한도 체크 |
| `test_kill_switch` | Kill Switch 동작 |
| `test_is_trading_allowed` | 거래 가능 여부 판단 |

---

## 4. Verification Plan

### 4.1 Syntax Check

```powershell
cd d:\Codes\Sigma9-0.1
python -m py_compile backend/core/risk_manager.py
python -m py_compile backend/core/risk_config.py
```

### 4.2 Unit Tests

```powershell
pytest tests/test_risk_manager.py -v
```

---

## 5. 핵심 로직

### Kelly Criterion (간소화 버전)

```python
# f* = (bp - q) / b
# b: 승수 (평균 수익 / 평균 손실)
# p: 승률
# q: 패률 (1 - p)

def calculate_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    b = abs(avg_win / avg_loss) if avg_loss != 0 else 1.0
    p = win_rate
    q = 1 - p
    kelly = (b * p - q) / b
    return max(0, min(kelly, 0.25))  # 0~25% 제한
```

---

## 6. 다음 단계

- **Step 3.3**: Double Tap & Harvest
