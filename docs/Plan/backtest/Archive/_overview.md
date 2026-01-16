# 001-01: Backtest 모듈 구축 계획서

> **문서 번호**: 001-01  
> **작성일**: 2026-01-15  
> **상태**: 초안  
> **목표**: Rheograph 전략 백테스트 시스템 구축 및 전략 승격 파이프라인 설계

---

## 1. 개요

### 1.1 목표
1. Rheograph 전략을 과거 데이터로 검증하는 백테스트 시스템 구축
2. GUI에서 백테스트 실행/결과 조회 가능
3. 검증된 전략을 라이브 트레이딩으로 승격하는 파이프라인 구축

### 1.2 개발 철학: 플랫폼 우선

> [!IMPORTANT]
> **플랫폼 먼저, 전략은 나중에**  
> 이 프로젝트의 1차 목표는 **범용 백테스트 플랫폼** 구축입니다.  
> Rheograph 등 특정 전략 적용은 플랫폼 완성 이후 단계입니다.

**핵심 설계 원칙:**
- **전략 불가지론(Strategy-Agnostic)**: 플랫폼은 특정 전략에 종속되지 않음
- **플러그인 아키텍처**: 새 전략 개발 시 `back_strat/` 폴더에 드롭인 방식으로 적용
- **표준 인터페이스**: 모든 전략은 동일한 입출력 규격 준수
- **빠른 반복**: 전략 코드 변경 → 즉시 백테스트 실행 가능

```
                    ┌─────────────────────────────────┐
                    │       백테스트 플랫폼 (Core)      │
                    │  ┌───────────────────────────┐  │
                    │  │ Engine │ DataFeed │ Report│  │
                    │  └───────────────────────────┘  │
                    └─────────────┬───────────────────┘
                                  │ 표준 인터페이스
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
   │  Rheograph  │        │  Strategy B │        │  Strategy N │
   │  (Phase 2)  │        │  (Future)   │        │  (Future)   │
   └─────────────┘        └─────────────┘        └─────────────┘
```

### 1.3 핵심 요구사항
| 요구사항 | 설명 |
|----------|------|
| Point-in-time 데이터 | 미래 정보 누출 방지 |
| 전략 코드 재사용 | 백테스트 ↔ 라이브 동일 로직 |
| 전략 승격 | 사용자 승인 시 라이브 전략으로 이동 |
| API 노출 | GUI에서 제어 가능 |

---

## 2. 폴더 구조

```
Sigma9-0.1/
├── backend/
│   ├── api/
│   │   └── routers/
│   │       └── backtest.py           # 백테스트 API 라우터
│   │
│   ├── backtest/                      # 🆕 백테스트 모듈
│   │   ├── __init__.py
│   │   ├── __main__.py                # CLI 진입점
│   │   │
│   │   ├── engine/                    # 백테스트 엔진
│   │   │   ├── __init__.py
│   │   │   ├── runner.py              # Backtrader 래퍼
│   │   │   ├── analyzer.py            # 결과 분석기
│   │   │   └── simulator.py           # 브로커 시뮬레이터
│   │   │
│   │   ├── data/                      # 데이터 피드
│   │   │   ├── __init__.py
│   │   │   ├── parquet_feed.py        # Parquet → Backtrader
│   │   │   └── polygon_feed.py        # Polygon API 연동 (옵션)
│   │   │
│   │   ├── indicators/                # 커스텀 지표
│   │   │   ├── __init__.py
│   │   │   ├── rvol.py                # RVOL (실시간/누적)
│   │   │   ├── dollar_float.py        # Dollar Float
│   │   │   └── tape_accel.py          # 체결 가속도
│   │   │
│   │   ├── reports/                   # 리포트 생성
│   │   │   ├── __init__.py
│   │   │   ├── html_report.py
│   │   │   └── json_export.py
│   │   │
│   │   ├── back_strat/                # 🆕 백테스트 전략 저장소
│   │   │   ├── __init__.py
│   │   │   ├── _template/             # 전략 템플릿
│   │   │   │   ├── __init__.py
│   │   │   │   ├── strategy.py
│   │   │   │   └── config.yaml
│   │   │   │
│   │   │   └── rheograph/             # Rheograph 전략
│   │   │       ├── __init__.py
│   │   │       ├── config.yaml        # 전략 설정
│   │   │       ├── scanner.py         # 스캐너 로직
│   │   │       ├── playbooks/         # 플레이북들
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py
│   │   │       │   ├── hod_break.py
│   │   │       │   ├── vwap_reclaim.py
│   │   │       │   ├── first_pullback.py
│   │   │       │   ├── gap_and_go.py
│   │   │       │   ├── halt_reopen.py
│   │   │       │   └── washout_reversal.py
│   │   │       └── fsm.py             # 포지션 FSM
│   │   │
│   │   └── config.yaml                # 백테스트 글로벌 설정
│   │
│   ├── strategies/                    # 라이브 전략 (승격 후)
│   │   ├── __init__.py
│   │   ├── rheograph/                 # 승격된 Rheograph
│   │   │   └── ...                    # back_strat에서 복사됨
│   │   └── ...
│   │
│   └── ...
│
├── data/
│   └── parquet/                       # 백테스트 데이터
│       ├── intraday/
│       └── daily/
│
└── docs/
    └── plan/
        └── backtest/
            └── 001-01.md              # 이 문서
```

