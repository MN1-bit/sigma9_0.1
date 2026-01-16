# check_tickers.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/scripts/check_tickers.py` |
| **역할** | 디버깅 스크립트 - 50.0점 종목 원인 분석 |
| **라인 수** | 55 |
| **바이트** | 1,972 |

## 설명

> 정확히 50.0점으로 표시되는 종목들의 스코어링 상세 분석

## 함수

### `analyze()` (async)
> 특정 티커들의 상세 점수 분석 후 파일 저장

#### 분석 대상
```python
tickers = ["MOBX", "ACFN", "MRNOW", "BFRGW", "CUBWW", "MRTNO", "KITTW"]
```

#### 출력 내용
- Score V1, V2
- Stage
- Signals (Boolean)
- Intensities (0.0~1.0)

#### 결과 파일
`analysis_result.txt`

## 실행 방법

```bash
python backend/scripts/check_tickers.py
```

## 🔗 외부 연결

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/data/database.py` | `MarketDB` |
| `backend/strategies/seismograph` | `SeismographStrategy` |

## 외부 의존성
- `asyncio`
