import time

class BasicLadderStrategy:
    def __init__(self, config):
        self.config = config

        raw_direction = (
            config.get("direction")
            or config.get("side")
            or "buy"
        ).lower()

        if raw_direction in ("buy", "long"):
            self.direction = "long"
            self.side = "buy"
        elif raw_direction in ("sell", "short"):
            self.direction = "short"
            self.side = "sell"
        else:
            raise ValueError(f"Unsupported direction/side: {raw_direction}")

        self.reentry_levels = config.get("reentry_levels") or config.get("reentry", [])

        if not self.reentry_levels:
            raise ValueError("Missing 'reentry_levels' in strategy config")

        self.max_level = int(config.get("max_level", len(self.reentry_levels)))

    def on_tick(self, market_data, state):
        print(">>> STRATEGY CALLED")

        symbol = self.config["symbol"]

        current_level = int(state.get("level") or 1)
        current_level = max(1, min(current_level, self.max_level))

        entry_cfg = self.config.get("entry", {})
        now = time.time()

        # block while reconciliation / sync cooldown is active
        if state.get("reconciling", False):
            return None

        if state.get("entry_order_pending", False):
            return None

        if now < float(state.get("flat_cooldown_until", 0) or 0):
            return None

        # do not open if there is already a live position
        if float(state.get("position_size", 0) or 0) > 0:
            return None

        # do not open if ladder is already active
        if state.get("ladder_active", False):
            return None

        # only open when ladder must be rebuilt
        if not state.get("needs_new_ladder", False):
            return None

        level_cfg = self.reentry_levels[current_level - 1]

        return {
            "action": "OPEN_ENTRY",
            "symbol": symbol,
            "side": self.side,
            "margin_fraction": float(entry_cfg.get("margin_fraction", 0.1)),
            "tp_pct": float(level_cfg.get("take_profit_pct", 0.003)),
            "drop_pct": float(level_cfg.get("drop_pct", 0.01)),
            "size_multiplier": float(level_cfg.get("size_multiplier", 1.0)),
            "level": 1,
            "next_level": 1,
        }
