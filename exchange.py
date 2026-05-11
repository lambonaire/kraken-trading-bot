from dotenv import load_dotenv
import os
import requests

load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

BASE_URL = "https://futures.kraken.com/derivatives/api/v3"

def get_tickers():
    url = f"{BASE_URL}/tickers"
    r = requests.get(url, timeout=10)
    return r.json()["tickers"]


def get_doge_price():
    tickers = get_tickers()

    for t in tickers:
        if "DOGE" in t.get("symbol", ""):
            return t

    return None

if __name__ == "__main__":
    print("Bot test start...")

    doge = get_doge_price()
    print("DOGE data:", doge)
