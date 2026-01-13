# r04 전략 시스템 오버뷰 v1.0

> **작성일**: 2026-01-12 | **기반**: 17개 전략 문서 종합
> **핵심 원리**: 유동성 우선성 (Liquidity Primacy Thesis)

---

## 1. 핵심 철학

> **"개잡주 트레이딩의 본질은 '가격 예측'이 아니라, '실행 가능한 유동성 상태 전이'를 포착하는 것이다."**

| 기존 사고 | 새로운 사고 |
|-----------|-------------|
| 엣지 = 예측 | **엣지 = 필터링 + 손실 구조 설계** |
| 모델이 맞추는가? | **틀렸을 때 비용 구조는?** |
| 언제 진입하나? | **언제 진입하지 말아야 하나?** |

---

## 2. 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     STAGE 1: Universe Filtering                 │
│  [Float < 20M] + [RVOL > 3x] + [Catalyst 있음] + [¬ATM]         │
│                           ↓                                     │
│                      WATCHLIST 등록                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     STAGE 2: Entry Timing                       │
│                                                                 │
│  [구조 조건] ─→ ARMED ─→ [테이프 트리거] ─→ TRIGGERED           │
│       ↓           │              ↓                              │
│  VWAP 상방      Timeout        체결 가속                        │
│  스프레드 축소  Half-Life×0.3  스프레드↓                        │
│  레벨 돌파        ↓                                             │
│                 IDLE                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   4계층 실행 레짐 모니터                         │
│                                                                 │
│  Layer 4: 매크로 상태 ─→ 🟢Green │ 🟡Yellow │ 🔴Red             │
│  Layer 3: 마이크로 상태 ─→ ABSORPTION │ VACUUM │ DISTRIBUTION   │
│  Layer 2: 파생 지표 ─→ tape_accel │ trade_imbalance │ absorption│
│  Layer 1: 원시 지표 ─→ trade_volume │ effective_spread │ VWAP   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   반박 게이트 (Adversarial Gate)                 │
│                                                                 │
│  [시간대] ─→ Dead Zone (11:30-14:00)?          → 🔴 봉쇄        │
│  [Rotation] ─→ FATIGUE 상태?                   → 🟡 경고        │
│  [Half-Life] ─→ 촉매 없음/원인 불명?           → 🔴 봉쇄        │
│  [실행 레짐] ─→ Red 상태?                      → 🔴 봉쇄        │
│  [일일 손실] ─→ 80% 도달?                      → 🟡 사이즈 50%  │
│  [붕괴 경보] ─→ Yellow 이상?                   → 🟡 경고        │
│                           ↓                                     │
│              🟢 All Clear │ 🟡 Warning │ 🔴 Blocked             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      진입/청산 실행                              │
│                                                                 │
│  [🟢 All Clear] ─→ 표준 진입                                    │
│  [🟡 Warning] ─→ 사이즈 축소 or 재검토                          │
│  [🔴 Blocked] ─→ 진입 불가                                      │
│                                                                 │
│  [붕괴 경보 Red] ─→ 즉시 청산 트리거                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Stage 1: Universe Filtering

| 필터 | 임계값 | 데이터 소스 |
|------|--------|------------|
| Float | < 10-20M (정책별) | SEC Edgar, yfinance |
| RVOL | > 3-5x | 자체 계산 |
| Catalyst | 존재 | News API |
| ATM Offering | 없음 | SEC filings |

**출력**: WATCHLIST 등록 + 메타데이터 (Float, RVOL, Catalyst 유형, Half-Life 추정)

---

## 4. Stage 2: Entry Timing

### 4.1 ARMED 상태 FSM

```
IDLE → [구조 충족] → ARMED → [테이프 트리거] → TRIGGERED → IN_POSITION
                        ↓ [Timeout 또는 Red 전환]
                      IDLE (기회 소멸)
```

### 4.2 ARMED 진입 조건

| 조건 | 판정 기준 |
|------|----------|
| VWAP 상방 | price > VWAP |
| 체결 가속 | tape_accel > 0 |
| 스프레드 안정 | effective_spread ≤ baseline |
| 레벨 돌파 | price > HOD or PMH |

### 4.3 Half-Life 기반 Timeout

| 촉매 유형 | Half-Life | Timeout | 트레일링 강도 |
|-----------|-----------|---------|--------------|
| FDA 승인 | 수 시간 | 30분 | 느슨 |
| 계약 발표 | 1-3시간 | 15분 | 중간 |
| 테마 편승 | 30분-1시간 | 5분 | 공격적 |
| 원인 불명 | 수 분 | 1분 | 극공격/봉쇄 |

---

## 5. 4계층 실행 레짐 모니터

### Layer 1: 원시 지표

| 지표 | 계산 | 데이터 |
|------|------|--------|
| trade_volume | Σ(size) / Δt | Time & Sales |
| effective_spread | 2 × |price - mid| / mid | NBBO |
| bid/ask_volume | 방향별 체결량 | T&S + Lee-Ready |

### Layer 2: 파생 지표

