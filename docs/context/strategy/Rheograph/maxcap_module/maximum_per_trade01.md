아래 문서의 철학(= **유동성 우선성**, “예측”이 아니라 **실행 가능한 상태 전이**)에 맞춰, **“무한 자본”이어도 결국 시장(미시구조)이 허용하는 범위 안에서만 ‘가격에 영향을 주지 않는’ 최대 사이즈**를 계산하는 논리를 설계하겠습니다. 핵심은 한 줄입니다:

> **최대 사이즈 = (진입에서 안 밀리고) ∧ (붕괴 시 즉시 빠질 수 있는) ‘시장 수용량(capacity)’의 최소값**

---

## 0) 먼저 “가격에 영향을 주지 않는다”의 정량 정의

무한 자본이면 “리스크(자본)”이 아니라 **유동성(용량)**이 상한입니다.
따라서 “노임팩트”를 아래 중 하나(또는 조합)로 정의해야 계산이 됩니다.

### (A) 참여율(Participation) 기반 정의 (가장 실용적)

* 내가 **Δt 실행 창**에서 체결한 물량이
  **해당 창 전체 체결량의 π 이하**이면 “노임팩트”
* 즉, **Q ≤ π · V(Δt)**

여기서

* Q = 내 주문 수량(주)
* V(Δt) = Δt 동안의 총 체결량(주) (Tape 기반)
* π = 허용 참여율 (상태/시간대/스프레드에 따라 동적)

### (B) “가격 발자국(footprint)” 기반 정의 (L2 있으면 더 정밀)

* 내 주문으로 **호가를 k틱 이상 걷지 않는다**
* 즉, **Q ≤ Σ depth(0…k틱) + refill_rate·Δt**

(A)는 L2 없어도 되므로 MVP에 적합하고, (B)는 V2(L2)에서 강해집니다.

---

## 1) “최대 사이징”의 최종 산출물 (정확히 무엇을 뱉을 것인가)

실전에서 필요한 출력은 3개입니다.

1. **Q_in_max**: “이 진입 조건에서” 노임팩트로 들어갈 수 있는 최대 주수
2. **Q_out_max**: “붕괴(경보 Red) 상황에서” 즉시 나올 수 있는 최대 주수
3. **Q_max = min(Q_in_max, Q_out_max, Q_float_cap, GateCap)**

그리고 달러로 바꾸면

* **Notional_max = Q_max · price**

여기서 중요한 건 **항상 ‘출구’가 더 빡빡해서 Q_out_max가 병목**이 되는 경우가 많다는 점입니다(개잡주 특성).

---

## 2) 입력 데이터 (문서의 Layer 구조와 1:1 대응)

문서의 Layer를 그대로 씁니다.

### Layer 1 (원시)

* trade_volume (주/초): 최근 N초의 Tape 체결량/시간
* effective_spread (달러 또는 bps)
* NBBO bid/ask size (가능하면)
* price, mid

### Layer 2 (파생)

* tape_accel
* trade_imbalance
* absorption_ratio (MVP는 Tick Proxy)
* rotation_velocity / rotation_accel

### Layer 3/4 (상태)

* Micro: ABSORPTION / VACUUM / DISTRIBUTION / EXHAUSTION
* Macro: 🟢/🟡/🔴
* Collapse Warning: Yellow/Red
* Rotation state: FUEL / FATIGUE

### Moderators

* 시간대(오프닝/데드존)
* Half-Life 추정치(→ Timeout)
* Short interest 구간(선택)

---

## 3) 실행 창(Δt) 설계: “언제까지 채워야 노임팩트인가?”

사이즈는 결국 **“얼마나 빨리 채우느냐”**와 직결됩니다.
문서에 이미 ARMED_Timeout이 있으니 이를 **사이징용 실행창으로 투영**합니다.

### 3.1 진입 실행창 Δt_in (Fill-time budget)

추천 형태(안정적):

* **Δt_in = clamp(2s, 0.02 · ARMED_Timeout, 20s)**

설명:

* Half-Life가 길어도 “엔트리 타이밍”은 보통 초~수십초가 승부입니다.
* ARMED_Timeout(분 단위)을 그대로 쓰면 너무 큽니다 → 2%만 사용.
* 너무 짧게 잡히면(원인불명 등) 최소 2초는 보장.

### 3.2 청산 실행창 Δt_out (Emergency exit budget)

붕괴 경보 Red는 “즉시 청산”이므로 더 공격적으로:

* **Δt_out = clamp(1s, 0.005 · ARMED_Timeout, 8s)**

---

## 4) 허용 참여율 π 설계: 상태/시간대/스프레드로 동적

π는 “노임팩트”의 핵심 노브입니다. 문서의 신호등(🟢🟡🔴)과 마이크로상태를 그대로 매핑합니다.

### 4.1 기본값 (MVP)

* 🟢 & ABSORPTION: π_base = 8%
* 🟢 & VACUUM: π_base = 3%  (얇은 유동성이라 더 보수)
* 🟡: π_base = 2%
* 🔴: 0%

*(수치는 시작점입니다. 실제로는 로그로 보정해야 합니다.)*

### 4.2 Moderator로 곱셈 보정

