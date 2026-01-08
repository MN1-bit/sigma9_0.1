# 04-001: server.py lifespan 분리

> **작성일**: 2026-01-08 01:07
> **우선순위**: 4 | **예상 소요**: 2-3h | **위험도**: 낮음

## 1. 목표

`server.py` (525줄)의 lifespan 함수가 너무 비대함 (280줄+)
→ 초기화 로직을 별도 모듈로 분리하여 가독성 및 테스트 용이성 확보

## 2. 현재 문제점

```
lifespan() 함수 (Line 110-432):
├── Config 로드 (~20줄)
├── DI Container 설정 (~15줄)
├── Database 초기화 (~10줄)
├── Strategy Loader (~10줄)
├── IgnitionMonitor (~15줄)
├── Daily Data Sync (~25줄)
├── IBKR 연결 (~15줄)
├── Scheduler (~15줄)
├── Massive WebSocket (~80줄)
├── IgnitionMonitor 자동시작 (~35줄)
├── RealtimeScanner (~35줄)
└── Shutdown 로직 (~40줄)
```

## 3. 목표 구조

```
backend/
├── server.py              # FastAPI app + 간단한 lifespan (~150줄)
└── startup/
    ├── __init__.py
    ├── config.py          # Config + Logging 초기화
    ├── database.py        # DB 초기화
    ├── realtime.py        # Massive WS, Scanner, IgnitionMonitor
    └── shutdown.py        # 종료 로직
```

## 4. 실행 계획

### Step 1: startup/ 디렉터리 생성
### Step 2: 초기화 함수 추출
각 초기화 블록을 `async def initialize_*()` 함수로 분리
### Step 3: lifespan 리팩터링
분리된 함수들 호출로 단순화
### Step 4: shutdown 로직 분리

## 5. 검증 계획
- [ ] `python -m backend` 정상 시작
- [ ] 모든 컴포넌트 초기화 로그 확인
- [ ] Graceful shutdown 동작 확인
- [ ] `lint-imports` 통과

## 6. 롤백 계획
- `git checkout HEAD -- backend/server.py`
- `rm -rf backend/startup/`
