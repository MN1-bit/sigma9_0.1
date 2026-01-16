# 09-102: DI Container 등록

> **작성일**: 2026-01-13 | **예상**: 15분  
> **상위 문서**: [09-009_ticker_selection_event_bus.md](./09-009_ticker_selection_event_bus.md)

---

## 목표

`TradingContext`를 DI Container에 Singleton으로 등록

---

## 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `backend/container.py` | MODIFY | +15 |

---

## 구현 내용

```python
# backend/container.py 에 추가

# ───────────────────────────────────────────────────────────────────────
# [09-009] TradingContext: 활성 티커 컨텍스트 (Singleton)
# ───────────────────────────────────────────────────────────────────────
@staticmethod
def _create_trading_context():
    """
    TradingContext 생성 팩토리
    
    📌 [09-009] Frontend ↔ Backend 활성 티커 상태 관리
    📌 모든 Backend 서비스가 공유하는 "현재 상태"
    """
    from backend.core.trading_context import TradingContext
    return TradingContext()

trading_context = providers.Singleton(_create_trading_context)
```

---

## 추가 위치

`Container` 클래스 내부, Core Layer 섹션 근처에 추가:

```python
class Container(containers.DeclarativeContainer):
    # ... 기존 코드 ...
    
    # ═══════════════════════════════════════════════════════════════════
    # Core Layer
    # ═══════════════════════════════════════════════════════════════════
    
    # 📌 NEW: TradingContext [09-009]
    @staticmethod
    def _create_trading_context():
        ...
    
    trading_context = providers.Singleton(_create_trading_context)
    
    # ... realtime_scanner, ignition_monitor 등 ...
```

---

## 검증

- [ ] `lint-imports` 통과
- [ ] `python -c "from backend.container import container; print(container.trading_context())"` 작동

---

## 다음 단계

→ [09-103: WebSocket 핸들러 추가](./09-103_websocket_handler.md)
