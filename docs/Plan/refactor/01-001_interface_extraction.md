# 01-001: 인터페이스 추출 (순환 해소)

> **작성일**: 2026-01-08 00:38
> **우선순위**: 1 | **예상 소요**: 2-3h | **위험도**: 낮음

## 1. 목표
`realtime_scanner.py` ↔ `seismograph.py` 순환 의존성을 **인터페이스 추출 (DIP)** 로 해소

## 2. 현재 상황

### 순환 구조
```
realtime_scanner.py (Line 94)
    → from backend.strategies.seismograph import SeismographStrategy  (런타임 import)
```

### 문제점
- 런타임 import로 회피 중 → 코드 가독성 저하, 정적 분석 불가
- `lint-imports` 위반 가능성

## 3. 실행 계획

### Step 1: ScoringStrategy 인터페이스 생성
- 경로: `backend/core/interfaces/scoring.py`
- ABC 클래스로 `calculate_watchlist_score_detailed()` 시그니처 정의

### Step 2: SeismographStrategy가 인터페이스 구현
- `seismograph.py`에서 `ScoringStrategy` 상속 추가

### Step 3: RealtimeScanner가 인터페이스만 의존
- 생성자에서 `scoring_strategy: ScoringStrategy` 주입받도록 수정
- 런타임 import 제거

### Step 4: server.py에서 주입
- `SeismographStrategy` 인스턴스를 생성하여 RealtimeScanner에 전달

## 4. 검증 계획
- [ ] `lint-imports` 통과
- [ ] `pydeps backend --show-cycles` 순환 없음
- [ ] 백엔드 정상 시작 (`python -m backend`)
- [ ] GUI 연결 정상

## 5. 롤백 계획
- 기존 런타임 import 코드 복원
