# Step 3.2 Report: Risk Manager & Position Sizing

**날짜**: 2025-12-18  
**작업자**: Antigravity Agent

---

## 📋 개요

Step 3.2에서는 리스크 관리 및 포지션 사이징을 구현했습니다.

---

## ✅ 완료 항목

### 3.2.1: RiskManager 클래스

**파일**: `backend/core/risk_manager.py`

| 메서드 | 설명 |
|--------|------|
| `calculate_position_size()` | 포지션 사이즈 계산 |
| `check_daily_limit()` | 일일 손실 한도 체크 |
| `check_weekly_limit()` | 주간 손실 한도 체크 |
| `is_trading_allowed()` | 거래 가능 여부 |
| `kill_switch()` | 긴급 청산 |
| `record_trade()` | 거래 기록 |

### 3.2.2: Kelly Criterion

- `_calculate_kelly_fraction()` 구현
- Fractional Kelly (1/4 Kelly) 지원
- 최소 거래 수 설정 (kelly_min_trades)

### 3.2.3: Loss Limits

| Parameter | Default |
|-----------|---------|
| Daily Loss Limit | -3% |
| Weekly Loss Limit | -10% |
| Per-Trade Stop | -5% |

### 3.2.4: Kill Switch

- 모든 미체결 주문 취소
- 전 포지션 시장가 청산
- 자동 트리거 옵션

---

## 🧪 테스트 결과

```
pytest tests/test_risk_manager.py -v
======================== 24 passed in 0.07s ========================
```

---

## 📁 생성된 파일

| 파일 | 설명 |
|------|------|
| `backend/core/risk_config.py` | 리스크 설정 |
| `backend/core/risk_manager.py` | 리스크 관리자 |
| `tests/test_risk_manager.py` | 테스트 코드 |
| `docs/Plan/steps/step_3.2_plan.md` | 계획 문서 |

---

## 🔜 다음 단계

- **Step 3.3**: Double Tap & Harvest
