import time


class MarketSpecs:

    def __init__(self, kraken_client):
        self.kraken = kraken_client
        self.cache = {}
        self.last_update = 0
        self.ttl = 300  # 5 min cache

    def refresh(self):
        """
        Fetch instrument specs from Kraken.
        NO hardcoding allowed.
        """
        data = self.kraken.get_futures_instruments()

        specs = {}

        for item in data.get("instruments", []):
            symbol = item["symbol"]

            specs[symbol] = {
                "symbol": symbol,
                "contract_size": float(item.get("contractSize", 1)),
                "min_size": float(item.get("minOrderSize", 1)),
                "size_step": float(item.get("orderSizeIncrement", 1)),
                "max_size": float(item.get("maxOrderSize", 1e9)),
                "type": "futures"
            }

        self.cache = specs
        self.last_update = time.time()

    def get(self, symbol):
        if time.time() - self.last_update > self.ttl:
            self.refresh()

        return self.cache.get(symbol, {
            "symbol": symbol,
            "contract_size": 1,
            "min_size": 1,
            "size_step": 1,
            "max_size": 1e9
        })
