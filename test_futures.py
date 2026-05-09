import requests

url = "https://futures.kraken.com/derivatives/api/v3/tickers"
data = requests.get(url).json()

for t in data["tickers"]:
    if "DOGE" in t["symbol"]:
        print(t["symbol"], t["last"])
