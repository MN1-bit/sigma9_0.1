# A01-01: Watchlist Refresh Strategy Enhancement

## 개요

Watchlist 및 Chart의 실시간 업데이트 전략 재설계. 현재 stale price 문제를 해결하고, Time-of-Day Normalization을 통한 장중 동시간대 비교 기능 도입.

---

## Phase 1: Stale Price 문제 해결 (Immediate)

### 문제
- Day Gainer로 편입된 종목이 Top 21에서 탈락하면 price/change_pct 업데이트 중단
- 어제 +800% 기록이 오늘도 그대로 표시

### 해결책: 1분마다 Snapshot 폴링

```
Snapshot API 호출 (1분마다)
→ 전체 Watchlist 종목 price/change_pct 갱신
→ 오늘 기준으로 change_pct 재계산
```

### 리소스 예상
- 500개 종목: 2 API 호출/분
- 1000개 종목: 4 API 호출/분
- 유료 플랜 (100 호출/분) 내 여유

---

## Phase 2: Tier 구조 도입

```
┌─────────────────────────────────────────────────────────────────────┐
│  Tier 0.5: Archive Pool (최대 500-1000개)                           │
│  - Snapshot 폴링: 1분마다                                           │
│  - score_v3: 장 마감 후 1회                                         │
│  - UI 표시: ❌                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 1: Watchlist (상위 100개)                                     │
│  - 표시 기준: score_v3 × 0.5 + today_change_pct × 0.5              │
│  - UI 표시: ✅                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 2: Hot Zone (상위 10개)                                       │
│  - T채널 틱 구독                                                     │
│  - ignition 실시간 계산                                              │
│  - UI 표시: ✅                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 자동 승격/강등
- 1분마다 정렬 기준 재계산
- score_v3 + change_pct 조합으로 상위 100개 선정
- Multi-day runner 포착: 종목은 Archive에 영구 보관

---

## Phase 3: Time-of-Day Normalization (Future)

### 문제
- 장 초반 거래량이 적어 전일 대비가 무의미
- 9:35 AM 오늘 50K vs 어제 전일 5M = 1% (의미 없음)

### 해결책: 동시간대 비교

```python
# 올바른 비교
today_volume_at_935 = 50,000
yesterday_volume_at_935 = 40,000
relative_volume = 50,000 / 40,000 = 125%  # 의미 있음
```

### 필요 데이터
- 분봉 (1min bar) 또는 시간봉 데이터
- 과거 N일간 시간대별 누적 거래량 프로파일
- Intraday Volume Profile 구축

### Synthetic Today Bar + Time Normalization

```python
def get_score_v3_live(ticker: str) -> float:
    # 과거 19일 일봉
    historical_bars = db.get_daily_bars(ticker, days=19)
    
    # 오늘 Synthetic Bar (실시간)
    today_bar = {
        "open": today_open,
        "high": current_high,
        "low": current_low,
        "close": current_price,
        "volume": normalize_volume_by_time(today_volume, current_time)
    }
    
    return calculate_score_v3(historical_bars + [today_bar])
```

### 구현 복잡도
- 분봉 데이터 저장 인프라 필요
- Intraday Profile 구축 로직
- score_v3 하이브리드 재설계

---

## 구현 우선순위

| Phase | 내용 | 복잡도 | 우선순위 |
|-------|-----|--------|---------|
| 1 | Snapshot 1분 폴링 + Stale 해결 | 낮음 | **즉시** |
| 2 | Tier 구조 + 자동 승격/강등 | 중간 | 다음 |
| 3 | Time-of-Day Normalization | 높음 | 차후 |

---

## 관련 문서

- [02-002_tier1_realtime_change_update.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/bugfix/02-002_tier1_realtime_change_update.md) - 기존 A채널 구독 계획
- [watchlist_realtime_sync.md](file:///C:/Users/USER/.gemini/antigravity/knowledge/sigma9_core_engine/artifacts/implementation/watchlist_realtime_sync.md) - Dual-Path Sync 아키텍처