* 시간대: 오프닝(09:30-10:30) ×1.3, 데드존(11:30-14:00) ×0 (봉쇄)
* Rotation: FUEL ×1.2, FATIGUE ×0.6
* Collapse Warning: Yellow ×0.5, Red ×0 (즉시청산 모드)
* effective_spread:

  * spread가 baseline 이하: ×1.1
  * spread가 baseline 초과: ×0.7
  * spread > critical: ×0 (문서의 Red 조건)

최종:

* **π_in = clip(π_base_in · Mods, 0, π_ceil)**
* **π_out = clip(π_base_out · Mods, 0, π_ceil_out)**

(보통 π_out이 π_in보다 더 보수적이어야 합니다. “나갈 때”는 시장이 얇아지는 방향이기 때문입니다.)

---

## 5) 최대 사이즈 계산식 (MVP: Tape 기반, V2: L2 기반)

### 5.1 MVP(=Tape 기반 용량)

최근 N초(예: 5~10초)에서

* v = trade_volume_rate = Σsize / Δt  (주/초)

그럼

* **Q_in_max = π_in · v · Δt_in**
* **Q_out_max = π_out · v_panic · Δt_out**

여기서 **v_panic**은 “붕괴 시 실제 유효 체결률”인데, 붕괴에서는 보통 체결률이 *늘기도/줄기도* 해서 애매합니다. 안전하게는:

* **v_panic = v · panic_discount**
* panic_discount 추천 시작값:

  * 정상(🟢): 1.0
  * 🟡/FATIGUE/imbalance 악화: 0.6
  * EXHAUSTION 징후(spread↑, tape_accel↓): 0.4

즉, **출구는 ‘보수적 체결률’로 계산**해야 합니다.

---

### 5.2 V2(=Depth/호가 기반 추가 상한)

“k틱 이상 걷지 않는다”를 조건으로:

* D_ask(k) = ask side 0~k틱 누적 물량
* D_bid(k) = bid side 0~k틱 누적 물량
* refill_rate = 상위 호가 리필 속도(주/초)

그러면

* **Q_in_depth = D_ask(k) + refill_rate_ask · Δt_in**
* **Q_out_depth = D_bid(k) + refill_rate_bid · Δt_out**

최종 상한은:

* **Q_max = min(Q_in_max, Q_out_max, Q_in_depth, Q_out_depth, …)**

---

## 6) “개잡주 특화” 추가 캡 2개 (실제로 중요)

### 6.1 Float 점유 캡 (Q_float_cap)

무한자본이더라도, float 대비 비중이 커지면 **“내가 유동성 그 자체”**가 되어버려서 출구가 망가집니다(사실상 임팩트).

* **Q_float_cap = φ · Float**

φ 시작값(정책별 예시):

* Aggressive: 0.3%
* Standard: 0.15%
* Conservative: 0.08%

### 6.2 “이벤트/하프-라이프” 기반 캡 (Q_HL_cap)

Half-Life가 짧을수록(테마/원인불명) **엣지 창이 짧고 붕괴도 빠르므로** Δt_out이 더 짧아야 하고, 결과적으로 사이즈가 자동으로 줄어야 합니다.

이건 위에서 Δt_in/Δt_out로 이미 반영되지만, **원인불명/촉매 불명확**은 문서에서도 봉쇄/극공격이라 별도 캡을 하나 더 두는 게 안전합니다:

* catalyst = 원인불명 → **Q_max × 0.3** (또는 Block)

---

## 7) 최종 결론: “최대 사이징” 의사결정 트리

1. Gate:

* 🔴 Blocked → Q=0
* 🟡 Warning → 최종 Q에 ×0.5 (문서와 동일)

2. 상태 결정:

* Micro(ABS/VAC/DIST/EXH), Macro(🟢🟡🔴), Rotation(FUEL/FATIGUE), CW(Y/R)

3. Δt_in, Δt_out 산출 (Timeout 기반)

4. π_in, π_out 산출 (상태+Moderator)

5. Q_in_max, Q_out_max 계산 (Tape)

6. (가능 시) Depth cap 추가 (L2/NBBO)

7. Float cap / catalyst cap / spread critical cap 적용

8. **Q_max = min(모든 캡)**
   → Notional_max = Q_max · price

---

## 8) 운영적으로 “이 논리가 진짜로 맞아지려면” (로그 최소셋)

문서의 로그 철학과 완전히 일치합니다. 이 사이징은 **캘리브레이션**이 없으면 숫자가 “그럴싸한 가정”으로 남습니다. 그래서 최소로 이걸 남겨야 합니다:

* (entry) 당시 v(주/초), effective_spread, 상태(🟢/🟡/🔴 + micro), Δt_in, π_in, 실제 체결 완료 시간
* (exit) 붕괴 경보 발생 시 v 변화, 실제 청산 소요 시간, 슬리피지/가격 이탈
* (결과) “Q가 커질수록” 슬리피지가 실제로 증가했는지(=임팩트 발생) 여부

이걸로 결국 해야 하는 건 1개입니다:

* “내가 노임팩트라고 믿었던 π/Δt 조합이, 실제로는 몇 분위(예: 90% 케이스)까지 안전했나?”를 업데이트

---

원하시면, 위 로직을 **당신 문서의 컴포넌트명(예: r04-03 Rotation, Collapse Warning, Gate UI)**에 맞춰서 “모듈 I/O 명세(입력/출력/필드명/로그 스키마)” 형태로 더 딱딱하게 정리해드리겠습니다.
