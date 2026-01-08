# 05-001: dashboard.py 분리

> **작성일**: 2026-01-08 01:07
> **우선순위**: 5 | **예상 소요**: 6-8h | **위험도**: 중간

## 1. 목표

`dashboard.py` (2,616줄) God Class 해소
→ 패널별 위젯 분리, 중앙 상태 관리 도입

## 2. 현재 문제점

| 책임 | 메서드 수 (추정) | 라인 수 (추정) |
|------|----------------|---------------|
| 초기화/레이아웃 | ~10 | ~300 |
| Watchlist 패널 | ~15 | ~500 |
| Tier2 Hot Zone | ~10 | ~300 |
| Chart 패널 | ~8 | ~400 |
| Log 패널 | ~5 | ~150 |
| Control 패널 | ~10 | ~300 |
| Backend 통신 | ~15 | ~400 |
| 이벤트 핸들러 | ~20 | ~300 |

## 3. 목표 구조 (REFACTORING.md 2.2)

```
frontend/gui/
├── dashboard.py              # 메인 윈도우 (조합자, ~300줄)
├── panels/
│   ├── __init__.py
│   ├── watchlist_panel.py    # 워치리스트 테이블
│   ├── tier2_panel.py        # Hot Zone
│   ├── chart_panel.py        # 차트 컨테이너
│   └── log_panel.py          # 로그 패널
└── state/
    └── dashboard_state.py    # 중앙 상태 관리
```

## 4. 실행 계획

### Step 1: panels/ 디렉터리 생성
### Step 2: WatchlistPanel 분리
- `_create_watchlist_panel()` + 관련 메서드 추출
- QTableWidget → QWidget 서브클래스
### Step 3: Tier2Panel 분리
### Step 4: LogPanel 분리
### Step 5: dashboard_state.py 생성
- 중앙 상태 저장소 (싱글톤 대신 DI)
### Step 6: dashboard.py 정리
- 패널 조합 + 이벤트 라우팅만 담당

## 5. 검증 계획
- [ ] GUI 정상 실행
- [ ] Watchlist 표시/정렬 동작
- [ ] Tier2 Hot Zone 업데이트
- [ ] 차트 표시 정상
- [ ] 로그 패널 동작
- [ ] 모든 파일 ≤500줄

## 6. 롤백 계획
- `git checkout HEAD -- frontend/gui/dashboard.py`
- `rm -rf frontend/gui/panels/ frontend/gui/state/`
