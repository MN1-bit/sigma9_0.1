# Step 3.3: Double Tap & Harvest 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 3 (Execution & Management)  
> **목표**: Trailing Stop 및 재진입 로직 구현

---

## 1. 배경 및 목적

`masterplan.md` Section 5에 정의된 **Harvest 및 Double Tap**을 구현합니다.

- **Harvest (Trailing Stop)**: +3% 도달 시 ATR×1.5 Trailing Stop 활성화
- **Double Tap**: 1차 청산 후 조건 충족 시 50% 사이즈로 재진입

---

## 2. 마스터플랜 요구사항

### 2.1 Profit Harvester (Section 5.1)

| Parameter | Value |
|-----------|-------|
| 활성화 조건 | +3% 도달 |
| Trailing Amount | ATR × 1.5 |
| Type | TRAIL |

### 2.2 Double Tap (Section 5.2)

| Step | Condition |
|------|-----------|
| 1. Cooldown | 1차 청산 후 3분 대기 |
| 2. Filter | 주가 > VWAP |
| 3. Trigger | HOD 돌파 시 Stop-Limit @ HOD + $0.01 |
| 4. Size | 1차의 50% |
| 5. Exit | Trailing Stop 1.0% |

---

## 3. Proposed Changes

### 3.1 Backend Core

#### [NEW] [double_tap.py](file:///d:/Codes/Sigma9-0.1/backend/core/double_tap.py)

```
DoubleTapManager
├── __init__(connector, order_manager)
│
├── on_first_exit(symbol, exit_reason, exit_price) → None
│   └── 1차 청산 시 호출 → Cooldown 시작
│
├── check_reentry_conditions(symbol, current_price, vwap, hod) → bool
│   └── 재진입 조건 체크 (Cooldown 완료, 주가 > VWAP, HOD 돌파)
│
├── execute_double_tap(symbol, base_qty) → Optional[int]
│   └── 재진입 실행 (50% 사이즈, Trailing Stop 1.0%)
│
└── cancel_pending_reentry(symbol) → None
    └── 대기 중인 재진입 취소
```

#### [NEW] [trailing_stop.py](file:///d:/Codes/Sigma9-0.1/backend/core/trailing_stop.py)

```
TrailingStopManager
├── create_trailing_stop(symbol, qty, trail_amount) → int
│   └── Trailing Stop Order 생성
│
├── activate_on_profit(symbol, current_price, entry_price, atr) → bool
│   └── +3% 도달 시 Trailing Stop 활성화
│
└── update_trail(symbol, current_price) → None
    └── 고점 갱신 시 Trail 가격 조정
```

---

### 3.2 Tests

#### [NEW] [test_double_tap.py](file:///d:/Codes/Sigma9-0.1/tests/test_double_tap.py)

| 테스트 | 검증 내용 |
|--------|----------|
| `test_cooldown_timer` | 3분 Cooldown 동작 |
| `test_vwap_filter` | VWAP 필터 조건 |
| `test_hod_trigger` | HOD 돌파 트리거 |
| `test_double_tap_size` | 50% 사이즈 계산 |
| `test_trailing_stop_activation` | +3% 도달 시 활성화 |

---

## 4. Verification Plan

```powershell
pytest tests/test_double_tap.py -v
```

---

## 5. 다음 단계

- **Step 3.4**: GUI Control Panel
