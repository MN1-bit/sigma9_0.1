# scoring/__init__.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/seismograph/scoring/__init__.py` |
| **역할** | Scoring 모듈 진입점 - V1/V2/V3 점수 함수 및 가중치 export |
| **라인 수** | 15 |
| **바이트** | 353 |

## Export 목록

```python
__all__ = [
    "calculate_score_v1",
    "calculate_score_v2",
    "calculate_score_v3",
    "SCORE_WEIGHTS",
    "V3_WEIGHTS",
]
```

| Export | 소스 | 설명 |
|--------|------|------|
| `calculate_score_v1` | `v1.py` | Stage-Based Priority 점수 |
| `calculate_score_v2` | `v2.py` | 가중합 연속 점수 |
| `calculate_score_v3` | `v3.py` | Pinpoint Algorithm |
| `SCORE_WEIGHTS` | `v2.py` | V2 가중치 |
| `V3_WEIGHTS` | `v3.py` | V3 가중치 |

## 🔗 외부 연결

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `seismograph/strategy.py` | 점수 계산 함수 호출 |

## 외부 의존성
- (없음)
