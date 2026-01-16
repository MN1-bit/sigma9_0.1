<root_instruction>
  <critical_warning>
    YOU MUST READ THIS DOCUMENT BEFORE GENERATING ANY CODE.
    IGNORING THESE RULES WILL CAUSE SYSTEM CRASH.
  </critical_warning>

  <project_dna>
# 🧬 PROJECT_DNA.md — Σ-IX (Sigma-Nine)

> **For AI Agent (Google Antigravity)**  
> **Version**: 4.0 | **Last Updated**: 2026-01-16  
> **Philosophy**: "Detect the Accumulation, Strike the Ignition, Harvest the Surge."

> [!IMPORTANT]
> **AWS 이식 계획**: 현재 로컬 개발 환경에서 운영 중. 향후 Backend 서버를 AWS EC2 (us-east-1)로 이식 예정.
> Frontend는 Windows 로컬 클라이언트로 유지.

---

## 🎯 Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | Sigma9 (Σ-IX) |
| **Domain** | Automated US Microcap Stock Trading System |
| **Language** | Python (Backend + Frontend) |
| **Primary Language** | Korean (code comments, docs) |

---

## 🏗️ Architecture Overview

> 📐 **상세 아키텍처**: [Full_DataFlow.md](docs/_architecture/Full_DataFlow.md)

**High-Level**: AWS Backend (FastAPI + IBKR Gateway) ↔ WebSocket ↔ Windows Client (PyQt6)

---

## 📂 Project Structure

> 📂 **전체 파일 구조**: [_index.md](docs/_architecture/_index.md)

```
Sigma9-0.1/
├── backend/          # AWS 배포 대상 (FastAPI, DI Container, Strategies)
├── frontend/         # Windows 로컬 (PyQt6 대시보드)
├── docs/             # 문서 (_architecture, devlog)
└── .agent/           # AI Agent 설정 (workflows, Ref)
```

---

## 🛠️ Tech Stack

| Layer | Stack |
|-------|-------|
| **Backend** | `FastAPI` + `uvicorn`, `ib_insync`, `pandas` + `pandas_ta`, `SQLite` (WAL), `SQLAlchemy`, `loguru` |
| **Frontend** | `PyQt6` + `qfluentwidgets`, `pyqtgraph`, `httpx`, `websockets`, `qasync` |
| **LLM** | `openai` / `anthropic` / `google` (Read-Only Oracle) |

---

## 🎨 Design System

| Theme | `PyQt-Fluent-Widgets` Glassmorphism |
|-------|-------------------------------------|
| **Policy** | [/Theme-policy](.agent/workflows/Theme-policy.md) |

---

## 📌 Design Principles

1. **Backend/Frontend 분리**: AWS 마이그레이션 용이성 확보
2. **Strategy = Scanning + Trading**: 전략이 자체 스캐닝 로직 보유
3. **Strategy Pattern + Plugin Architecture**: 런타임 전략 교체 가능
4. **ABC 인터페이스**: `StrategyBase` 상속 필수 ([/StrategyBase-interface](.agent/workflows/StrategyBase-interface.md))
5. **Hot Reload**: 서버 재시작 없이 전략 파일 교체
6. **Server-Side OCA**: 모든 청산 로직은 서버에서 처리

---

## 🛣️ Development Process

> **모든 개발은 워크플로우를 따릅니다.**
>
> | Phase | Workflow |
> |-------|----------|
> | 계획 | [/IMP-planning](.agent/workflows/IMP-planning.md) |
> | 실행 | [/IMP-execution](.agent/workflows/IMP-execution.md) |
> | 검증 | [/IMP-verification](.agent/workflows/IMP-verification.md) |

---

## 💻 Development Commands

```bash
# 실행
python -m backend              # FastAPI (http://localhost:8000/docs)
python -m frontend             # PyQt6 GUI


---

## 📚 Quick Reference Hub

### 아키텍처 & 구조
| 문서 | 설명 |
|------|------|
| [📂 _index.md](docs/_architecture/_index.md) | 전체 파일 구조 + 문서화 현황 |
| [🔀 Full_DataFlow.md](docs/_architecture/Full_DataFlow.md) | 데이터 흐름 다이어그램 |

### 개발 워크플로우
| 워크플로우 | 용도 |
|-----------|------|
| [/IMP-planning](.agent/workflows/IMP-planning.md) | 구현 계획서 작성 |
| [/IMP-execution](.agent/workflows/IMP-execution.md) | 구현 실행 + 코딩 규칙 |
| [/IMP-verification](.agent/workflows/IMP-verification.md) | 구현 검증 + 품질 검사 |
| [/StrategyBase-interface](.agent/workflows/StrategyBase-interface.md) | 전략 인터페이스 명세 |
| [/Theme-policy](.agent/workflows/Theme-policy.md) | GUI 테마 정책 |

### API 문서
- **Swagger UI**: `http://localhost:8000/docs` (서버 실행 후)

---

> **"Smart money leaves footprints. We just need to read them."**
  </project_dna>
</root_instruction>
