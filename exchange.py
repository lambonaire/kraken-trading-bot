import requests

BASE_URL = "https://futures.kraken.com/derivatives/api/v3"

def get_tickers():
    url = f"{BASE_URL}/tickers"
    response = requests.get(url)
    data = response.json()
    return data["tickers"]

def get_doge_price():
    tickers = get_tickers()

    for t in tickers:
        if "DOGE" in t["symbol"]:
            return float(t["last"])

    return None
