# ============================================================================
# Ticker Info Model - 티커 종합 정보 데이터 모델
# ============================================================================
# [15-001] Ticker Info Viewer 구현
#
# 역할:
#   - TickerInfo dataclass: 13개 카테고리 티커 정보 통합
#   - SEC Filing 유형 한글 매핑
#
# 원본: scripts/demos/ticker_info_demo.py에서 이동
# ============================================================================

from dataclasses import dataclass, field
from typing import Any

# SEC 공시 유형 한글 매핑
SEC_FILING_TYPES: dict[str, str] = {
    # 정기 보고서
    "10-K": "연간 실적 보고서",
    "10-K/A": "연간 실적 보고서 (수정)",
    "10-Q": "분기 실적 보고서",
    "10-Q/A": "분기 실적 보고서 (수정)",
    "8-K": "주요 사항 공시",
    "8-K/A": "주요 사항 공시 (수정)",
    # 등록/상장
    "S-1": "IPO 등록 신청서",
    "S-1/A": "IPO 등록 신청서 (수정)",
    "S-3": "간이 등록 신청서 (희석 가능)",
    "S-3/A": "간이 등록 신청서 (수정)",
    "S-4": "합병/인수 등록 신청서",
    "S-8": "직원 주식보상 등록",
    "F-1": "외국기업 IPO 등록",
    "F-3": "외국기업 간이 등록",
    # 위임장/의결권
    "DEF 14A": "주주총회 위임장",
    "DEFA14A": "주주총회 위임장 (추가)",
    "PRE 14A": "위임장 예비 신고",
    "PROXY": "위임장 관련",
    # 내부자 거래
    "3": "내부자 최초 보유 신고",
    "4": "내부자 거래 신고",
    "5": "내부자 연간 보유 변경",
    "SC 13D": "5% 이상 대량 보유 (능동적)",
    "SC 13D/A": "5% 이상 대량 보유 (수정)",
    "SC 13G": "5% 이상 대량 보유 (수동적)",
    "SC 13G/A": "5% 이상 대량 보유 (수정)",
    # 기타
    "6-K": "외국기업 수시 보고",
    "20-F": "외국기업 연간 보고서",
    "NT 10-K": "연간 보고 지연 통보",
    "NT 10-Q": "분기 보고 지연 통보",
    "424B5": "증권 발행 가격 확정",
    "EFFECT": "등록 효력 발생",
    "SC TO-I": "공개 매수 의향서",
    "SC TO-C": "공개 매수 관련 통신",
    "13F-HR": "기관 투자자 보유 보고",
    "UPLOAD": "기타 업로드",
}


def get_filing_description(filing_type: str) -> str:
    """
    SEC 공시 유형에 대한 한글 설명 반환.

    Args:
        filing_type: SEC 공시 유형 코드 (예: "10-K", "8-K")

    Returns:
        한글 설명 문자열. 매칭되지 않으면 빈 문자열.
    """
    # 정확한 매칭 먼저
    if filing_type in SEC_FILING_TYPES:
        return SEC_FILING_TYPES[filing_type]
    # 부분 매칭 시도
    for key, desc in SEC_FILING_TYPES.items():
        if key in filing_type or filing_type.startswith(key.split("/")[0]):
            return desc
    return ""


@dataclass
class TickerInfo:
    """
    종합 티커 정보 데이터클래스.

    13개 카테고리의 티커 정보를 통합하여 관리합니다.
    각 카테고리는 API 응답을 그대로 저장하며,
    UI에서 필요한 형태로 변환하여 사용합니다.

    Attributes:
        ticker: 종목 심볼 (예: "AAPL")
        profile: 기본 정보 (이름, 시가총액, 직원수 등)
        float_data: 유동성 데이터 (Free Float, Float %)
        financials: 재무제표 리스트 (최근 4분기)
        dividends: 배당 이력 리스트
        splits: 주식 분할 이력 리스트
        ipo: IPO 정보
        ticker_events: 티커 이벤트 (이름 변경, 상장폐지 등)
        filings: SEC 공시 리스트
        news: 뉴스 리스트
        related_companies: 관련 기업 리스트
        snapshot: 현재가 스냅샷 (실시간)
        short_interest: 공매도 잔고 리스트
        short_volume: 공매도 거래량 리스트
    """

    ticker: str

    # 1. 기본 정보
    profile: dict[str, Any] = field(default_factory=dict)

    # 2. 유동성
    float_data: dict[str, Any] = field(default_factory=dict)

    # 3. 재무제표
    financials: list[dict[str, Any]] = field(default_factory=list)

    # 4. 기업 행동
    dividends: list[dict[str, Any]] = field(default_factory=list)
    splits: list[dict[str, Any]] = field(default_factory=list)
    ipo: dict[str, Any] = field(default_factory=dict)
    ticker_events: list[dict[str, Any]] = field(default_factory=list)

    # 5. SEC 공시
    filings: list[dict[str, Any]] = field(default_factory=list)

    # 6. 뉴스
    news: list[dict[str, Any]] = field(default_factory=list)

    # 7. 관련 기업
    related_companies: list[dict[str, Any]] = field(default_factory=list)

    # 8. 스냅샷 (실시간)
    snapshot: dict[str, Any] = field(default_factory=dict)

    # 9. Short Data
    short_interest: list[dict[str, Any]] = field(default_factory=list)
    short_volume: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """UI 표시용 딕셔너리로 변환."""
        return {
            "ticker": self.ticker,
            "profile": self._format_profile(),
            "float": self.float_data,
            "financials": self.financials[:3],
            "dividends": self.dividends[:5],
            "splits": self.splits[:5],
            "filings": self.filings[:5],
            "news": self.news[:3],
            "related_companies": self.related_companies[:10],
            "snapshot": self.snapshot,
            "short_interest": self.short_interest[:5],
            "short_volume": self.short_volume[:5],
            "ipo": self.ipo,
            "ticker_events": self.ticker_events[:5],
        }

    def _format_profile(self) -> dict[str, Any]:
        """프로필 데이터를 간소화된 형태로 변환."""
        if not self.profile:
            return {}
        return {
            "name": self.profile.get("name"),
            "description": (self.profile.get("description", "") or "")[:200],
            "market_cap": self.profile.get("market_cap"),
            "employees": self.profile.get("total_employees"),
            "sic_description": self.profile.get("sic_description"),
            "homepage": self.profile.get("homepage_url"),
            "list_date": self.profile.get("list_date"),
            "shares_outstanding": self.profile.get("share_class_shares_outstanding"),
            "primary_exchange": self.profile.get("primary_exchange"),
            "cik": self.profile.get("cik"),
        }
