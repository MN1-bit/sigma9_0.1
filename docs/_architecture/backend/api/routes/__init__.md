# routes/__init__.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/api/routes/__init__.py` |
| **역할** | 모든 도메인별 라우터를 조합하여 단일 APIRouter로 제공 |
| **라인 수** | 115 |

---

## 구조

라우터 조합 순서:
1. Status & Control (기본)
2. Watchlist & Position
3. Strategy
4. Scanner & Gainers
5. Ignition (실시간)
6. Chart
7. LLM / Oracle
8. Tier2 (Hot Zone)
9. Z-Score
10. Data Sync

---

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `fastapi` | `APIRouter` |
| `./models.py` | Pydantic 모델들 (EngineCommand, ControlRequest 등) |
| `./status.py` | `router as status_router` |
| `./control.py` | `router as control_router` |
| `./watchlist.py` | `router as watchlist_router` |
| `./position.py` | `router as position_router` |
| `./strategy.py` | `router as strategy_router` |
| `./scanner.py` | `router as scanner_router` |
| `./ignition.py` | `router as ignition_router` |
| `./chart.py` | `router as chart_router` |
| `./llm.py` | `router as llm_router` |
| `./tier2.py` | `router as tier2_router` |
| `./zscore.py` | `router as zscore_router` |
| `./sync.py` | `router as sync_router` |

### Imported By (이 파일을 가져가는 것)
| 파일 | 사용 목적 |
|------|----------|
| `backend/server.py` | `app.include_router(router, prefix="/api")` |

### Exports
```python
__all__ = [
    "router",
    "EngineCommand", "ControlRequest", "ControlResponse",
    "ServerStatus", "WatchlistItem", "PositionItem",
    "StrategyInfo", "AnalysisRequest", "Tier2PromoteRequest",
]
```

---

## 외부 의존성
- `fastapi`
