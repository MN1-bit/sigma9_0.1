# 09-101: TradingContext 클래스 생성

> **작성일**: 2026-01-13 | **예상**: 30분  
> **상위 문서**: [09-009_ticker_selection_event_bus.md](./09-009_ticker_selection_event_bus.md)

---

## 목표

Backend에 `TradingContext` 클래스 생성 (Source of Truth)

---

## 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `backend/core/trading_context.py` | **NEW** | ~80 |

---

## 구현 내용

```python
# backend/core/trading_context.py

from typing import Callable
from loguru import logger


class TradingContext:
    """
    트레이딩 세션의 공유 콘텍스트 (Source of Truth)
    
    📌 [09-009] 모든 Backend 서비스가 참조하는 "현재 활성 티커"
    📌 Frontend에서 WebSocket으로 변경 요청 수신
    📌 변경 시 구독자들에게 알림
    """
    
    def __init__(self):
        self._active_ticker: str | None = None
        self._previous_ticker: str | None = None
        self._subscribers: list[Callable[[str, str], None]] = []
        logger.debug("[TradingContext] Initialized")
    
    @property
    def active_ticker(self) -> str | None:
        """현재 활성 티커 (읽기 전용)"""
        return self._active_ticker
    
    @property
    def previous_ticker(self) -> str | None:
        """이전 활성 티커"""
        return self._previous_ticker
    
    def set_active_ticker(self, ticker: str, source: str = "unknown") -> bool:
        """
        활성 티커 변경 (유일한 진입점)
        
        Args:
            ticker: 새 티커 심볼
            source: 변경 출처 (watchlist, search, tier2, ...)
        
        Returns:
            bool: 변경되었으면 True, 동일 티커면 False
        """
        if self._active_ticker == ticker:
            logger.debug(f"[TradingContext] Same ticker, skip: {ticker}")
            return False
        
        self._previous_ticker = self._active_ticker
        self._active_ticker = ticker
        
        logger.info(f"[TradingContext] Active ticker changed: {self._previous_ticker} → {ticker} (source: {source})")
        
        # 구독자들에게 알림
        for callback in self._subscribers:
            try:
                callback(ticker, source)
            except Exception as e:
                logger.error(f"[TradingContext] Subscriber error: {e}")
        
        return True
    
    def subscribe(self, callback: Callable[[str, str], None]) -> None:
        """
        티커 변경 구독
        
        Args:
            callback: (ticker, source) -> None
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
            logger.debug(f"[TradingContext] Subscriber added: {callback.__name__ if hasattr(callback, '__name__') else callback}")
    
    def unsubscribe(self, callback: Callable[[str, str], None]) -> None:
        """구독 해제"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
```

---

## 검증

- [ ] 파일 생성 확인
- [ ] `ruff check backend/core/trading_context.py` 통과
- [ ] 단위 테스트 (선택): `set_active_ticker`, `subscribe` 동작 확인

---

## 다음 단계

→ [09-102: DI Container 등록](./09-102_di_container_registration.md)
