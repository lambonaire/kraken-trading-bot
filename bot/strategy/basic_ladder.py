class BasicLadderStrategy:
    def __init__(self, config):
        self.config = config
        self.reentry_levels = config["reentry"]
        self.max_level = config.get("max_level", len(self.reentry_levels))

    def on_tick(self, market_data, state):
        price = market_data["price"]
        symbol = self.config["symbol"]

        current_level = int(state.get("level", 1) or 1)
        current_level = max(1, min(current_level, self.max_level))

        level_cfg = self.reentry_levels[current_level - 1]

        position_size = state.get("position_size", 0) or 0
        entry_price = state.get("entry_price")

        # 1. Geen positie → entry
        if position_size == 0 or entry_price is None:
            return {
                "action": "OPEN_ENTRY",
                "symbol": symbol,
                "margin_fraction": self.config["base_entry"]["margin_fraction"],
                "level": 1,
            }

        # 2. Take profit
        tp_pct = level_cfg.get("take_profit_pct")
        if tp_pct is not None:
            tp_price = entry_price * (1 + tp_pct)
            if price >= tp_price:
                return {
                    "action": "TAKE_PROFIT",
                    "symbol": symbol,
                    "level": current_level,
                }

        # 3. Re-entry alleen als je nog niet op max level zit
        if current_level < self.max_level:
            drop_pct = level_cfg.get("drop_pct")
            size_mult = level_cfg.get("size_multiplier", 1.0)

            if drop_pct is not None:
                trigger_price = entry_price * (1 - drop_pct)
                if price <= trigger_price:
                    return {
                        "action": "REENTRY",
                        "symbol": symbol,
                        "size_multiplier": size_mult,
                        "next_level": current_level + 1,
                        "level": current_level,
                    }

        return None