---

## 3. 전략 승격 파이프라인

### 3.0 핵심 원칙: 폴더 단위 관리

> **전략 = 폴더**  
> - 모든 전략은 `back_strat/` 아래 **독립된 폴더**로 생성·관리됩니다.
> - 승격 시 해당 전략 폴더를 **통째로** `strategies/`로 복사합니다.
> - 폴더 내부 구조 (config, scanner, playbooks, fsm 등)는 그대로 유지됩니다.

```
승격 전:  backend/backtest/back_strat/rheograph/   (폴더 전체)
                                      ├── __init__.py
                                      ├── config.yaml
                                      ├── scanner.py
                                      ├── playbooks/
                                      └── fsm.py

승격 후:  backend/strategies/rheograph/            (폴더째 복사)
                             ├── __init__.py
                             ├── config.yaml       ← promoted: true 추가
                             ├── scanner.py
                             ├── playbooks/
                             └── fsm.py
```

### 3.1 승격 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 개발 (폴더 단위)                                             │
│  backend/backtest/back_strat/new_strategy/                      │
│  └→ 전략 코드 작성, 백테스트 반복                                │
│  └→ 폴더 = 하나의 완결된 전략 단위                               │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. 검증                                                        │
│  - 백테스트 실행                                                │
│  - 성과 리포트 생성                                             │
│  - 기준 충족 여부 판단 (Sharpe > 1.5, MaxDD < 20% 등)          │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. 사용자 승인                                                 │
│  - GUI에서 "승격" 버튼 클릭                                     │
│  - 승격 전 경고: "라이브 자금에 영향을 줍니다"                  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. 승격 실행 (폴더째 복사)                                      │
│  backend/backtest/back_strat/new_strategy/  ← 소스 폴더         │
│                    ↓ shutil.copytree()                          │
│  backend/strategies/new_strategy/           ← 타겟 폴더         │
│  └→ config.yaml에 "promoted: true" 플래그 추가                  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. 라이브 활성화                                               │
│  - 전략 매니저에서 new_strategy 폴더 로드                       │
│  - 페이퍼 트레이딩 모드로 초기 실행 (권장)                      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 승격 API

```python
# backend/api/routers/backtest.py

@router.post("/strategies/{strategy_name}/promote")
async def promote_strategy(
    strategy_name: str,
    confirm: bool = Query(False, description="사용자 확인 여부")
):
    """백테스트 전략을 라이브로 승격"""
    if not confirm:
        raise HTTPException(400, "승격을 확인해주세요 (confirm=true)")
    
    source = Path(f"backend/backtest/back_strat/{strategy_name}")
    target = Path(f"backend/strategies/{strategy_name}")
    
    if not source.exists():
        raise HTTPException(404, f"전략 {strategy_name} 없음")
    
    if target.exists():
        raise HTTPException(409, f"전략 {strategy_name} 이미 승격됨")
    
    # 복사 및 플래그 설정
    shutil.copytree(source, target)
    update_config(target / "config.yaml", {"promoted": True, "promoted_at": datetime.now()})
    
    return {"status": "promoted", "path": str(target)}
```

### 3.3 승격 기준 (권장)

| 지표 | 임계값 | 설명 |
|------|--------|------|
| Sharpe Ratio | > 1.5 | 위험 대비 수익 |
| Max Drawdown | < 20% | 최대 손실폭 |
| Win Rate | > 40% (Early), > 50% (Pullback) | 전략별 기대 승률 |
| Profit Factor | > 1.5 | 총 이익 / 총 손실 |
| Trade Count | > 100 | 통계적 유의성 |
| Out-of-Sample 성과 | 유지 | 과적합 방지 |

---

## 4. 구현 단계

### Phase 1: MVP (2주)

