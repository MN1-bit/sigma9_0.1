# 02-001c: Score V2 툴팁 계산 요소 표시

**상태**: ✅ 완료  
**작성일**: 2026-01-06

---

## 목표

Watchlist의 Score 컬럼에 마우스를 올렸을 때, 계산에 사용된 4가지 신호 강도를 툴팁으로 표시하여 투명성을 높입니다.

---

## 현재 상태

| 상태 | Score V2 표시 |
|------|--------------|
| `score_v2 > 0` | 숫자 (예: 35.0) |
| `score_v2 == 0` | ➖ (매집 신호 없음) |
| `score_v2 == -1` | 🆕 (데이터 부족) |
| `score_v2 is None` | ⚠️ (계산 실패) |

**문제**: 숫자만으로는 **왜** 그 점수가 나왔는지 알 수 없음

---

## 제안 솔루션

### 툴팁 형식

```
📊 Score V2: 35.0

• Tight Range:    ██░░░ 0.25
• OBV Divergence: █████ 1.00  ⬅ 주요
• Accum Bar:      ░░░░░ 0.00
• Volume Dryout:  ░░░░░ 0.00

가중합: (25×0.25 + 35×1.0 + 25×0.0 + 15×0.0) = 41.25
```

### 이모지 케이스 툴팁

```
➖ 매집 신호 없음

모든 신호 강도가 0입니다:
• Tight Range:    0.0
• OBV Divergence: 0.0
• Accum Bar:      0.0
• Volume Dryout:  0.0
```

---

## 구현 계획

### Phase 1: 백엔드 - intensities 데이터 추가

**파일**: `backend/core/realtime_scanner.py`

`_periodic_watchlist_broadcast()` 및 `recalculate_all_scores()`에서 `intensities` 딕셔너리를 Watchlist 항목에 추가:

```python
result = self.strategy.calculate_watchlist_score_v2(ticker, data)
item["score_v2"] = result.get("score_v2")
item["intensities"] = result.get("intensities", {})
# intensities = {
#     "tight_range": 0.25,
#     "obv_divergence": 1.0,
#     "accumulation_bar": 0.0,
#     "volume_dryout": 0.0
# }
```

### Phase 2: 프론트엔드 - intensities 파싱

**파일**: `frontend/services/backend_client.py`

`WatchlistItem` dataclass에 `intensities` 필드 추가:

```python
@dataclass
class WatchlistItem:
    # ... 기존 필드 ...
    intensities: dict = field(default_factory=dict)
```

### Phase 3: 프론트엔드 - 툴팁 생성

**파일**: `frontend/gui/watchlist_model.py`

`_set_row_data()` 메서드에서 Score 셀의 툴팁 생성:

```python
def _build_score_tooltip(self, score_v2, intensities):
    if score_v2 == -1:
        return "🆕 신규/IPO 종목 - 일봉 데이터 부족 (5일 미만)"
    elif score_v2 == 0:
        lines = ["➖ 매집 신호 없음\n"]
        for k, v in intensities.items():
            lines.append(f"• {k}: {v:.2f}")
        return "\n".join(lines)
    elif score_v2 is None:
        return "⚠️ score_v2 계산 실패"
    else:
        lines = [f"📊 Score V2: {score_v2:.1f}\n"]
        for k, v in intensities.items():
            bar = "█" * int(v * 5) + "░" * (5 - int(v * 5))
            marker = " ⬅ 주요" if v >= 0.8 else ""
            lines.append(f"• {k}: {bar} {v:.2f}{marker}")
        return "\n".join(lines)
```

---

## 파일 수정 목록

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/realtime_scanner.py` | `intensities` 딕셔너리 추가 |
| `backend/strategies/seismograph.py` | `calculate_watchlist_score_v2` 반환값에 `intensities` 포함 확인 |
| `frontend/services/backend_client.py` | `WatchlistItem.intensities` 필드 추가 |
| `frontend/gui/watchlist_model.py` | `_build_score_tooltip()` 메서드 추가 |

---

## 검증 계획

1. GUI 실행 후 Watchlist에서 Score 컬럼에 마우스 오버
2. 숫자 점수 → 4가지 신호 강도 바 표시 확인
3. ➖ 이모지 → "매집 신호 없음" + 각 신호 0.0 확인
4. 🆕 이모지 → "데이터 부족" 메시지 확인

---

## 예상 소요 시간

- Phase 1 (백엔드): ~10분
- Phase 2 (프론트엔드 파싱): ~5분
- Phase 3 (툴팁 생성): ~15분
- 검증: ~5분

**총: ~35분**
