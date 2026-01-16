# Step 4.A.0.c: 실시간 데이터 파이프라인 수정 계획

> **버전**: 1.0  
> **작성일**: 2026-01-02  
> **선행 조건**: Step 4.A.0.b 완료  
> **참조**: `docs/references/research/phase_4.a.0_review.md`

---

## 📋 개요

Phase 4.A.0/4.A.0.b 구현 검토 결과 발견된 결함 수정

---

## 🔴 P0: listen() 루프 추가

**현재 문제:**
```python
# server.py - connect만 하고 listen() 없음
async def start_massive_streaming():
    if await app_state.massive_ws.connect():
        logger.info("✅ Connected")
        # → 여기서 끝남. 메시지 수신 안됨
```

**수정:**
```python
async def start_massive_streaming():
    if await app_state.massive_ws.connect():
        async for _ in app_state.massive_ws.listen():
            pass  # 콜백이 데이터 처리
```

| 파일 | 변경 |
|------|------|
| `backend/server.py` | listen() 루프 추가 |

---

## 🟡 P1: 초기 구독 트리거

**현재 문제:** connect 후 subscribe 호출 없음

**수정:** connect 직후 Watchlist 로드 + sync_watchlist() 호출

| 파일 | 변경 |
|------|------|
| `backend/server.py` | 초기 구독 로직 추가 |

---

## 🟡 P2: backend_client.py 문자열 수정

**현재 문제:** Line 104-105 문자열 깨짐
```python
bar_received = pyqtSignal(dict)  # Phase 4.A.0: {"
": str, ...
```

**수정:** 한 줄로 정리

| 파일 | 변경 |
|------|------|
| `frontend/services/backend_client.py` | Line 104-105 수정 |

---

## 🟡 P2: AppState 필드 추가

**현재 문제:** `trailing_stop` 필드 미선언

**수정:** AppState 클래스에 필드 추가

| 파일 | 변경 |
|------|------|
| `backend/server.py` (AppState) | `self.trailing_stop = None` 추가 |

---

## 🟢 P3: TYPE_CHECKING 정리

**현재 문제:** tick_broadcaster.py에 TickDispatcher import 누락

| 파일 | 변경 |
|------|------|
| `backend/core/tick_broadcaster.py` | TYPE_CHECKING import 추가 |

---

## 📝 구현 순서

| # | 우선순위 | 작업 | 예상 시간 |
|---|----------|------|----------|
| 1 | P0 | listen() 루프 추가 | 10분 |
| 2 | P1 | 초기 구독 트리거 | 15분 |
| 3 | P2 | backend_client.py 수정 | 5분 |
| 4 | P2 | AppState 필드 추가 | 5분 |
| 5 | P3 | TYPE_CHECKING 정리 | 5분 |

**총 예상 시간**: 40분

---

## ✅ 완료 조건

1. [ ] Massive WebSocket 연결 후 메시지 수신 확인
2. [ ] 초기 구독 자동 실행
3. [ ] 코드 문법 오류 없음
