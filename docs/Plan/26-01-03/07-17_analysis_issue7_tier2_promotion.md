# Issue 7 분석: Hot Zone (Tier 2) 승격 실패

**작성일시**: 2026-01-03 07:14:24 (KST)  
**상태**: 📋 분석 완료 (구현 대기)

---

## 문제 설명

Tier 1 Watchlist에서 Tier 2 Hot Zone으로 종목이 승격되지 않습니다.

---

## 아키텍처 분석

### Tier 2 승격 조건
Tier 2 승격은 **Ignition Score ≥ 70**일 때 발생합니다.

### 데이터 흐름
```
[Backend] IgnitionMonitor
    ↓ (1초 폴링)
Polygon API로 현재가 조회
    ↓
Ignition Score 계산 (변동률 기반)
    ↓ (score ≥ 70 또는 변화 ≥ 5)
WebSocket broadcast_ignition()
    ↓
IGNITION:{"ticker":"AAPL","score":75,...}
    ↓
[Frontend] WsAdapter.ignition_updated signal
    ↓
BackendClient.ignition_updated signal
    ↓
Dashboard._on_ignition_update()
    ↓
score ≥ 70 && passed_filter?
    ↓ Yes
Dashboard._promote_to_tier2(ticker, score)
```

---

## 잠재적 문제점

### 1. ⚠️ IgnitionMonitor가 시작되지 않음 (해결됨 - Issue 5)
- 서버 시작 시 `ignition_monitor.start(watchlist)` 호출 추가됨
- **하지만**: Watchlist가 없으면 시작되지 않음

### 2. ⚠️ Watchlist 파일이 비어있음
- `load_watchlist()`가 `data/watchlist/watchlist_current.json`을 읽음
- 파일이 없거나 비어있으면 IgnitionMonitor가 시작되지 않음
- **확인 필요**: 해당 파일 존재 여부

### 3. ⚠️ Ignition Score 계산 로직
현재 Ignition Score 계산 방식 (`ignition_monitor.py` Line 210-224):
```python
# 변동률 → Ignition Score 변환
# +3% = 30점, +5% = 50점, +7% = 70점, +10% = 100점
new_score = min(100, max(0, change_pct * 10))
```

**문제**: 이 공식에서 **+7% 이상 상승**해야 70점이 됩니다.
- 일반적인 종목은 하루에 7% 이상 상승하기 어려움
- 사전 장(Pre-market)이나 장 중 시작 직후가 아니면 거의 달성 불가

### 4. ⚠️ WebSocket 연결 문제
- Frontend가 WebSocket에 연결되지 않으면 IGNITION 메시지 수신 불가
- 연결 상태 확인 필요

### 5. ⚠️ last_close 값 부재
- `last_close` 값이 없으면 변동률 계산 불가 → score = 0
- Watchlist 항목에 `last_close` 필드가 있어야 함

---

## 권장 해결 방안

### 방안 1: Ignition Score 계산 로직 개선
**현재**: 단순 변동률 × 10
```python
new_score = change_pct * 10
```

**개선안**: SeismographStrategy의 실제 Ignition 로직 사용
```python
# 전략 객체에 이미 구현된 calculate_ignition_score() 활용
new_score = self.strategy.calculate_ignition_score(
    ticker=ticker,
    price=price,
    volume=volume,
    timestamp=datetime.now()
)
```

### 방안 2: 테스트용 임시 Ignition Score 조정
개발/테스트 시에는 임계값을 낮춤:
```python
# +3% = 70점 (테스트용)
new_score = min(100, max(0, change_pct * 23.33))
```

### 방안 3: Watchlist 파일 초기화 보장
- 서버 시작 시 Scanner 자동 실행
- Watchlist 파일이 없으면 기본 종목 리스트로 생성

### 방안 4: WebSocket 연결 디버깅
- Dashboard 시작 시 WebSocket 연결 상태 로그 확인
- `ignition_updated` 시그널 수신 확인

---

## 디버깅 체크리스트

1. **Watchlist 파일 확인**
   ```
   data/watchlist/watchlist_current.json
   ```

2. **서버 로그 확인**
   ```
   ✅ IgnitionMonitor started with X tickers
   ⚡ IgnitionMonitor: 폴링 루프 시작
   ```

3. **Frontend 로그 확인**
   ```
   📡 WebSocket connected
   [IGNITION] 🔥 AAPL Score=XX
   ```

4. **Ignition Score 계산 확인**
   - 현재가와 last_close 비교
   - 7% 이상 상승 종목 존재 여부

---

## 수정해야 할 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/ignition_monitor.py` | Ignition Score 계산 로직 개선 |
| `backend/server.py` | Watchlist 없을 시 Scanner 자동 실행 |
| `frontend/gui/dashboard.py` | WebSocket 연결 상태 디버깅 로그 추가 |

---

## 구현 우선순위

1. Watchlist 파일 존재 여부 확인
2. IgnitionMonitor 로그 확인
3. Ignition Score 계산 로직 개선
4. 테스트

---

## 다음 단계

사용자 승인 후 구현 진행
