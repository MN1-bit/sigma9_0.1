"""
Massive API Ticker Information Demo
===================================
티커 입력 시 종합 기업 정보를 조회하는 데모 스크립트

카테고리:
1. 기본 정보 (Company Profile)
2. 유동성 (Float & Shares)
3. 재무제표 (Financials)
4. 기업 행동 (Corporate Actions: Dividends, Splits)
5. SEC 공시 (Filings)
6. 뉴스 (News)
7. 관련 기업 (Related Companies)
8. 스냅샷 (Current Price & Volume)
"""

import os
import json
import asyncio
from dataclasses import dataclass, field

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.massive.com"
API_KEY = os.getenv("MASSIVE_API_KEY")

# SEC 공시 유형 한글 매핑
SEC_FILING_TYPES = {
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
    """공시 유형 한글 설명 반환"""
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
    """종합 티커 정보"""
    ticker: str
    
    # 1. 기본 정보
    profile: dict = field(default_factory=dict)
    
    # 2. 유동성
    float_data: dict = field(default_factory=dict)
    
    # 3. 재무제표
    financials: list = field(default_factory=list)
    
    # 4. 기업 행동
    dividends: list = field(default_factory=list)
    splits: list = field(default_factory=list)
    ipo: dict = field(default_factory=dict)
    ticker_events: list = field(default_factory=list)
    
    # 5. SEC 공시
    filings: list = field(default_factory=list)
    
    # 6. 뉴스
    news: list = field(default_factory=list)
    
    # 7. 관련 기업
    related_companies: list = field(default_factory=list)
    
    # 8. 스냅샷
    snapshot: dict = field(default_factory=dict)
    
    # 9. Short Data
    short_interest: list = field(default_factory=list)
    short_volume: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "profile": self._format_profile(),
            "float": self.float_data,
            "financials": self.financials[:3],  # 최근 3개
            "dividends": self.dividends[:5],
            "splits": self.splits[:5],
            "filings": self.filings[:5],
            "news": self.news[:3],
            "related_companies": self.related_companies[:10],
            "snapshot": self.snapshot,
        }
    
    def _format_profile(self) -> dict:
        if not self.profile:
            return {}
        return {
            "name": self.profile.get("name"),
            "description": self.profile.get("description", "")[:200] + "...",
            "market_cap": self.profile.get("market_cap"),
            "employees": self.profile.get("total_employees"),
            "sic_description": self.profile.get("sic_description"),
            "homepage": self.profile.get("homepage_url"),
            "list_date": self.profile.get("list_date"),
            "shares_outstanding": self.profile.get("share_class_shares_outstanding"),
        }


