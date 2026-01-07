# 문서 통합 계획 (Documentation Consolidation Plan)

> **작성일**: 2026-01-07  
> **목표**: 29개 정책 문서 → 5개 + 전략별 개별 문서로 통합

---

## 1. 현황

### 1.1 현재 문서 분포 (29개)

| 위치 | 문서 수 | 내용 |
|------|---------|------|
| 루트 | 2 | @PROJECT_DNA.md, CLAUDE.md |
| docs/Plan/ | 2 | masterplan.md, development_steps.md |
| docs/architecture/ | 2 | data_flow.md, data_flow_mermaid.md |
| docs/refactor/ | 2 | automation_standards.md, codebase_analysis.md |
| docs/strategy/ | 21 | Seismograph, Score V2/V3, MEP 3.1/3.2 등 |

### 1.2 문제점

- 정책 문서 산재 → AI/개발자가 어디 참조해야 할지 불명확
- 중복 내용 다수 (Score V2/V3 여러 버전)
- 진입점 혼란 (@PROJECT_DNA vs CLAUDE.md vs masterplan)

---

## 2. 목표 구조

```
Sigma9-0.1/
│
├── @PROJECT_DNA.md                    # 🔴 진입점 (규칙, 컨벤션, 워크플로우)
│
├── .agent/
│   └── workflows/                     # 워크플로우 정의
│       ├── build.md
│       ├── test.md
│       └── deploy.md
│
└── docs/
    └── context/                       # 🔵 핵심 정책 문서
        ├── ARCHITECTURE.md            # 시스템 설계
        ├── REFACTORING.md             # 리팩터링 정책
        │
        └── strategy/                  # 🟢 전략별 개별 문서
            ├── seismograph.md         # Seismograph 전략 (Score V3 포함)
            ├── mep.md                 # MEP 3.2 프로토콜
            └── ignition.md            # Ignition Score
```

---

## 3. 통합 매핑

### 3.1 @PROJECT_DNA.md (진입점)

**흡수 대상:**
- `CLAUDE.md` → 전체 흡수
- `.agent/workflows/` 참조 추가

**최종 섹션 구성:**
1. 프로젝트 정체성 (기존)
2. 아키텍처 개요 (기존)
3. 개발 프로세스 (기존)
4. 코딩 컨벤션 (기존)
5. AI 에이전트 가이드 (CLAUDE.md에서 흡수)
6. 명령어 & 워크플로우 (신규)

---

### 3.2 docs/context/ARCHITECTURE.md

**흡수 대상:**
| 원본 | 흡수 내용 |
|------|-----------|
| `docs/Plan/masterplan.md` | Section 6 (Architecture), Section 7 (GUI) |
| `docs/Plan/steps/development_steps.md` | 전체 |
| `docs/architecture/data_flow.md` | 전체 |
| `docs/architecture/data_flow_mermaid.md` | 다이어그램만 |

**최종 섹션 구성:**
1. 시스템 아키텍처 (Backend/Frontend 분리)
2. 데이터 파이프라인 (Mermaid 다이어그램)
3. 모듈 구조 (core, strategies, data, api, gui)
4. 개발 로드맵 (Step 단계)

---

### 3.3 docs/context/strategy/ (전략별 개별 문서)

#### 3.3.1 seismograph.md

**흡수 대상:**
| 원본 | 흡수 내용 |
|------|-----------|
| `docs/Plan/masterplan.md` | Section 3 (Phase 1: Accumulation Detection) |
| `docs/strategy/seismograph_strategy_guide.md` | 전체 |
| `docs/strategy/Score_v3_complete_guide.md` | 전체 (최신) |
| `docs/strategy/score_v2_formula.md` | V3 비교용 참조만 |
| `docs/strategy/accumulation_bar_v3_argument.md` | 핵심만 |
| `docs/strategy/signal_modifier_design.md` | 전체 |

**최종 섹션 구성:**
1. Seismograph 전략 개요 (철학, 3-Phase)
2. Phase 1: Accumulation Detection (4단계)
3. Score V3 알고리즘 (공식 + 파라미터)
4. Signal Modifier 설계
5. 리스크 관리

