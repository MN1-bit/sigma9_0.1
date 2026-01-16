# 02-007: Frontend 싱글톤 패턴 검토 계획서

> **작성일**: 2026-01-10 05:29  
> **우선순위**: 2 (DI Container 후속) | **예상 소요**: TBD | **위험도**: 중간

---

## 1. 목표

Frontend 모듈의 싱글톤 패턴 현황 파악 및 향후 개선 방향 검토.

> [!IMPORTANT]
> 현재 Frontend DI Container가 없으므로 **즉시 실행 대상 아님**.  
> 향후 Frontend 아키텍처 리팩터링 시 참조용 문서.

---

## 2. 왜 Frontend DI Container가 없는가?

### 2.1 아키텍처 분리 원칙

```
Backend (AWS 배포) ←── REST/WebSocket ──→ Frontend (Windows 로컬)
```

- **Backend**: 모든 비즈니스 로직, 데이터 처리, 전략 실행
- **Frontend**: 단순 GUI 표시 + Backend 호출 (Thin Client)

### 2.2 Backend vs Frontend 복잡도 비교

| 항목 | Backend | Frontend |
|------|---------|----------|
| 서비스 수 | 10+ (Scanner, Monitor, Repository 등) | 2~3개 (BackendClient, Theme) |
| 의존성 그래프 | 복잡 (순환 위험) | 단순 (선형) |
| Mock 주입 필요성 | 높음 (단위 테스트) | 낮음 (GUI 테스트는 별도 방법론) |
| DI 도입 효과 | 높음 | 낮음 |

### 2.3 결론

Frontend DI Container가 없는 것은 **"누락"이 아니라 의도적 설계**.

- Frontend는 Thin Client로서 복잡한 DI가 **불필요**
- `BackendClient.instance()` 패턴은 테스트 용이성 측면에서 개선 여지 있음
- REFACTORING.md에서 "📋 대기" 상태: 우선순위 낮음

---

## 3. 현황 분석

### 3.1 발견된 싱글톤 패턴

| 파일 | 패턴 | 용도 | 현재 상태 |
|------|------|------|----------|
| [backend_client.py](file:///d:/Codes/Sigma9-0.1/frontend/services/backend_client.py#L113-140) | `_instance` + `instance()` | Backend 통신 클라이언트 | 📋 검토 필요 |
| [theme.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/theme.py#L115-122) | `_instance` + `__new__()` | 전역 테마 관리 | ✅ 현행 유지 |

### 3.2 상세 분석

#### `BackendClient` (backend_client.py)

```python
# L113-140
class BackendClient(QObject):
    _instance = None

    @classmethod
    def instance(cls):
        """싱글톤 인스턴스 반환"""
        if not cls._instance:
            cls._instance = BackendClient()
        return cls._instance
```

**특징**:
- PyQt `QObject` 상속
- Qt Signal 사용 (`connected`, `watchlist_updated` 등)
- REST/WebSocket 어댑터 관리

**개선 검토 사항**:
- Frontend DI Container 도입 시 마이그레이션 가능
- 현재는 GUI 전체에서 단일 인스턴스 필요

#### `ThemeManager` (theme.py)

```python
# L115-122
class ThemeManager(QObject):
    _instance: Optional["ThemeManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
```

**특징**:
- 앱 전체 테마/색상 관리
- Hot Reload Signal 지원 (`theme_changed`)
- 전역 인스턴스 `theme = ThemeManager()` 제공

**권장 사항**:
- ✅ **현행 유지**: 테마 관리자는 전역 단일 인스턴스가 적합
- 앱 전체에서 일관된 스타일 적용 필요

---

## 4. 개선 방향 (향후)

### 4.1 Frontend DI Container 도입 시

```python
# frontend/container.py (예시)
from dependency_injector import containers, providers

class FrontendContainer(containers.DeclarativeContainer):
    backend_client = providers.Singleton(BackendClient)
    # ThemeManager는 전역 유지
```

### 4.2 점진적 마이그레이션

1. `FrontendContainer` 생성
2. `BackendClient` 등록
3. GUI 모듈에서 `container.backend_client()` 사용
4. 레거시 `instance()` 메서드에 DeprecationWarning 추가

---

## 5. 현재 조치

| 항목 | 조치 | 이유 |
|------|------|------|
| `BackendClient._instance` | 📋 대기 | Frontend DI Container 부재 |
| `ThemeManager._instance` | ✅ 유지 | 전역 테마 관리 목적 적합 |

---

## 6. 선행 작업

- [ ] Frontend DI Container 아키텍처 설계
- [ ] PyQt + dependency-injector 통합 방안 검토
- [ ] 테스트 용이성 vs 복잡도 트레이드오프 분석

---

## 7. 참고

- [02-006_singleton_cleanup.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/02-006_singleton_cleanup.md) - Backend 싱글톤 정리
- [REFACTORING.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/REFACTORING.md) - DI 패턴 가이드
