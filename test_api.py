"""Test REST API watchlist response"""
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/api/watchlist", timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Find AMCI 
                for item in data[:5]:  # First 5 items
                    ticker = item.get("ticker", "?")
                    score = item.get("score", "?")
                    score_v2 = item.get("score_v2", "MISSING")
                    print(f"{ticker}: score={score}, score_v2={score_v2}")
            else:
                print(f"API Error: {response.status_code}")
        except Exception as e:
            print(f"Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
