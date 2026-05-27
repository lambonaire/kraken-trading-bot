class BasicLadderStrategy:

    def __init__(self, config):
        self.config = config

        self.reentry_levels = config.get("reentry", [])

        if not self.reentry_levels:
            raise ValueError("Missing 'reentry' in strategy config")

        self.max_level = config.get(
            "max_level",
            len(self.reentry_levels)
        )

    def on_tick(self, market_data, state):

        print(">>> STRATEGY CALLED")

        symbol = self.config["symbol"]

        current_level = int(state.get("level") or 1)
        current_level = max(1, min(current_level, self.max_level))

        level_cfg = self.reentry_levels[current_level - 1]

        position_size = float(state.get("position_size") or 0)
        entry_price = state.get("entry_price")

        # =========================
        # OPEN ENTRY ONLY
        # =========================

        if position_size <= 0 or entry_price is None:

            entry_cfg = self.config.get("entry", {})

            return {
                "action": "OPEN_ENTRY",
                "symbol": symbol,
                "margin_fraction": float(entry_cfg.get("margin_fraction", 0.1)),
                "tp_pct": float(level_cfg.get("take_profit_pct", 0.003)),
                "drop_pct": float(level_cfg.get("drop_pct", 0.01)),
                "size_multiplier": float(level_cfg.get("size_multiplier", 1.0)),
                "level": 1,
                "next_level": 1
            }

        return None
