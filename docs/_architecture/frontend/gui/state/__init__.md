# state/__init__.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `frontend/gui/state/__init__.py` |
| **역할** | State 관리 패키지 초기화 및 공개 인터페이스 |
| **라인 수** | 19 |

## 패키지 개요

Sigma9 Dashboard의 상태 관리를 중앙화합니다.
싱글톤 패턴 대신 **의존성 주입(DI)**을 통해 상태를 공유합니다.

## 공개 인터페이스 (Exports)

| 클래스 | 소스 파일 | 설명 |
|--------|----------|------|
| `DashboardState` | `dashboard_state.py` | 중앙 상태 저장소 (Event Bus) |
| `Tier2Item` | `dashboard_state.py` | Tier 2 데이터 아이템 (re-export) |

## 🔗 외부 연결 (Connections)

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `frontend/gui/state/dashboard_state.py` | `DashboardState`, `Tier2Item` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `frontend/gui/panels/*.py` | DI로 state 주입 |
| `frontend/gui/dashboard.py` | 중앙 state 생성 및 주입 |

## 구조
```
state/
├── __init__.py           # 이 파일 - 상태 관리자 내보내기
└── dashboard_state.py    # 중앙 상태 저장소
```
