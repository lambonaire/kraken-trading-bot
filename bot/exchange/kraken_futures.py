import requests
import json

BASE_URL = "https://futures.kraken.com/derivatives/api/v3"


def get_ticker(symbol="PF_DOGEUSD"):
    """
    Haalt markPrice of last price op van Kraken Futures.
    Robuust voor verschillende API response formats.
    """

    url = f"{BASE_URL}/tickers"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        # 🔥 Soms is het een dict met "tickers"
        tickers = data.get("tickers")

        # 🔥 Soms is het direct een list
        if tickers is None:
            tickers = data if isinstance(data, list) else []

        for t in tickers:
            sym = t.get("symbol")

            if sym == symbol or (sym and "DOGE" in sym):
                price = t.get("markPrice") or t.get("last")

                print(json.dumps(t, indent=2))

                return float(price) if price is not None else None

    except Exception as e:
        print(f"[ERROR get_ticker] {e}")

    return None
