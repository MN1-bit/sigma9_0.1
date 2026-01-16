# [DOC-001] 통합 아키텍처 분석 문서 생성 계획서

> **작성일**: 2026-01-17 04:31 | **예상**: 4h (7단계 chunk)
> 
> **실행 워크플로우**: `/IMP-execution`

---

## 1. 목표 (PRD 구조)

### 1.1 배경 (Problem)
- `docs/_architecture/` 내 **~156개 개별 문서** 존재
- 기존 `Full_DataFlow.md` (84개 dataflow), `Full_DataFlow_Diagram.md` (8개 다이어그램)는 **Data Flow만** 다룸
- **클래스 구조, 멤버, 연결 관계** 통합 시각화 부재

### 1.2 목표 (Goal)
1. **모든 Data Flow** 시각화 (기존 84개 + 누락분)
2. **모든 클래스 및 연결 방식** 도표화
3. **통합/단순화 가능한 dataflow** 식별

### 1.3 User Stories
- As a **개발자**, I want **전체 아키텍처를 한 문서**에서 파악 so that **영향 범위 빠르게 파악**
- As a **AI 에이전트**, I want **클래스 연결 관계 명세** so that **의존성 체크 자동화**

### 1.4 Functional Requirements
1. 모든 **Data Flow 섹션** 통합
2. 모든 **클래스의 public 멤버** 도표화
3. **클래스 간 연결 관계** 매트릭스 표현
4. **중복/유사 dataflow** 식별 및 통합 제안

### 1.5 Non-Goals

#### 🚫 Out of Scope
- ❌ Rheograph 전략 내부 사양 — 별도 프로젝트
- ❌ 코드 구현 상세 (함수 내부 로직)

#### ⏳ Deferred
- ⏳ 인터랙티브 HTML 다이어그램 → **별도 작업**
- ⏳ 자동 문서 동기화 스크립트 → **[DOC-002]**

---

## 2. 레이어 체크
- [x] 레이어 규칙 위반 없음 (문서 작업)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: 아니오

---

## 3. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `docs/_architecture/Full_Architecture.md` | 신규 | ~3000줄 |
| `docs/_architecture/Full_DataFlow_Diagram.md` | 수정 | +500줄 |

---

## 4. Tasks (7단계 분해)

> **규칙**: 완료 시 `- [ ]` → `- [x]`로 마킹
> 
> **워크플로우**: `/IMP-execution` 따라 각 Chunk 완료 후 Devlog 작성

### Chunk 1: Data Flow 확장 (~45분)
- [ ] 1.0 기존 Data Flow 현황 분석
  - [ ] 1.1 `Full_DataFlow.md` 84개 항목 목록화
  - [ ] 1.2 개별 문서에서 누락된 Data Flow 식별
  - [ ] 1.3 누락분 추가 (예상: 10-20개)

### Chunk 2A: Backend 클래스 도표화 (~35분)
- [ ] 2A.0 Backend 클래스 인벤토리
  - [ ] 2A.1 `container.py` 기준 서비스 목록 추출
  - [ ] 2A.2 `backend/core/` 클래스 public 멤버 추출
  - [ ] 2A.3 `backend/data/`, `backend/broker/` 클래스 분석
  - [ ] 2A.4 Backend 클래스 도표 생성

### Chunk 2B: Frontend 클래스 도표화 (~25분)
- [ ] 2B.0 Frontend 클래스 인벤토리
  - [ ] 2B.1 `Dashboard`, `Panels` 클래스 분석
  - [ ] 2B.2 `Services`, `State` 클래스 분석
  - [ ] 2B.3 Frontend 클래스 도표 생성

### Chunk 3: 클래스 연결 관계 매트릭스 (~45분)
- [ ] 3.0 의존성 분석
  - [ ] 3.1 import 분석으로 의존성 그래프 생성
  - [ ] 3.2 상속 관계 도표화 (ABC → 구현체)
  - [ ] 3.3 컴포지션 관계 식별 (has-a)
  - [ ] 3.4 연결 관계 매트릭스 생성

### Chunk 4: 통합/단순화 기회 식별 (~30분)
- [ ] 4.0 중복 분석
  - [ ] 4.1 유사 dataflow 패턴 식별
  - [ ] 4.2 통합 가능한 서비스 후보 목록
  - [ ] 4.3 단순화 제안 섹션 작성

### Chunk 5A: 통합 문서 구조 + 콘텐츠 병합 (~30분)
- [ ] 5A.0 Full_Architecture.md 기본 구조
  - [ ] 5A.1 목차 구조 설계
  - [ ] 5A.2 Chunk 1-4 결과 통합
  - [ ] 5A.3 레이아웃 및 네비게이션 정리

### Chunk 5B: Mermaid 다이어그램 통합 (~30분)
- [ ] 5B.0 시각화 통합
  - [ ] 5B.1 기존 8개 다이어그램 복사/정리
  - [ ] 5B.2 클래스 다이어그램 추가
  - [ ] 5B.3 `Full_DataFlow_Diagram.md` 확장
  - [ ] 5B.4 렌더링 검증

---

## 5. 검증
- [ ] 마크다운 문법 검증
- [ ] Mermaid 렌더링 확인
- [ ] 개별 문서 대비 누락 없음 확인

---

## 6. Chunk별 산출물

| Chunk | 산출물 | Devlog |
|-------|--------|--------|
| 1 | Data Flow 전체 목록 | `26-01-17/XX-XX_DOC-001_chunk1.md` |
| 2A | Backend 클래스 도표 | `26-01-17/XX-XX_DOC-001_chunk2a.md` |
| 2B | Frontend 클래스 도표 | `26-01-17/XX-XX_DOC-001_chunk2b.md` |
| 3 | 연결 관계 매트릭스 | `26-01-17/XX-XX_DOC-001_chunk3.md` |
| 4 | 통합 제안 목록 | `26-01-17/XX-XX_DOC-001_chunk4.md` |
| 5A | 구조 + 콘텐츠 병합 | `26-01-17/XX-XX_DOC-001_chunk5a.md` |
| 5B | 다이어그램 통합 | `26-01-17/XX-XX_DOC-001_chunk5b.md` |
