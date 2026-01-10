"""
정확히 50.0으로 표시되는 종목들의 원인 분석
결과를 파일로 저장
"""

import asyncio
from backend.data.database import MarketDB
from backend.strategies.seismograph import SeismographStrategy


async def analyze():
    db = MarketDB("data/market_data.db")
    await db.initialize()
    strategy = SeismographStrategy()

    tickers = ["MOBX", "ACFN", "MRNOW", "BFRGW", "CUBWW", "MRTNO", "KITTW"]

    with open("analysis_result.txt", "w", encoding="utf-8") as f:
        f.write("=== 50.0점 종목 상세 분석 ===\n\n")
        for t in tickers:
            bars = await db.get_daily_bars(t, days=20)
            count = len(bars) if bars else 0

            if count >= 5:
                data = [
                    {
                        "open": b.open,
                        "high": b.high,
                        "low": b.low,
                        "close": b.close,
                        "volume": b.volume,
                    }
                    for b in reversed(bars)
                ]
                result = strategy.calculate_watchlist_score_detailed(t, data)

                f.write(f"[{t}] 일봉: {count}일\n")
                f.write(f"  score (v1): {result.get('score')}\n")
                f.write(f"  score_v2:   {result.get('score_v2')}\n")
                f.write(f"  stage:      {result.get('stage')}\n")
                f.write(f"  signals:    {result.get('signals')}\n")
                if result.get("intensities"):
                    f.write("  intensities:\n")
                    for k, v in result.get("intensities", {}).items():
                        f.write(f"    - {k}: {v:.2f} ({v * 100:.0f}%)\n")
                f.write("\n")
            else:
                f.write(f"[{t}] 일봉: {count}일 → 데이터 부족\n\n")

    print("분석 완료! analysis_result.txt 확인")


if __name__ == "__main__":
    asyncio.run(analyze())