class MassiveTickerClient:
    """Massive API 티커 정보 클라이언트"""
    
    def __init__(self, api_key: str = API_KEY):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def get_ticker_info(self, ticker: str) -> TickerInfo:
        """티커 종합 정보 조회"""
        info = TickerInfo(ticker=ticker)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 병렬 호출
            tasks = [
                self._get_profile(client, ticker),
                self._get_float(client, ticker),
                self._get_financials(client, ticker),
                self._get_dividends(client, ticker),
                self._get_splits(client, ticker),
                self._get_filings(client, ticker),
                self._get_news(client, ticker),
                self._get_related(client, ticker),
                self._get_snapshot(client, ticker),
                self._get_short_interest(client, ticker),
                self._get_short_volume(client, ticker),
                self._get_ipo(client, ticker),
                self._get_ticker_events(client, ticker),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 할당
            info.profile = results[0] if not isinstance(results[0], Exception) else {}
            info.float_data = results[1] if not isinstance(results[1], Exception) else {}
            info.financials = results[2] if not isinstance(results[2], Exception) else []
            info.dividends = results[3] if not isinstance(results[3], Exception) else []
            info.splits = results[4] if not isinstance(results[4], Exception) else []
            info.filings = results[5] if not isinstance(results[5], Exception) else []
            info.news = results[6] if not isinstance(results[6], Exception) else []
            info.related_companies = results[7] if not isinstance(results[7], Exception) else []
            info.snapshot = results[8] if not isinstance(results[8], Exception) else {}
            info.short_interest = results[9] if not isinstance(results[9], Exception) else []
            info.short_volume = results[10] if not isinstance(results[10], Exception) else []
            info.ipo = results[11] if not isinstance(results[11], Exception) else {}
            info.ticker_events = results[12] if not isinstance(results[12], Exception) else []
        
        return info
    
    async def _get_profile(self, client: httpx.AsyncClient, ticker: str) -> dict:
        """1. 기본 정보 - Ticker Details"""
        url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
        resp = await client.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get("results", {})
        return {}
    
    async def _get_float(self, client: httpx.AsyncClient, ticker: str) -> dict:
        """2. 유동성 - Free Float"""
        url = f"{BASE_URL}/stocks/vX/float"
        params = {"ticker": ticker, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            return results[0] if results else {}
        return {}
    
    async def _get_financials(self, client: httpx.AsyncClient, ticker: str) -> list:
        """3. 재무제표 - Stock Financials"""
        url = f"{BASE_URL}/vX/reference/financials"
        params = {"ticker": ticker, "limit": 4, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
    
    async def _get_dividends(self, client: httpx.AsyncClient, ticker: str) -> list:
        """4-1. 기업 행동 - Dividends"""
        url = f"{BASE_URL}/v3/reference/dividends"
        params = {"ticker": ticker, "limit": 5, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
    
    async def _get_splits(self, client: httpx.AsyncClient, ticker: str) -> list:
        """4-2. 기업 행동 - Splits"""
        url = f"{BASE_URL}/v3/reference/splits"
        params = {"ticker": ticker, "limit": 5, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
    
    async def _get_filings(self, client: httpx.AsyncClient, ticker: str) -> list:
        """5. SEC 공시 - Filings"""
        # 먼저 CIK 가져오기 (profile에서)
        profile = await self._get_profile(client, ticker)
        cik = profile.get("cik")
        if not cik:
            return []
        
        url = f"{BASE_URL}/v1/reference/sec/filings"
        params = {"cik": cik, "limit": 5, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
    
    async def _get_news(self, client: httpx.AsyncClient, ticker: str) -> list:
        """6. 뉴스"""
        url = f"{BASE_URL}/v2/reference/news"
        params = {"ticker": ticker, "limit": 5, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            # 간소화
            return [
                {
                    "title": n.get("title"),
                    "published": n.get("published_utc"),
                    "source": n.get("publisher", {}).get("name"),
                    "url": n.get("article_url"),
                }
                for n in results
            ]
        return []
    
    async def _get_related(self, client: httpx.AsyncClient, ticker: str) -> list:
        """7. 관련 기업"""
        url = f"{BASE_URL}/v1/related-companies/{ticker}"
        resp = await client.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
    
    async def _get_snapshot(self, client: httpx.AsyncClient, ticker: str) -> dict:
        """8. 스냅샷 - 현재가"""
        url = f"{BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        resp = await client.get(url, headers=self.headers)
        if resp.status_code == 200:
            ticker_data = resp.json().get("ticker", {})
            return {
                "price": ticker_data.get("day", {}).get("c"),  # close
                "change_pct": ticker_data.get("todaysChangePerc"),
                "volume": ticker_data.get("day", {}).get("v"),
                "prev_close": ticker_data.get("prevDay", {}).get("c"),
            }
        return {}
    
    async def _get_short_interest(self, client: httpx.AsyncClient, ticker: str) -> list:
        """9. Short Interest"""
        url = f"{BASE_URL}/vX/reference/short-interest/ticker/{ticker}"
        params = {"limit": 5, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
    
    async def _get_short_volume(self, client: httpx.AsyncClient, ticker: str) -> list:
        """10. Short Volume"""
        url = f"{BASE_URL}/vX/reference/short-volume/{ticker}"
        params = {"limit": 5, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
    
    async def _get_ipo(self, client: httpx.AsyncClient, ticker: str) -> dict:
        """11. IPO 정보"""
        url = f"{BASE_URL}/vX/reference/ipos"
        params = {"ticker": ticker, "limit": 1, "apiKey": self.api_key}
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            return results[0] if results else {}
        return {}
    
    async def _get_ticker_events(self, client: httpx.AsyncClient, ticker: str) -> list:
        """12. Ticker Events (이름 변경, 상장폐지 등)"""
        url = f"{BASE_URL}/vX/reference/tickers/{ticker}/events"
        resp = await client.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get("results", {}).get("events", [])
        return []


def print_ticker_info(info: TickerInfo):
    """티커 정보 출력"""
    print("\n" + "=" * 60)
    print(f"📊 {info.ticker} 종합 정보")
    print("=" * 60)
    
    # 1. 기본 정보
    if info.profile:
        print("\n🏢 기본 정보")
        print(f"   이름: {info.profile.get('name')}")
        print(f"   시가총액: ${info.profile.get('market_cap', 0):,.0f}")
        print(f"   직원수: {info.profile.get('total_employees', 'N/A'):,}")
        print(f"   업종: {info.profile.get('sic_description')}")
        print(f"   상장일: {info.profile.get('list_date')}")
    
    # 2. 유동성
    if info.float_data:
        print("\n💧 유동성 (Float)")
        print(f"   Free Float: {info.float_data.get('free_float', 0):,}")
        print(f"   Float %: {info.float_data.get('free_float_percent', 0):.1f}%")
        print(f"   기준일: {info.float_data.get('effective_date')}")
    
    # 3. 스냅샷
    if info.snapshot:
        print("\n📈 현재가")
        print(f"   가격: ${info.snapshot.get('price', 0):.2f}")
        print(f"   변동: {info.snapshot.get('change_pct', 0):.2f}%")
        print(f"   거래량: {info.snapshot.get('volume', 0):,}")
    
    # 4. 배당
    if info.dividends:
        print(f"\n💰 최근 배당 ({len(info.dividends)}건)")
        for d in info.dividends[:3]:
            print(f"   {d.get('ex_dividend_date')}: ${d.get('cash_amount', 0):.4f}")
    
    # 5. 분할
    if info.splits:
        print(f"\n✂️ 주식 분할 ({len(info.splits)}건)")
        for s in info.splits[:3]:
            print(f"   {s.get('execution_date')}: {s.get('split_from')}:{s.get('split_to')}")
    
    # 6. SEC 공시
    if info.filings:
        print(f"\n📄 최근 SEC 공시 ({len(info.filings)}건)")
        for f in info.filings[:3]:
            print(f"   {f.get('filing_date')}: {f.get('type')}")
    
    # 7. 뉴스
    if info.news:
        print(f"\n📰 최근 뉴스 ({len(info.news)}건)")
        for n in info.news[:3]:
            title = n.get("title", "")[:50]
            print(f"   - {title}...")
    
    # 8. 관련 기업
    if info.related_companies:
        tickers = [r.get("ticker") for r in info.related_companies[:10]]
        print("\n🔗 관련 기업")
        print(f"   {', '.join(tickers)}")
    
    print("\n" + "=" * 60)


async def main():
    """메인 함수"""
    import sys
    
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    
    print(f"조회 중: {ticker}...")
    
    client = MassiveTickerClient()
    info = await client.get_ticker_info(ticker.upper())
    
    # --output 옵션: 마크다운 파일로 저장
    if "--output" in sys.argv:
        output_file = f"scripts/demos/{ticker.upper()}_info.md"
        md = generate_markdown(info)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"저장 완료: {output_file}")
        return
    
    print_ticker_info(info)
    
    # JSON 출력 옵션
    if "--json" in sys.argv:
        print("\n[JSON Output]")
        print(json.dumps(info.to_dict(), indent=2, default=str))


def generate_markdown(info: TickerInfo) -> str:
    """마크다운 문서 생성"""
    # Profile 없음 처리
    if not info.profile:
        profile_section = "- 데이터 없음"
    else:
        p = info.profile
        # 주소 처리
        addr = p.get('address', {})
        address_str = f"{addr.get('address1', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('postal_code', '')}" if addr else "N/A"
        # 브랜딩 처리
        branding = p.get('branding', {})
        logo_url = branding.get('logo_url', 'N/A')
        icon_url = branding.get('icon_url', 'N/A')
        
        profile_section = f"""| 항목 | 값 |
|------|-----|
| 티커 | {p.get('ticker', 'N/A')} |
| 이름 | {p.get('name', 'N/A')} |
| Active | {'✅ 거래중' if p.get('active') else '❌ 상장폐지'} |
| 시가총액 | ${p.get('market_cap', 0):,.0f} |
| 직원수 | {p.get('total_employees', 'N/A'):,} |
| 업종 (SIC) | {p.get('sic_code', 'N/A')} - {p.get('sic_description', 'N/A')} |
| 시장 | {p.get('market', 'N/A')} |
| 거래소 | {p.get('primary_exchange', 'N/A')} |
| 통화 | {p.get('currency_name', 'N/A')} |
| 상장일 | {p.get('list_date', 'N/A')} |
| 상장폐지일 | {p.get('delisted_utc', 'N/A')} |
| CIK | {p.get('cik', 'N/A')} |
| Composite FIGI | {p.get('composite_figi', 'N/A')} |
| Share Class FIGI | {p.get('share_class_figi', 'N/A')} |
| 발행주식수 | {p.get('share_class_shares_outstanding', 0):,} |
| 가중 발행주식수 | {p.get('weighted_shares_outstanding', 0):,} |
| Round Lot | {p.get('round_lot', 'N/A')} |
| Ticker Root | {p.get('ticker_root', 'N/A')} |
| Ticker Suffix | {p.get('ticker_suffix', 'N/A')} |
| Type | {p.get('type', 'N/A')} |
| Locale | {p.get('locale', 'N/A')} |
| 전화번호 | {p.get('phone_number', 'N/A')} |
| 주소 | {address_str} |
| 홈페이지 | {p.get('homepage_url', 'N/A')} |
| 로고 | {logo_url} |
| 아이콘 | {icon_url} |

### 회사 설명
{p.get('description', 'N/A')[:500]}..."""

    # Float 없음 처리
    if not info.float_data:
        float_section = "- 데이터 없음"
    else:
        float_section = f"""| 항목 | 값 |
|------|-----|
| Free Float | {info.float_data.get('free_float', 0):,} |
| Float 비율 | {info.float_data.get('free_float_percent', 0):.1f}% |
| 기준일 | {info.float_data.get('effective_date', 'N/A')} |"""

    # Snapshot 없음 처리
    if not info.snapshot:
        snapshot_section = "- 데이터 없음"
    else:
        snapshot_section = f"""| 항목 | 값 |
|------|-----|
| 현재가 | ${info.snapshot.get('price', 0):.2f} |
| 변동률 | {info.snapshot.get('change_pct', 0):.2f}% |
| 거래량 | {info.snapshot.get('volume', 0):,.0f} |
| 전일 종가 | ${info.snapshot.get('prev_close', 0):.2f} |"""

    md = f"""# {info.ticker} 종합 정보

## 1. 기본 정보 (Profile)
{profile_section}

## 2. 유동성 (Float)
{float_section}

## 3. 현재가 (Snapshot)
{snapshot_section}

## 4. 재무제표 (Financials)
"""
    if info.financials:
        md += "| 기간 | 유형 | 매출 | 순이익 |\n|------|------|------|--------|\n"
        for f in info.financials[:4]:
            period = f.get('fiscal_period', 'N/A')
            year = f.get('fiscal_year', '')
            timeframe = f.get('timeframe', '')
            income = f.get('financials', {}).get('income_statement', {})
            revenues = income.get('revenues', {}).get('value', 0)
            net_income = income.get('net_income_loss', {}).get('value', 0)
            md += f"| {period} {year} | {timeframe} | ${revenues:,.0f} | ${net_income:,.0f} |\n"
    else:
        md += "- 데이터 없음\n"
    
    md += "\n## 5. 배당 (Dividends)\n"
    if info.dividends:
        md += "| 배당락일 | 금액 |\n|----------|------|\n"
        for d in info.dividends[:5]:
            md += f"| {d.get('ex_dividend_date')} | ${d.get('cash_amount', 0):.4f} |\n"
    else:
        md += "- 데이터 없음\n"
    
    md += "\n## 6. 주식 분할 (Splits)\n"
    if info.splits:
        md += "| 실행일 | 비율 |\n|--------|------|\n"
        for s in info.splits[:5]:
            md += f"| {s.get('execution_date')} | {s.get('split_from')}:{s.get('split_to')} |\n"
    else:
        md += "- 데이터 없음\n"
    
    md += "\n## 7. SEC 공시 (Filings)\n"
    if info.filings:
        md += "| 공시일 | 유형 | 설명 |\n|--------|------|------|\n"
        for f in info.filings[:5]:
            f_type = f.get('type', '')
            desc = get_filing_description(f_type)
            md += f"| {f.get('filing_date')} | {f_type} | {desc} |\n"
    else:
        md += "- 데이터 없음\n"
    
    md += "\n## 8. 최근 뉴스\n"
    if info.news:
        for n in info.news[:5]:
            title = n.get('title', '')[:80]
            md += f"- {title}...\n"
    else:
        md += "- 데이터 없음\n"
    
    md += "\n## 9. 관련 기업\n"
    if info.related_companies:
        tickers = [r.get('ticker') for r in info.related_companies[:10]]
        md += ", ".join(tickers)
    else:
        md += "- 데이터 없음"
    
    # 10. Short Interest
    md += "\n\n## 10. Short Interest\n"
    if info.short_interest:
        md += "| 결산일 | Short Interest | Short % |\n|--------|----------------|--------|\n"
        for s in info.short_interest[:5]:
            md += f"| {s.get('settlement_date')} | {s.get('short_interest', 0):,} | {s.get('short_percent_of_float', 0):.2f}% |\n"
    else:
        md += "- 데이터 없음\n"
    
    # 11. Short Volume
    md += "\n## 11. Short Volume (최근 거래일)\n"
    if info.short_volume:
        md += "| 날짜 | Short Volume | Total Volume | Short % |\n|------|--------------|--------------|--------|\n"
        for s in info.short_volume[:5]:
            short_vol = s.get('short_volume', 0)
            total_vol = s.get('total_volume', 1)
            pct = (short_vol / total_vol * 100) if total_vol else 0
            md += f"| {s.get('date')} | {short_vol:,} | {total_vol:,} | {pct:.1f}% |\n"
    else:
        md += "- 데이터 없음\n"
    
    # 12. IPO
    md += "\n## 12. IPO 정보\n"
    if info.ipo:
        md += f"""| 항목 | 값 |
|------|-----|
| 상태 | {info.ipo.get('ipo_status', 'N/A')} |
| 상장일 | {info.ipo.get('listing_date', 'N/A')} |
| 공모가 | ${info.ipo.get('offer_price', 0):.2f} |
| 공모 주식수 | {info.ipo.get('shares_offered', 0):,} |
| 거래소 | {info.ipo.get('primary_exchange', 'N/A')} |
"""
    else:
        md += "- 데이터 없음\n"
    
    # 13. Ticker Events
    md += "\n## 13. 티커 이벤트 (Ticker Events)\n"
    if info.ticker_events:
        md += "| 날짜 | 이벤트 유형 |\n|------|------------|\n"
        for e in info.ticker_events[:5]:
            md += f"| {e.get('date', 'N/A')} | {e.get('type', 'N/A')} |\n"
    else:
        md += "- 데이터 없음\n"
    
    return md


if __name__ == "__main__":
    asyncio.run(main())
