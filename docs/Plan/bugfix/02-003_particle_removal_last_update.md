# 02-003: Watchlist 파티클 효과 제거 + Last Update 타임스탬프

## 문제 설명
Watchlist가 업데이트될 때마다 파티클 효과가 발생하여 사용자에게 불편함.
대신 마지막 업데이트 시간을 라벨로 표시해달라는 요청.

## 근본 원인
`dashboard.py`의 `_update_watchlist_panel()` 마지막 줄에서
매 업데이트마다 `particle_system.order_created()` 호출.

```python
# 현재 코드 (라인 1394)
self.particle_system.order_created()
```

---

## 제안된 해결책

### Phase 1: 파티클 효과 제거
- `_update_watchlist_panel()`에서 `particle_system.order_created()` 호출 제거

### Phase 2: Last Update 라벨 추가
- Watchlist 라벨을 "📋 Watchlist (Last update: yy-mm-dd hh:mm:ss)" 형식으로 변경
- 업데이트 시마다 라벨 텍스트 갱신

---

## 수정 파일

### [MODIFY] [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py)

**수정 1**: `_create_left_panel()` (라인 629 부근)
- Watchlist 라벨을 인스턴스 변수로 저장

```diff
-        tier1_label = QLabel("📋 Watchlist")
+        self.tier1_label = QLabel("📋 Watchlist")
         ...
-        layout.addWidget(tier1_label)
+        layout.addWidget(self.tier1_label)
```

**수정 2**: `_update_watchlist_panel()` (라인 1393~1394)
- 파티클 호출 제거
- Last Update 라벨 갱신

```diff
         self.log(f"[INFO] Watchlist updated: {len(items)} stocks")
-        self.particle_system.order_created()
+        # [Issue 01-005] Last Update 타임스탬프 표시
+        from datetime import datetime
+        now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
+        self.tier1_label.setText(f"📋 Watchlist (Last update: {now})")
```

---

## 검증 계획

### 수동 테스트
1. 애플리케이션 실행: `python -m frontend.main`
2. 백엔드 연결 대기
3. Watchlist가 업데이트될 때:
   - ✅ 파티클 효과가 발생하지 않음
   - ✅ "📋 Watchlist (Last update: 26-01-06 10:30:45)" 형식으로 라벨 변경됨
4. 1분마다 갱신 시 타임스탬프가 업데이트되는지 확인

> [!TIP]
> 파티클 효과는 주문 생성/체결 같은 중요한 이벤트에만 사용하도록 유지합니다.
