---
description: StrategyBase 인터페이스 명세 (전략 개발 시 참조)
---

# StrategyBase Interface

> **핵심 변경**: Scanning 로직이 Strategy Layer에 통합됨

## Scanning Layer (Phase 1 & 2)

| Method | Description |
|--------|-------------|
| `get_universe_filter()` | Universe 필터 조건 반환 (가격, 시가총액, Float 등) |
| `calculate_watchlist_score()` | 일봉 기반 Watchlist 점수 (예: Accumulation Score) |
| `calculate_trigger_score()` | 실시간 Trigger 점수 (예: Ignition Score) |
| `get_anti_trap_filter()` | Anti-Trap 필터 조건 반환 |

## Trading Layer

| Method | Description |
|--------|-------------|
| `initialize()` | 전략 초기화 |
| `on_tick()` | 실시간 틱 처리 → Signal |
| `on_bar()` | 분봉/일봉 처리 → Signal |
| `on_order_filled()` | 주문 체결 콜백 |

## Configuration Layer

| Method | Description |
|--------|-------------|
| `get_config()` | 전략 설정값 반환 |
| `set_config()` | 전략 설정값 변경 (런타임) |

---

## 관련 파일

- `backend/core/strategy_base.py` - 추상 베이스 클래스
- `backend/strategies/_template.py` - 신규 전략 템플릿
- `backend/strategies/seismograph/strategy.py` - 메인 전략 구현
