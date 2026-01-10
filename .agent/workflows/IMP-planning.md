---
description: 새 기능 구현 계획서 작성 (구현 시작 전 필수)
---

# IMP-planning

> **원칙**: 리팩터링 없는 코드. REFACTORING.md 규칙 100% 준수.

## 1. 필수 컨텍스트

// turbo
```
docs/Plan/refactor/REFACTORING.md  ← 핵심 (§3-§6 필수)
.agent\Ref\archt.md   ← 모듈 배치 참조
.agent\Ref\MPlan.md   ← 마일스톤 참조
```

---

## 2. 레이어 의존성 (REFACTORING.md §3.3)

```
[상위] ← [하위] 방향만 허용

backend.api
    ↓
backend.core
    ↓
backend.strategies
    ↓
backend.data
    ↓
backend.broker
```

| 위반 시 | 결과 |
|--------|------|
| 역방향 import | `lint-imports` 실패 → 머지 불가 |
| 순환 import | `pydeps --show-cycles` 검출 → 수정 필수 |

### 금지된 import 패턴
```python
# ❌ backend.data가 strategies import
from backend.strategies import ...

# ❌ backend.strategies가 api import
from backend.api import ...

# ❌ backend ↔ frontend 상호 import
from frontend import ...  # in backend
from backend import ...   # in frontend
```

---

## 3. DI 패턴 (REFACTORING.md §5-§6)

### 금지 패턴
```python
# ❌ 전역 싱글톤
_instance = None
def get_scanner_instance(): ...
```

### 필수 패턴
```python
# ✅ Container 등록
# backend/container.py
scanner = providers.Singleton(RealtimeScanner, db=db_client)

# ✅ 주입받아 사용
def __init__(self, scanner: RealtimeScanner): ...
```

### 순환 의존성 해소
```python
# ✅ 인터페이스 추출 (DIP)
# backend/core/interfaces/xxx.py
class ScoringStrategy(ABC):
    @abstractmethod
    def calculate_score(self, ...): ...
```

---

## 4. 크기 제한 (REFACTORING.md §8)

| 대상 | 제한 | 위반 시 |
|------|------|--------|
| 파일 | ≤ **1000줄** | 분할 필수 |
| 클래스 | ≤ **30 메서드** | 분할 필수 |
| 클래스 | ≤ **400줄** | 분할 필수 |

---

## 5. 바퀴 재발명 금지 (No Reinventing the Wheel)

> **원칙**: 직접 구현 전 **반드시** 기존 솔루션 검색. 더 빠른 길이 있으면 그 길로.

### 필수 검색 항목
| 검색 대상 | 검색처 | 예시 |
|-----------|--------|------|
| 알고리즘/로직 | PyPI, npm, GitHub | `finplot`, `pandas-ta` |
| UI 컴포넌트 | Qt 위젯, 오픈소스 | `QDarkStyleSheet` |
| 인프라/패턴 | 공식 문서, Stack Overflow | `ib_insync` 네이티브 기능 |

### 검색 프로세스
```
1. 구현하려는 기능을 키워드로 분해
2. PyPI / GitHub / Stack Overflow 검색 (최소 3곳)
3. 검색 결과 → 계획서에 기록:
   - 발견한 라이브러리/솔루션 목록
   - 채택/미채택 사유
   - 없으면 "검색 완료, 적합한 솔루션 없음" 명시
```

### 계획서 템플릿 추가 항목
```markdown
## X. 기존 솔루션 검색 결과
| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| (예시) finplot | PyPI | ✅ 채택 | PyQtGraph보다 금융차트 특화 |
| (예시) mplfinance | PyPI | ❌ 미채택 | Qt 임베딩 복잡 |
```

> ⚠️ **검색 없이 직접 구현 시작 = 계획서 반려**

---

## 6. 사전 체크리스트

계획서 작성 전 **반드시** 확인:

- [ ] 레이어 규칙 위반 없는가? (§2)
- [ ] 신규 서비스 → Container 등록 계획 있는가?
- [ ] 순환 의존성 위험 → 인터페이스 추출 계획 있는가?
- [ ] 기존 1000줄+ 파일 수정 → 분할 선행 필요?

---

## 6. 계획서 템플릿

경로: `docs/Plan/impl/{기능명}_plan.md`

```markdown
# [기능명] 구현 계획서

> **작성일**: YYYY-MM-DD | **예상**: Xh

## 1. 목표
-

## 2. 레이어 체크
- [ ] 레이어 규칙 위반 없음
- [ ] 순환 의존성 없음
- [ ] DI Container 등록 필요: 예/아니오

## 3. 변경 파일
| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
|      |     |          |

## 4. 실행 단계
### Step 1:
### Step 2:

## 5. 검증
- [ ] lint-imports
- [ ] pydeps --show-cycles
```

## 7. 승인

**반드시** 사용자 승인 후 코드 작성.

---

**다음**: `/IMP-execution`