1) 핵심 원칙

사이징의 본질은 Exit-first + No-impact 두 축이며 

max02

최대 사이즈는 진입 용량과 비상 청산 용량의 최소값입니다. 

maximum_per_trade01

2) 계산 출력

Q_in_max, Q_out_max를 만들고

Q_max = min(Q_in_max, Q_out_max, Q_float_cap, GateCap, …) 

maximum_per_trade01

Notional_max = Q_max · price 

maximum_per_trade01

3) MVP 입력(최소)

bid/ask/mid, last trade price/size, dt

유지 상태변수 1개: L = $/s 체결유동성 EMA 

max02

4) 노임팩트 상한(2중 안전장치)
(A) 참여율 기반

Q ≤ π · V(Δt) 

maximum_per_trade01

π는 상태/시간대/경보/스프레드로 동적 조정 

maximum_per_trade01

(B) 스퀘어루트 임팩트 기반

Impact_{bps} ≈ κ_{bps}·√(Q/V), Q_{max}=V·(B/κ)^2 

max02

κ는 spread로 근사: κ=max(κ_{floor}, k_{spr}·spread_{bps}) 

max02

V(τ)는 L로 근사: V(τ)≈L·τ 

max02

5) Exit-first 구현

진입/청산 각각 계산 후 min: Q_max=min(Q_in,Q_out) 

max02

청산은 더 보수적으로: τ_out(또는 Δt_out) 짧게 + panic_discount 적용 

max02

6) 마이크로캡 특화 캡

Float cap: Q_float_cap = φ·Float 

maximum_per_trade01

Catalyst unknown: Q_max × 0.3 또는 Block 

maximum_per_trade01

7) 게이트/하드게이트

🔴 Blocked → Q=0, 🟡 Warning → 최종 Q × 0.5 

maximum_per_trade01

spread 임계 초과, L 너무 낮음 → Q=0 

max02

8) 튜닝(검증) 최소셋

κ_obs ≈ slippage_{bps}/√(Q/V)로 κ를 분위수 기준 상향 보정 

max02

엔트리/엑싯 로그 최소셋으로 “내가 노임팩트라고 믿은 조합이 실제로 안전했는지” 업데이트 

maximum_per_trade01