import math


class SizingEngine:

    def __init__(self, strategy):
        self.strategy = strategy

    def calculate_size(self, symbol, price, signal, balance):

        entry_cfg = getattr(self.strategy, "entry", {})
        risk_cfg = getattr(self.strategy, "risk", {})

        available_margin = self._extract_margin(balance)

        if available_margin is None:
            print("[SIZING] invalid balance")
            return 0

        if not price or price <= 0:
            print("[SIZING] invalid price")
            return 0

        margin_fraction = float(
            signal.get("margin_fraction", entry_cfg.get("margin_fraction", 0.1))
        )

        usd_size = available_margin * margin_fraction

        min_usd = float(entry_cfg.get("min_usd_size", 0))

        if usd_size < min_usd:
            print("[SIZING] usd_size too small")
            return 0

        raw_size = usd_size / float(price)

        step = int(entry_cfg.get("size_step", 1))
        if step < 1:
            step = 1

        size = math.floor(raw_size / step) * step

        # 🔴 FIX: NO ZERO SIZES EVER
        if size <= 0:
            size = step

        min_size = int(entry_cfg.get("min_size", 1))

        # soft floor (not kill)
        if size < min_size:
            size = min_size

        max_size = risk_cfg.get("max_position_size")
        if max_size:
            size = min(size, int(max_size))
            print("[SIZING] symbol =", symbol)
            print("[SIZING] price =", price)
            print("[SIZING] raw_size =", raw_size)
            print("[SIZING] final_size =", size)

        return size

    def _extract_margin(self, balance):

        if not balance:
            return None

        if isinstance(balance, dict) and "availableMargin" in balance:
            try:
                return float(balance["availableMargin"])
            except:
                return None

        try:
            return float(
                balance.get("accounts", {})
                .get("flex", {})
                .get("availableMargin", 0)
            )
        except:
            return None