| 지표 | 계산 | 의미 |
|------|------|------|
| tape_accel | d(velocity)/dt | 체결 가속도 |
| trade_imbalance | (bid-ask)/total | 방향 불균형 |
| absorption_ratio | Tick Proxy (MVP) | 흡수 효율 |
| rotation_velocity | d(cumVol/Float)/dt | Float 회전 속도 |
| rotation_accel | d(velocity)/dt | 회전 가속도 |

### Layer 3: 마이크로 상태

| 상태 | 조건 | 의미 |
|------|------|------|
| ABSORPTION | 대량체결 + 가격유지 | 받아주고 있음 |
| VACUUM | tape_accel↑ + ask↓ | 유동성 고갈 |
| DISTRIBUTION | imbalance < -0.3 | 분배 중 |
| EXHAUSTION | tape_accel↓ + spread↑ | 소진 |

### Layer 4: 매크로 상태

| 상태 | 합성 조건 | 행동 |
|------|----------|------|
| 🟢 Green | ABSORPTION ∨ VACUUM | 진입 허용 |
| 🟡 Yellow | DISTRIBUTION ∨ EXHAUSTION | 진입 주의 |
| 🔴 Red | PANIC ∨ spread > critical | 진입 차단 |

---

## 6. Rotation 가속도 기반 상태 (r04-03)

| 상태 | 조건 | 의미 |
|------|------|------|
| FUEL | accel > +θ | 회전 가속, 연료 상태 |
| TRANSITION | |accel| ≤ θ | 중립, 방향 불명 |
| FATIGUE | accel < -θ (N초 지속) | 회전 둔화, 피로 |

---

## 7. 붕괴 예고 시스템 (Collapse Warning)

```
[원인] rotation_accel < 0 (FATIGUE)
  AND
[증상] spread↑ OR tape_accel < 0 (실행 레짐 악화)
  →
⚠️ "분배/덤프 임박" 경보
```

| 경보 | 조건 | 행동 |
|------|------|------|
| ⚠️ Yellow | 원인 OR 증상 | 신규 진입 금지 |
| 🔴 Red | 원인 AND 증상 | **즉시 청산** |

---

## 8. Moderators (효과 조절자)

| Moderator | 효과 증폭 | 효과 반전 |
|-----------|----------|----------|
| 시간대 | 09:30-10:30 | 11:30-14:00 Dead Zone |
| Rotation | FUEL 상태 | FATIGUE 상태 |
| Short Interest | 20-50% | 50%+ (과열) |
| Half-Life | 강한 촉매 | 원인 불명 |

---

## 9. 공격성 동적 조절 (Regime-Based)

### 9.1 시장 레짐

| 레짐 | 지표 | 공격성 |
|------|------|--------|
| Bull | 데이게이너 다수 | 1.5x |
| Neutral | 혼조 | 1.0x |
| Chop | 휩소 빈발 | 0.5x |
| Bear | 데이루저 우세 | 0.3x |

### 9.2 정책 분리

| 정책 | Float | 리버설 | 오버나잇 |
|------|------|--------|---------|
| Aggressive | 20M | 허용 | 선택적 |
| Standard | 10M | 금지 | 금지 |
| Conservative | 5M | 금지 | 금지 |

---

## 10. 손실 구조 설계

> **"모델이 맞추는가 아니라, 틀렸을 때 비용 구조가 핵심"**

- **자동 손절 시스템 필수** (심리적으로 안 지켜짐)
- Half-Kelly 또는 1/4 Kelly 사이징
- 일일 손실 한도 80% 도달 시 사이즈 50% 감소

---

## 11. 구현 우선순위

| 우선순위 | 모듈 |
|----------|------|
| 🔴 P0 | 로그 체계 (상태 전이 기록) |
| 🔴 P0 | 실행 레짐 모니터 |
| 🔴 P0 | 자동 손절 시스템 |
| 🟡 P1 | 반박 게이트 UI (신호등) |
| 🟡 P1 | 시간대 스케줄러 |
| 🟡 P1 | Stage 1 스캐너 |
| 🟢 P2 | 붕괴 경보 시스템 |
| 🟢 P2 | Rotation 위상 분류기 |
| 🔵 P3 | Half-Life 추정기 |

---

## 12. MVP 데이터 요구 (r04-05/06 결론)

| 데이터 | MVP 해결책 | V2 (L2 추가) |
|--------|-----------|--------------|
| trade | Massive T | - |
| NBBO | Massive Q | - |
| trade_side | Lee-Ready (85-90%) | - |
| absorption | **Tick Proxy** | L2 기반 |
| Adaptive Order | ❌ | L2 → 최적가 |
| Dynamic Exit | ❌ | L2 → 저항 확인 |

---

## 13. 참조 문서 계층

| 레벨 | 문서 | 내용 |
|------|------|------|
| L0 | r04-04 | **시스템 아키텍처** |
| L0 | r04-03 | **QTS 피드백 통합** |
| L1 | r04-05 | 데이터 밴더 선정 |
| L1 | r04-06 | L2 알파 토론 |
| L2 | r04-02 | 방법론 토론 |
| L2 | r04-01 | 50턴 토론 |
| L3 | r03-* | 전략 융합 |
| L3 | r02-* | 플레이북 비교 |
| L4 | anth/cgpt/gem/perp | 원본 플레이북 |

---

*작성일: 2026-01-12*
*버전: v1.0*