| 태스크 | 설명 | 예상 일수 |
|--------|------|----------|
| 폴더 구조 생성 | 위 구조대로 디렉토리 생성 | 0.5 |
| Backtrader 연동 | runner.py 구현 | 2 |
| Parquet 피드 | parquet_feed.py 구현 | 1 |
| 스캐너 MVP | Dollar Float + RVOL + Gap | 2 |
| HOD Break 플레이북 | 첫 번째 전략 | 2 |
| 기본 리포트 | JSON 성과 출력 | 1 |
| CLI 진입점 | `python -m backend.backtest` | 0.5 |
| **총** | | **9일** |

### Phase 2: 전체 플레이북 (2주)

| 태스크 | 설명 | 예상 일수 |
|--------|------|----------|
| 나머지 5개 플레이북 | VWAP, Pullback, Gap&Go, Halt, Washout | 5 |
| 포지션 FSM | 5상태 전이 구현 | 2 |
| 촉매 티어링 | Tier 1/2/3 분류 | 1 |
| HTML 리포트 | 시각화 리포트 | 2 |
| **총** | | **10일** |

### Phase 3: API & 승격 (1주)

| 태스크 | 설명 | 예상 일수 |
|--------|------|----------|
| API 라우터 | /backtest/* 엔드포인트 | 2 |
| 승격 API | /strategies/promote | 1 |
| 승격 검증 | 기준 체크 로직 | 1 |
| 통합 테스트 | E2E 테스트 | 1 |
| **총** | | **5일** |

### Phase 4: GUI 통합 (2주, 별도 계획)

- 프론트엔드 백테스트 페이지
- 결과 대시보드
- 승격 워크플로우 UI

---

## 5. 기술 스택

| 컴포넌트 | 기술 | 이유 |
|----------|------|------|
| 백테스트 엔진 | Backtrader | 성숙한 이벤트 기반 프레임워크 |
| 데이터 저장 | Parquet (기존) | 이미 구축됨 |
| API | FastAPI (기존) | 기존 backend와 일관성 |
| 리포트 | Jinja2 + Plotly | 인터랙티브 차트 |

---

## 6. 리스크 & 완화

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| 틱/L2 데이터 부재 | 테이프 리딩 정확도 저하 | 분봉 기반 근사, 이후 틱 데이터 추가 |
| 과적합 | 라이브 성과 저조 | Walk-forward 검증, Out-of-Sample 테스트 |
| 승격 후 버그 | 라이브 손실 | 페이퍼 트레이딩 필수, 단계적 자금 증가 |

---

## 7. 연구 과제: 급등 전 스캐닝 전략 (Pre-Surge Detection)

> [!NOTE]
> 이 섹션은 **별도 연구 과정**으로 진행됩니다.  
> 플랫폼 구축 완료 후 본격 연구 착수 예정이며, 여기서는 철학과 논리적 프레임워크만 정의합니다.

### 7.1 연구 목표

**핵심 질문**: *급등 전날/직전에 해당 종목을 스캔할 수 있었는가?*

| 구분 | 설명 |
|------|------|
| 목표 | Daygainer(당일 급등주)의 **급등 이전** 공통 패턴 발굴 |
| 방법론 | Daygainer vs 대조군 비교 분석을 통한 차별화 지표 탐색 |
| 결과물 | "급등 전 스캐닝 전략" — 급등 확률 높은 종목 사전 필터링 |

### 7.2 연구 철학

#### 7.2.1 대조군 설계의 중요성

급등주(Daygainer)만 분석하면 **생존자 편향(Survivorship Bias)**에 빠집니다.  
"이 패턴이 있었다" ≠ "이 패턴이 있으면 급등한다"를 구분해야 합니다.

```
                ┌─────────────────────────────────────────┐
                │           전체 종목 풀 (Universe)         │
                └─────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌─────────────┐                 ┌─────────────┐
            │ Daygainer   │                 │  대조군      │
            │ (급등 발생)  │                 │ (급등 미발생) │
            └─────────────┘                 └─────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                    ┌─────────────────────────────────┐
                    │  D-1, D-2 시점의 지표 비교 분석  │
                    │  → 차별화 지표(Discriminator) 발굴 │
                    └─────────────────────────────────┘
```

**대조군 선정 기준 (v4 확정):**

| 조건 | 값 | 근거 |
|------|-----|------|
| 동일 날짜 | 필수 | 시장 환경 통제 |
| 종가 등락률 | -50% ~ +10% | 급등 실패 ~ 평범 |
| 가격 | ≥ $0.1 | 초저가 제외 |
| RVOL 스파이크 | 분봉 RVOL ≥ 2x 존재 | 관심 받았던 종목 |
| 가격 구간 매칭 | Tier 기반 | 가격 프락시 |
| 비율 | 1:5 | Daygainer당 5개 |

- **Failed Pump 라벨**: RVOL 스파이크 + 장중 고점 대비 30% 하락
- **rvol_max 피처**: 당일 최대 RVOL을 연속값으로 저장
- **상세 계획서**: [003-01_control_group_plan.md](./003-01_control_group_plan.md)

#### 7.2.2 시점 엄격성 (Point-in-Time Discipline)

> [!WARNING]
> **미래 정보 누출(Look-Ahead Bias) 절대 금지**  
> 분석 시점은 반드시 급등 발생 **이전**으로 고정해야 합니다.

| 분석 시점 | 사용 가능 데이터 | 불가 데이터 |
|-----------|-----------------|------------|
| D-1 종가 시점 | D-1까지의 OHLCV, 보조지표 | D-0 데이터 일체 |
| D-0 09:30 시점 | D-1 종가 + 프리마켓 갭 | D-0 정규장 데이터 |

### 7.3 접근 방법론 (확정)

> [!IMPORTANT]
> **결론: ML + LLM 협업 (단계별 역할 분담)**
> 
> "ML이냐 LLM이냐"는 잘못된 질문.  
> 각 단계마다 적합한 도구가 다름.

#### 7.3.1 단계별 역할 분담

| 단계 | 주 담당 | 보조 | 상세 |
|------|---------|------|------|
| **4a. 탐색** | ML | LLM | LLM이 가설 제안 → ML이 정량 검증 → 피드백 |
| **4b. 모델링** | ML | LLM | ML이 분류기 학습, LLM은 피처 아이디어 제공 |
| **4c. 해석** | LLM | ML | ML이 SHAP 수치 제공 → LLM이 자연어 변환 |

#### 7.3.2 탐색 단계 상세 (가설-검증 루프)

```
┌────────────────────────────────────────────────────────────┐
│  LLM ──(가설)──▶ ML ──(검증 결과)──▶ LLM ──(다음 가설)      │
│                    │                                       │
│  예시:             ▼                                       │
│  LLM: "종가 대비 저점 위치가 중요해 보임"                   │
│  → ML: low_to_close_ratio 피처 생성                        │
│  → ML: t-test p < 0.01로 유의미                            │
│  → LLM에 피드백 → 다음 가설 생성                           │
└────────────────────────────────────────────────────────────┘
```

#### 7.3.3 모델링 단계

```python
# 입력
X = daygainer_features + control_features  # (2500, 50)
y = [1]*500 + [0]*2000  # Daygainer=1, Control=0

# 모델
model = XGBClassifier()  # 기본 선택 (대안: LightGBM, TabNet)

# 평가
precision_at_k(y_test, y_pred, k=20)
```

#### 7.3.4 해석 단계

| 해석 유형 | 도구 |
|-----------|------|
| 피처 중요도 랭킹 | ML (SHAP) |
| 개별 예측 설명 | ML (SHAP Local) |
| 자연어 변환 | LLM |
| 도메인 컨텍스트 | LLM |

#### 7.3.5 기술 스택

```yaml
Phase 4a (탐색):
  ml: scipy (t-test), pandas (EDA)
  llm: Claude/GPT-4o (가설 생성)

Phase 4b (모델링):
  library: scikit-learn, xgboost, shap
  validation: TimeSeriesSplit

Phase 4c (해석):
  ml: shap
  llm: Claude/GPT-4o-mini (비용 효율)
```

### 7.4 데이터 요구사항

| 데이터 | 용도 | 현재 상태 |
|--------|------|----------|
| 일간 OHLCV | Daygainer 식별, 대조군 선정 | ✅ 보유 (Parquet) |
| 분봉 데이터 | 급등 전 패턴 분석 | ✅ 보유 (Parquet) |
| 보조지표 로그 | RVOL, ATR, 이평선 등 사전 계산 | 🔲 구축 필요 |
| 카탈리스트 데이터 | 뉴스, SEC 공시 등 | 🔲 Polygon/별도 수집 |

### 7.5 연구 단계

| 단계 | 설명 | 선행 조건 | 상태 |
|------|------|----------|------|
| **R-1** | Daygainer 정의 (75%+, $50만 거래대금) | - | ✅ 완료 |
| **R-2** | 역대 Daygainer 라벨링 | R-1 | ✅ 완료 (1,284건) |
| **R-3** | 대조군 매칭 로직 | R-2 | ✅ 완료 (4,205건) |
| **R-4** | D-1/M-n 피처 파이프라인 | R-3 | 🟡 진행중 |
| **R-5** | 탐색 (EDA) — 가설-검증 루프 | R-4 | ⬜ 대기 |
| **R-6** | 분류 모델 학습 (XGBoost) | R-5 | ⬜ 대기 |
| **R-7** | SHAP + LLM 해석 파이프라인 | R-6 | ⬜ 대기 |
| **R-8** | 백테스트 검증 및 반복 | R-7 | ⬜ 대기 |

**R-4 세부 현황:**
- Phase A (D-1 피처): ✅ 4,894건 완료
- Phase B (M-n 피처): ✅ 35건 완료 (분봉 가용 샘플)
- Phase C (EDA): ✅ 샘플 부족으로 유의미 결과 X
- Phase D (분봉 다운로드): 🟡 진행중 (4,855건)

### 7.6 전문가 리뷰 반영 (reflect01/02)

> [!CAUTION]
> **Phase E 결과 폐기**: pandas_ta CCI 오류, D-1+M-n 혼합 설계, T0 누수 발견  
> → 아래 3-Stage 재설계로 전환

#### 7.6.1 발견된 구조적 문제

| 문제 | 설명 | 영향 |
|------|------|------|
| **단일 모델 혼합** | D-1 스캐너 + M-n 경보를 한 모델로 학습 | 운영 불가능한 룰 도출 |
| **T0 정의 왜곡** | Positive는 +6% 돌파, Control은 HOD fallback | 사후 정보 누수 |
| **평가 지표 불일치** | Recall/Precision vs 필요한 Recall@N | 운영 성능 추정 불가 |

#### 7.6.2 3-Stage 재설계 (대안 B 채택)

```
Stage 0: D-1 Attempt Scanner (has_attempt 예측)
  → 목표: Top-N 후보 선정, Recall@200 ≥ 70%
  
Stage 1: Success vs Fail Classifier (is_success 예측)
  → 목표: Attempt 성공/실패 판별, Precision ≥ 50%
  
Stage 2: Alert Policy
  → 목표: 알림 예산/쿨다운 최적화
```

#### 7.6.3 핵심 정의 변경

| 라벨 | 정의 | 용도 |
|------|------|------|
| **Attempt** | minute_rvol ≥ 3.0 AND (ret_5m ≥ 1.5% OR breakout) | Stage 0 타깃 |
| **Failed Pump** | Attempt 후 HOD 대비 -30% 드로다운 | Stage 1 음성 |

#### 7.6.4 수정된 평가 체계

| 지표 | Stage | 목표 | 측정 방법 |
|------|-------|------|----------|
| Recall@200 | 0 | ≥ 70% | 일별 Top-200 평균 |
| Candidates/day | 0 | 150-250 | 일별 분포 |
| Alerts/day | 1 | 20-50 | 일별 평균 |
| Success Rate | 1 | ≥ 50% | Alerts 중 Daygainer |
| Lead Time | 1 | ≥ 15min | T0 - Alert 시간 |

**상세 문서**: [reflect01.md](./reflect/reflect01.md), [reflect02.md](./reflect/reflect02.md)

---

## 8. 성공 기준

| 기준 | 측정 방법 |
|------|----------|
| MVP 완성 | HOD Break 백테스트 실행 가능 |
| 전략 재사용 | 동일 코드로 백테스트/라이브 실행 |
| 승격 파이프라인 | API로 승격 후 라이브 로드 가능 |
| GUI 통합 | 프론트엔드에서 백테스트 트리거 가능 |
| 연구 환경 구축 | Daygainer 라벨링 및 대조군 비교 분석 가능 |

---

## 9. 다음 단계

1. [ ] 이 계획서 검토 및 승인
2. [ ] Phase 1 세부 태스크 분해 (플랫폼 중심)
3. [ ] 폴더 구조 생성
4. [ ] Backtrader 기본 연동 구현
5. [ ] 연구 과제 R-1: Daygainer 라벨링 기준 정의

---

**문서 이력**
| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| 001-01 | 2026-01-15 | 초안 작성 |
| 001-01a | 2026-01-15 | 플랫폼 우선 철학, 급등 전 스캐닝 연구 과제 추가 |
| 001-01b | 2026-01-15 | _detection.md 동기화: ML+LLM 협업 방법론 확정, 가설-검증 루프 추가 |
| 001-01c | 2026-01-15 | **전문가 리뷰 반영 (reflect01/02)**: 섹션 7.6에 3-Stage 재설계, Phase E 폐기 사유 추가 |
