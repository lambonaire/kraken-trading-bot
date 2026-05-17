class BasicLadderStrategy:
    def __init__(self, config):
        self.config = config
        self.reentry_levels = config["reentry"]

    def on_tick(self, market_data, state):
        price = market_data["price"]

        symbol = self.config["symbol"]
        level_index = state.get("level", 1) - 1
        level_index = min(level_index, len(self.reentry_levels) - 1)

        level_cfg = self.reentry_levels[level_index]

        # -------------------------
        # 1. NO POSITION → ENTRY
        # -------------------------
        if state.get("position_size", 0) == 0:
            return {
                "action": "OPEN_ENTRY",
                "symbol": symbol,
                "margin_fraction": self.config["base_entry"]["margin_fraction"]
            }

        entry_price = state["entry_price"]

        # -------------------------
        # 2. TAKE PROFIT CHECK
        # -------------------------
        tp_pct = level_cfg.get("take_profit_pct")

        if tp_pct is not None:
            tp_price = entry_price * (1 + tp_pct)

            if price >= tp_price:
                return {
                    "action": "TAKE_PROFIT",
                    "symbol": symbol,
                    "level": state.get("level", 1)
                }

        # -------------------------
        # 3. RE-ENTRY (DIP BUY)
        # -------------------------
        drop_pct = level_cfg.get("drop_pct")
        size_mult = level_cfg.get("size_multiplier", 1.0)

        if drop_pct is not None:
            trigger_price = entry_price * (1 - drop_pct)

            if price <= trigger_price:
                return {
                    "action": "REENTRY",
                    "symbol": symbol,
                    "size_multiplier": size_mult,
                    "next_level": state.get("level", 1) + 1
                }

        return None
