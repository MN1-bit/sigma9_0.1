# tests/__init__.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `tests/__init__.py` |
| **역할** | Sigma9 테스트 패키지 초기화 |
| **라인 수** | 26 |
| **바이트** | 1,037 |

## 설명

> 단위 테스트 및 통합 테스트를 포함하는 패키지 (pytest 프레임워크)

## 테스트 원칙

1. 모든 전략은 `StrategyBase` 인터페이스 준수 테스트 필요
2. API 엔드포인트는 성공/실패 케이스 모두 테스트
3. 브로커 연동은 Mock 객체 사용 (실제 거래 방지)

## 포함 모듈

| 모듈 | 설명 |
|------|------|
| `test_strategies.py` | 전략 테스트 |
| `test_backtest.py` | 백테스트 엔진 테스트 |
| `test_database.py` | MarketDB 테스트 |
| `test_data_integrity.py` | 데이터 정합성 테스트 |
| ... | 총 15개 테스트 모듈 |

## 실행 방법

```bash
pytest tests/                     # 전체 테스트
pytest tests/test_strategies.py   # 특정 모듈만
pytest tests/ -v                  # Verbose
```

## 외부 의존성
- `pytest`
