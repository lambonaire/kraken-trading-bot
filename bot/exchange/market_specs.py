import time

from bot.exchange.kraken_futures import get_instruments


class MarketSpecs:
    def __init__(self):
        self.cache = {}
        self.last_update = 0
        self.ttl = 300  # 5 min cache

    def refresh(self):
        """
        Fetch instrument specs from Kraken futures module.
        """

        data = get_instruments()

        instruments = []

        if isinstance(data, dict):
            instruments = data.get("instruments", [])
        elif isinstance(data, list):
            instruments = data
        else:
            print("[MarketSpecs] invalid response format")
            return

        specs = {}

        for item in instruments:
            if not isinstance(item, dict):
                continue

            symbol = item.get("symbol")
            if not symbol:
                continue

            specs[symbol] = {
                "symbol": symbol,
                "contract_size": float(item.get("contractSize", 1)),
                "min_size": float(item.get("minOrderSize", 1)),
                "size_step": float(item.get("orderSizeIncrement", 1)),
                "max_size": float(item.get("maxOrderSize", 1e9)),
                "tick_size": float(item.get("tickSize", 0.0)) if item.get("tickSize") else 0.0,
                "type": "futures",
            }

        self.cache = specs
        self.last_update = time.time()

        print(f"[MarketSpecs] loaded {len(specs)} instruments")

    def get(self, symbol):
        if time.time() - self.last_update > self.ttl:
            self.refresh()

        return self.cache.get(symbol, {
            "symbol": symbol,
            "contract_size": 1,
            "min_size": 1,
            "size_step": 1,
            "max_size": 1e9,
            "tick_size": 0.0,
            "type": "unknown",
        })
