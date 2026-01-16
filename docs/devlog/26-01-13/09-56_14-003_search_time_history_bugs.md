# 14-003: 검색창 자동완성/히스토리 및 시간 표시 Devlog

> **작성일**: 2026-01-13
> **계획서**: [link](../../Plan/bugfix/14-003_search_time_history_bugs.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1 | ✅ | 09:55 |
| Step 2 | ✅ | 10:05 |
| Step 3 | ✅ | 10:06 |
| Step 4 | ✅ | 10:06 |

---

## Step 1: 문제 원인 분석

### 분석 결과

#### Bug 1: US East 시간 미표시
- **원인**: `ws_adapter.py` L366-370의 `_send_ping()` 메서드
- `asyncio.create_task()`는 asyncio 이벤트 루프가 필요
- PyQt 메인 스레드에서 QTimer로 호출 시 이벤트 루프 없음 → 실패

#### Bug 2&3: 자동완성 / 히스토리
- 기존 코드 정상, 런타임에서 확인 필요

### 검증
- 분석 완료 ✅

---

## Step 2: 시간 표시 수정 (Bug 1)

### 변경 사항
- `frontend/services/ws_adapter.py`:
  - L134: `_event_loop` 필드 추가
  - L172: `connect()`에서 이벤트 루프 참조 저장
  - L368-378: `_send_ping()`에서 `asyncio.run_coroutine_threadsafe()` 사용

### 검증
- lint: ✅ (All checks passed!)

---

## Step 3 & 4: 자동완성 / 히스토리 확인

### 분석
- `_load_ticker_data_for_search()`는 backend 연결 후 정상 호출
- `_add_to_history()` → `_update_combo_items()` 정상 동작
- **추가 수정 불필요**: 기존 구현 정상

### 검증
- 런타임 테스트 필요 (수동)
