# ============================================================================
# Audit Logger - 의사결정 감사 로거
# ============================================================================
# 📌 이 파일의 역할:
#   - 트레이딩 의사결정의 완전한 재현성(Reproducibility) 보장
#   - 입력 데이터 스냅샷, 신호, 결정, 파라미터 버전 기록
#   - 일별 JSONL 파일로 저장
#
# 📖 사용 예시:
#   >>> from backend.core.audit_logger import AuditLogger
#   >>> logger = AuditLogger()
#   >>> logger.log_decision(
#   ...     ticker="AAPL",
#   ...     decision="BUY",
#   ...     context={"ignition_score": 85, "price": 150.25}
#   ... )
#
# 📖 리팩터링 [08-001] Phase 5:
#   - 신규 파일 생성
# ============================================================================

"""
Audit Logger

트레이딩 의사결정을 JSONL 형식으로 기록하여 완전한 재현성을 보장합니다.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class AuditLogger:
    """
    의사결정 감사 로거

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    트레이딩 시스템이 왜 그 결정을 내렸는지 기록합니다.
    마치 비행기의 "블랙박스"처럼, 나중에 문제가 생기면
    어떤 정보로 어떤 결정을 내렸는지 완벽하게 재현할 수 있습니다.

    기록 내용:
      - 언제: event_time (거래소 시간)
      - 무엇을: ticker + decision (매수/매도/홀드)
      - 왜: signals, scores, context
      - 어떤 설정으로: strategy_version, config_hash

    Attributes:
        log_dir: 로그 저장 디렉토리 (기본: data/audit)

    Example:
        >>> logger = AuditLogger()
        >>> logger.log_decision(
        ...     ticker="AAPL",
        ...     decision="BUY",
        ...     context={
        ...         "ignition_score": 85,
        ...         "price": 150.25,
        ...         "volume": 10000
        ...     }
        ... )
    """

    def __init__(
        self,
        log_dir: str = "data/audit",
        strategy_version: str = "2.0.0",
    ):
        """
        AuditLogger 초기화

        Args:
            log_dir: 로그 저장 디렉토리
            strategy_version: 전략 버전 (로그에 기록)
        """
        self.log_dir = Path(log_dir)
        self.strategy_version = strategy_version
        self._current_date: Optional[str] = None
        self._file_handle = None

        # 디렉토리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📝 AuditLogger initialized: {self.log_dir}")

    def _get_log_file_path(self, date_str: str) -> Path:
        """
        일별 로그 파일 경로 반환

        Args:
            date_str: YYYY-MM-DD 형식 날짜

        Returns:
            Path: 로그 파일 경로 (예: data/audit/2026-01-08/decisions.jsonl)
        """
        date_dir = self.log_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir / "decisions.jsonl"

    def _ensure_file_handle(self) -> None:
        """
        현재 날짜의 로그 파일 핸들 확보

        날짜가 바뀌면 새 파일을 생성합니다.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        if self._current_date != today:
            # 기존 파일 닫기
            if self._file_handle:
                self._file_handle.close()

            # 새 파일 열기
            log_path = self._get_log_file_path(today)
            self._file_handle = open(log_path, "a", encoding="utf-8")
            self._current_date = today
            logger.debug(f"📝 Opened audit log: {log_path}")

    def log_decision(
        self,
        ticker: str,
        decision: str,
        context: Dict[str, Any],
        event_time: Optional[datetime] = None,
        signals: Optional[Dict[str, float]] = None,
        config_snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        의사결정 기록

        ═══════════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════════
        "이 종목에 대해 이런 결정을 내렸어요" 라고 기록합니다.
        나중에 왜 그랬는지 정확히 알 수 있도록 모든 정보를 저장해요.

        Args:
            ticker: 종목 코드 (예: "AAPL")
            decision: 결정 유형 ("BUY", "SELL", "HOLD", "FILTER_REJECTED")
            context: 결정 맥락 (가격, 거래량, 점수 등)
            event_time: 이벤트 발생 시간 (None이면 현재 시간)
            signals: 시그널 강도 (예: {"tight_range": 0.8, "obv": 0.6})
            config_snapshot: 파라미터 스냅샷

        Example:
            >>> logger.log_decision(
            ...     ticker="NVDA",
            ...     decision="BUY",
            ...     context={"ignition_score": 92},
            ...     signals={"volume_burst": 0.95}
            ... )
        """
        self._ensure_file_handle()

        now = datetime.now()

        record = {
            # 시간 정보
            "event_time": (event_time or now).isoformat(),
            "log_time": now.isoformat(),
            # 의사결정 정보
            "ticker": ticker,
            "decision": decision,
            "context": self._serialize_context(context),
            # 시그널 정보
            "signals": signals or {},
            # 버전 정보
            "strategy_version": self.strategy_version,
            "config_snapshot": config_snapshot,
        }

        # JSONL 형식으로 기록
        try:
            line = json.dumps(record, ensure_ascii=False, default=str)
            self._file_handle.write(line + "\n")
            self._file_handle.flush()  # 즉시 디스크에 쓰기
        except Exception as e:
            logger.error(f"❌ Audit log write failed: {e}")

    def _serialize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Context 객체를 JSON 직렬화 가능 형태로 변환

        numpy, datetime 등 특수 타입 처리
        """
        serialized = {}
        for key, value in context.items():
            try:
                # numpy 타입 처리
                if hasattr(value, "item"):
                    serialized[key] = value.item()
                elif isinstance(value, datetime):
                    serialized[key] = value.isoformat()
                else:
                    serialized[key] = value
            except Exception:
                serialized[key] = str(value)
        return serialized

    def log_ignition(
        self,
        ticker: str,
        score: float,
        passed_filter: bool,
        filter_reason: str = "",
        event_time: Optional[datetime] = None,
    ) -> None:
        """
        Ignition Score 이벤트 기록 (Phase 2 편의 메서드)

        Args:
            ticker: 종목 코드
            score: Ignition Score (0~100)
            passed_filter: Anti-Trap 필터 통과 여부
            filter_reason: 필터 미통과 시 사유
            event_time: 이벤트 발생 시간
        """
        decision = "IGNITION_TRIGGERED" if passed_filter else "FILTER_REJECTED"

        self.log_decision(
            ticker=ticker,
            decision=decision,
            context={
                "ignition_score": round(score, 1),
                "passed_filter": passed_filter,
                "filter_reason": filter_reason,
            },
            event_time=event_time,
        )

    def close(self) -> None:
        """로그 파일 종료"""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
            logger.info("📝 AuditLogger closed")

    def __enter__(self):
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.close()
        return False


__all__ = ["AuditLogger"]
