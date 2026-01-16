# 02-004: Hotzone 승격 로직 확장 (Day Gainer 지원)

## 문제 설명
Hot Zone으로 승격되는 종목이 없음.

## 근본 원인
현재 승격 로직 (`_check_tier2_promotion`)은 **Ignition Score 업데이트 시에만** 호출됨.
Ignition Score 계산이 비활성화되거나 지연되면 Day Gainer도 승격되지 않음.

```python
# 현재 흐름
_on_ignition_update()  ← Ignition Score WebSocket 수신 시만 호출
    └── _check_tier2_promotion()
            └── _promote_to_tier2()
```

### 기존 승격 조건 (모두 Ignition 의존):
1. Ignition Score ≥ 70
2. Stage 4 VCP
3. zenV-zenP Divergence
4. High Accumulation Score (≥ 80) + Day Gainer

> **문제**: 조건 4가 있지만, `_on_ignition_update`가 호출되지 않으면 검사 자체가 안 됨.

---

## 제안된 해결책

### Watchlist 업데이트 시에도 승격 검사 수행
- `_update_watchlist_panel()`에서 각 항목에 대해 승격 조건 검사
- Day Gainer + High Score 조건을 독립적으로 평가

---

## 수정 파일

### [MODIFY] [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py)

**수정 1**: `_update_watchlist_panel()` (라인 1383~1391)
- 각 항목에 대해 승격 조건 검사 추가

```python
# Model 업데이트 후 승격 조건 검사
item_data = {
    "ticker": ticker,
    "change_pct": change_pct,
    "dollar_volume": dollar_volume,
    "score": score,
    "ignition": ignition_score,
}
self.watchlist_model.update_item(item_data)

# [Issue 01-005] Watchlist 업데이트 시에도 승격 조건 검사
if ticker not in self._tier2_cache:  # 이미 Tier2가 아닌 경우만
    # Ignition 캐시에서 조회 (0이면 Ignition 미계산 상태)
    cached_ignition = self._ignition_cache.get(ticker, 0)
    should_promote, reason = self._check_tier2_promotion(
        ticker, cached_ignition, passed_filter=True,
        data={"source": source, "score": score, "stage_number": stage_number}
    )
    if should_promote:
        self.particle_system.take_profit()
        self._play_ignition_sound()
        self.log(f"[TIER2] {reason}: {ticker} (Score={score:.0f})")
        self._promote_to_tier2(ticker, cached_ignition)
```

**수정 2**: `_check_tier2_promotion()` - `data` 파라미터 활용 개선

현재 조건 4에서 `source`와 `acc_score`를 `watchlist_entry` 캐시에서 가져오는데,
이미 위에서 계산된 값을 직접 전달받아 사용하도록 개선:

```diff
     # 4. High Accumulation Score (≥ 80) + Day Gainer
-    acc_score = watchlist_entry.get("score", 0) if isinstance(watchlist_entry, dict) else 0
-    source = watchlist_entry.get("source", "") if isinstance(watchlist_entry, dict) else ""
+    # data 파라미터에서 우선 조회 (Watchlist 업데이트 시 전달됨)
+    acc_score = data.get("score", 0) if data else watchlist_entry.get("score", 0)
+    source = data.get("source", "") if data else watchlist_entry.get("source", "")
     if acc_score >= 80 and source == "realtime_gainer":
         return True, "⭐ High Score Gainer"
```

---

## 검증 계획

### 수동 테스트
1. 애플리케이션 실행: `python -m frontend.main`
2. 시장 개장 시간에 Day Gainer가 Watchlist에 표시될 때까지 대기
3. Score ≥ 80인 Day Gainer가 자동으로 Hot Zone에 승격되는지 확인
4. 로그에서 `[TIER2] ⭐ High Score Gainer:` 메시지 확인

> [!IMPORTANT]
> 프리마켓/애프터마켓에서는 Day Gainer 데이터가 없을 수 있습니다.
> 정규 거래 시간(9:30 AM - 4:00 PM EST)에 테스트하세요.
