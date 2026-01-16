# Backend API Overview

> 📍 **Location**: `backend/api/`  
> **Role**: REST 및 WebSocket API 엔드포인트 정의

---

## 구조

```
api/
├── __init__.py
├── websocket.py          # WebSocket 핸들러
└── routes/               # REST 라우트
    ├── __init__.py
    ├── chart.py
    ├── common.py
    ├── control.py
    ├── ignition.py
    ├── llm.py
    ├── models.py
    ├── position.py
    ├── scanner.py
    ├── status.py
    ├── strategy.py
    ├── sync.py
    ├── tier2.py
    ├── watchlist.py
    └── zscore.py
```

---

## 파일 목록

### 메인 파일

| 파일 | 역할 |
|------|------|
| [websocket.py](./websocket.md) | WebSocket 핸들러 |

### Routes (15 files)

| 파일 | 역할 |
|------|------|
| [chart.py](./routes/chart.md) | 차트 데이터 API |
| [common.py](./routes/common.md) | 공통 유틸리티 |
| [control.py](./routes/control.md) | 제어 명령 API |
| [ignition.py](./routes/ignition.md) | 점화 스코어 API |
| [llm.py](./routes/llm.md) | LLM API |
| [models.py](./routes/models.md) | 모델 API |
| [position.py](./routes/position.md) | 포지션 API |
| [scanner.py](./routes/scanner.md) | 스캐너 API |
| [status.py](./routes/status.md) | 상태 API |
| [strategy.py](./routes/strategy.md) | 전략 API |
| [sync.py](./routes/sync.md) | 동기화 API |
| [tier2.py](./routes/tier2.md) | Tier2 API |
| [watchlist.py](./routes/watchlist.md) | 워치리스트 API |
| [zscore.py](./routes/zscore.md) | Z-Score API |
