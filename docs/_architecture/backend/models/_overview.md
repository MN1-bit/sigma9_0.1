# Backend Models Module

> 📍 **Location**: `backend/models/`  
> **Role**: 중앙 데이터 모델 저장소 - 모든 공용 데이터 구조체

---

## 파일 목록 (8 files)

| 파일 | 모델 | 설명 |
|------|------|------|
| `__init__.py` | - | 패키지 진입점, 모든 모델 re-export |
| `backtest.py` | `BacktestConfig`, `Trade`, `BacktestReport` | 백테스트 관련 |
| `order.py` | `OrderStatus`, `OrderType`, `OrderRecord`, `Position` | 주문/포지션 |
| `risk.py` | `RiskConfig` | 리스크 관리 설정 |
| `technical.py` | `IndicatorResult`, `StopLossLevels`, `ZScoreResult`, `DailyStats` | 기술적 분석 |
| `tick.py` | `TickData` | 실시간 틱 데이터 |
| `ticker_info.py` | `TickerInfo`, `SEC_FILING_TYPES` | 티커 종합 정보 |
| `watchlist.py` | `WatchlistItem` | Watchlist 항목 |

---

## 모델 상세

### `BacktestConfig`
> 백테스트 설정

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `initial_capital` | float | 100,000 | 초기 자본금 |
| `position_size_pct` | float | 10.0 | 포지션 크기 % |
| `max_positions` | int | 5 | 최대 동시 포지션 |
| `stop_loss_pct` | float | -5.0 | 스탑로스 % |
| `profit_target_pct` | float | 8.0 | 익절 % |
| `time_stop_days` | int | 3 | 시간 기반 청산 |
| `entry_stage` | int | 4 | 진입 Stage |
| `min_score` | float | 80.0 | 최소 진입 스코어 |

### `Trade`
> 개별 거래 기록

| 필드 | 타입 | 설명 |
|------|------|------|
| `ticker` | str | 종목 심볼 |
| `entry_date` | str | 진입 날짜 |
| `entry_price` | float | 진입 가격 |
| `exit_date` | str? | 청산 날짜 |
| `exit_price` | float? | 청산 가격 |
| `exit_reason` | str? | 청산 이유 |
| `pnl_pct` | float? | 손익률 % |

### `OrderRecord`
> 주문 기록

| 필드 | 타입 | 설명 |
|------|------|------|
| `order_id` | int | 주문 ID |
| `symbol` | str | 종목 심볼 |
| `action` | str | BUY/SELL |
| `qty` | int | 수량 |
| `order_type` | OrderType | 주문 유형 |
| `status` | OrderStatus | 주문 상태 |

### `Position`
> 포지션 정보

| 필드 | 타입 | 설명 |
|------|------|------|
| `symbol` | str | 종목 심볼 |
| `qty` | int | 보유 수량 |
| `avg_price` | float | 평균 매입가 |
| `current_price` | float | 현재가 |

### `RiskConfig`
> 리스크 관리 설정

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `max_position_pct` | 10.0 | 포지션당 최대 % |
| `max_positions` | 3 | 최대 동시 포지션 |
| `daily_loss_limit_pct` | -3.0 | 일일 손실 한도 |
| `per_trade_stop_pct` | -5.0 | 거래당 스탑 |

### `TickData`
> 실시간 틱 데이터

| 필드 | 타입 | 설명 |
|------|------|------|
| `price` | float | 체결 가격 |
| `volume` | int | 체결 수량 |
| `event_time` | datetime | 거래소 체결 시간 |
| `receive_time` | datetime | 서버 수신 시간 |
| `side` | str | B (매수) / S (매도) |

### `ZScoreResult`
> Z-Score 계산 결과

| 필드 | 타입 | 설명 |
|------|------|------|
| `zenV` | float | 거래량 Z-Score |
| `zenP` | float | 가격변동 Z-Score |

### `WatchlistItem`
> Watchlist 항목

| 필드 | 타입 | 설명 |
|------|------|------|
| `ticker` | str | 종목 코드 |
| `score` | float | Accumulation Score |
| `stage` | str | Stage 문자열 |
| `stage_number` | int | Stage 번호 (1-4) |
| `can_trade` | bool | 트레이딩 허용 여부 |

### `TickerInfo`
> 티커 종합 정보 (13개 카테고리)

| 필드 | 설명 |
|------|------|
| `profile` | 기본 정보 |
| `float_data` | 유동성 데이터 |
| `financials` | 재무제표 |
| `dividends` | 배당 이력 |
| `splits` | 주식 분할 이력 |
| `filings` | SEC 공시 |
| `news` | 뉴스 |
| `snapshot` | 현재가 스냅샷 |

---

## 🔗 외부 연결

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `dataclasses` | `dataclass`, `field` |
| `enum` | `Enum`, `auto` |
| `datetime` | `datetime` |
| `typing` | `Optional`, `Dict`, `List`, `Any` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `backend/core/*` | 데이터 모델 사용 |
| `backend/api/routes/*` | 요청/응답 모델 |
| `backend/strategies/*` | 전략 데이터 |

---

## 사용 예시
```python
from backend.models import (
    TickData, WatchlistItem, RiskConfig,
    BacktestConfig, Trade, OrderRecord
)
```
