"""Test WebSocket watchlist data by reading from watchlist store directly"""
import asyncio
from backend.data.watchlist_store import load_watchlist

def test():
    watchlist = load_watchlist()
    
    if watchlist:
        print(f"Total items: {len(watchlist)}")
        for item in watchlist[:5]:
            ticker = item.get("ticker", "?")
            score = item.get("score", "?")
            score_v2 = item.get("score_v2", "MISSING")
            print(f"{ticker}: score={score}, score_v2={score_v2}")
    else:
        print("Watchlist is empty")

if __name__ == "__main__":
    test()
