# frameless_dialog_pattern.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/Ref/frameless_dialog_pattern.md` |
| **역할** | Frameless + Acrylic 효과 Dialog 구현 패턴 |
| **라인 수** | 154 |

## 핵심 문제 및 해결

### 문제 1: 마우스 이벤트 통과
- **원인**: `WA_TranslucentBackground` 설정 시 alpha=0 영역 이벤트 통과
- **해결**: 컨테이너에 `rgba(0,0,0,0.01)` 배경 부여

### 문제 2: 자식 위젯 드래그 불가
- **원인**: 자식 위젯이 마우스 이벤트 소비
- **해결**: `installEventFilter` 재귀 설치

### 문제 3: 인터랙티브 위젯 드래그 방지
- **해결**: `_is_interactive_widget()` 체크 (QPushButton, QComboBox 등 제외)

## 구현 체크리스트
| # | 항목 |
|---|------|
| 1 | Frameless 설정 |
| 2 | WA_TranslucentBackground |
| 3 | rgba 배경 컨테이너 |
| 4 | Acrylic 효과 |
| 5 | 드래그 필터 설치 |
| 6 | 인터랙티브 위젯 제외 |
| 7 | `theme.apply_to_widget()` |
