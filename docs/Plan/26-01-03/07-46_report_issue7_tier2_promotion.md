# Issue 7 수정 완료 리포트: Hot Zone (Tier 2) 승격 로직

**완료일시**: 2026-01-03 07:45:00 (KST)

---

## 문제 설명

Tier 1 Watchlist에서 Tier 2 Hot Zone으로 종목이 승격되지 않았습니다.

---

## 원인 분석

### 근본 원인
1. **Ignition Score 계산 공식이 너무 엄격함**
   - 기존: `change_pct × 10` → **+7% 상승해야 70점**
   - 일반적인 종목은 하루에 7% 이상 상승하기 어려움

2. **Watchlist 파일 부재**
   - 서버 시작 시 Watchlist가 없으면 IgnitionMonitor가 시작되지 않음

---

## 해결 방안

### 1. Ignition Score 계산 로직 개선 (v3)

**파일**: `backend/core/ignition_monitor.py`

#### 기존 공식 (v2)
```python
# +7% = 70점 (너무 높음)
new_score = change_pct * 10
```

#### 새 공식 (v3)
```python
# base_score + stage_bonus + volume_bonus

# 1. Base Score: 변동률 × 14
# +3% = 42, +4% = 56, +5% = 70, +7% = 98
base_score = max(0, change_pct * 14)

# 2. Stage Bonus: Watchlist Stage에 따른 추가 점수
# Stage 4: +20, Stage 3: +10, Stage 1-2: 0
stage_bonus = 20 if stage_number >= 4 else (10 if stage_number >= 3 else 0)

# 3. Volume Bonus: 거래량 배수에 따른 추가 점수
# 3배 이상: +15, 2배 이상: +10, 1.5배 이상: +5
volume_bonus = ...

new_score = min(100, base_score + stage_bonus + volume_bonus)
```

#### 변경 효과
| 변동률 | Stage 4 | Stage 3 | Stage 1-2 |
|--------|---------|---------|-----------|
| +3% | 62점 | 52점 | 42점 |
| +4% | 76점 | 66점 | 56점 |
| +5% | 90점 | 80점 | 70점 |
| +7% | 100점 | 100점 | 98점 |

### 2. 서버 시작 시 Auto-Scanner 추가

**파일**: `backend/server.py`

```python
# Watchlist가 없으면 Scanner 자동 실행
if not watchlist:
    logger.info("📡 No watchlist found, running auto-scanner...")
    scanner = Scanner(app_state.db)
    strategy = SeismographStrategy()
    results = await scanner.scan_with_strategy(strategy, limit=30)
    if results:
        save_watchlist(results)
        watchlist = results
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/ignition_monitor.py` | Ignition Score v3 공식 적용 |
| `backend/server.py` | Auto-Scanner 추가 |

---

## 변경된 임계값

| 항목 | 기존 | 변경 |
|------|------|------|
| 70점 달성 조건 | +7% 상승 | +5% 상승 (Stage 3 이상) |
| 브로드캐스트 임계값 | 70점 이상 | 50점 이상 |
| Stage 4 보너스 | 없음 | +20점 |
| Stage 3 보너스 | 없음 | +10점 |
| 거래량 3배 보너스 | +20% (곱) | +15점 (합) |

---

## 동작 확인

서버 로그에서 Ignition Score 계산 확인:
```
⚡ AAPL: chg=3.5% base=49 stage_bonus=20 vol_bonus=0 → 69
⚡ TSLA: chg=5.0% base=70 stage_bonus=10 vol_bonus=10 → 90
```

---

## 상태

✅ **완료**
