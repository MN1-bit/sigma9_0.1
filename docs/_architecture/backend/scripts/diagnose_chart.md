# diagnose_chart.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/scripts/diagnose_chart.py` |
| **역할** | 차트 데이터 진단 스크립트 - High-Low 범위 분석 |
| **라인 수** | 82 |
| **바이트** | 2,578 |

## 함수

### `detailed_diagnose(ticker="SGBX")` (async)
> 특정 티커의 분봉 데이터 상세 분석

#### 분석 항목
- Doji 캔들 (H=L) vs Non-Doji 캔들 개수
- Non-Doji H-L 범위 통계 (Min/Max/Avg)
- 범위가 큰 상위 5개 캔들 출력
- 전체 가격 범위 (Global High/Low)

## 실행 방법

```bash
python backend/scripts/diagnose_chart.py
```

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/data/massive_client.py` | `MassiveClient` |

## 외부 의존성
- `dotenv`
- `asyncio`