---

#### 3.3.2 mep.md

**흡수 대상:**
| 원본 | 흡수 내용 |
|------|-----------|
| `docs/strategy/MEP3.2.md` | 전체 (최신) |
| `docs/strategy/MEP3.1/*.md` (7개) | 핵심만 축약 |
| `docs/strategy/microstructure_execution_protocol.md` | 전체 |

**최종 섹션 구성:**
1. MEP 개요 (목적, 버전 히스토리)
2. 스캔 단계 (Scan)
3. 매크로 권한 (Macro Permission)
4. 진입/청산 규칙 (Entry/Exit)
5. 포지션 관리 (In-Position)
6. 세션 프로토콜

---

#### 3.3.3 ignition.md

**흡수 대상:**
| 원본 | 흡수 내용 |
|------|-----------|
| `docs/Plan/masterplan.md` | Section 4 (Phase 2: Ignition Trigger) |
| `docs/strategy/ignition_score_formula.md` | 전체 |

**최종 섹션 구성:**
1. Ignition Score 개요
2. 4대 구성요소 (Tick Velocity, Volume Burst, Price Break, Buy Pressure)
3. Anti-Trap Filter
4. 실시간 계산 로직

---

**폐기 대상 (중복/구버전):**
| 폐기 문서 | 사유 |
|-----------|------|
| `Score_v2.1.md` | V3로 대체 |
| `Score_v3.md` | complete_guide로 대체 |
| `Score_v3_Critics.md` | seismograph.md에 통합 |
| `MEP3.1.md` | MEP3.2로 대체 |
| `ma_merger_arb_limitation.md` | 참조용 → archive |

---

### 3.4 docs/context/REFACTORING.md

**흡수 대상:**
| 원본 | 흡수 내용 |
|------|-----------|
| `docs/refactor/automation_standards.md` | 전체 |
| `docs/refactor/codebase_analysis.md` | 전체 |
| `docs/refactor/user001.md` | DI 섹션만 |

**최종 섹션 구성:**
1. 코드베이스 현황 분석
2. 리팩터링 우선순위 Top 10
3. 자동화 도구 (Ruff, mypy, import-linter, pydeps)
4. Dependency Injector 패턴
5. PR 템플릿 & 체크리스트

---

## 4. 폐기 예정 문서

통합 완료 후 삭제 또는 archive 이동:

| 문서 | 처리 |
|------|------|
| `CLAUDE.md` | @PROJECT_DNA에 흡수 → 삭제 |
| `docs/Plan/masterplan.md` | ARCHITECTURE + strategy/에 분산 → archive |
| `docs/architecture/*.md` | ARCHITECTURE에 흡수 → 삭제 |
| `docs/strategy/*.md` (21개) | strategy/ 폴더에 3개로 통합 → archive |
| `docs/refactor/user001.md` | REFACTORING에 흡수 → 삭제 |

---

## 5. 실행 순서

| 단계 | 작업 | 예상 소요 |
|------|------|-----------|
| 1 | `docs/context/`, `docs/context/strategy/` 폴더 생성 | 1분 |
| 2 | ARCHITECTURE.md 작성 | 30분 |
| 3 | strategy/seismograph.md 작성 | 40분 |
| 4 | strategy/mep.md 작성 | 30분 |
| 5 | strategy/ignition.md 작성 | 20분 |
| 6 | REFACTORING.md 작성 | 20분 |
| 7 | @PROJECT_DNA.md 업데이트 | 15분 |
| 8 | 기존 문서 archive 이동 | 10분 |
| 9 | 참조 링크 정리 | 10분 |

**총 예상: 약 3시간**

---

## 6. 검증

- [ ] @PROJECT_DNA.md에서 모든 핵심 문서 참조 가능
- [ ] AI가 5개 문서(ARCH + REFAC + 3 전략)로 프로젝트 이해 가능
- [ ] 중복 내용 0%
- [ ] 기존 정보 손실 없음 (archive로 보존)
