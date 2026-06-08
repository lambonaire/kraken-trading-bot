import math


class SizingEngine:

    def __init__(self, strategy, market_specs=None):
        self.strategy = strategy
        self.market_specs = market_specs  # 🔥 NEW

    def calculate_size(self, symbol, price, signal, balance):

        entry_cfg = getattr(self.strategy, "entry", {})
        risk_cfg = getattr(self.strategy, "risk", {})

        available_margin = self._extract_margin(balance)

        if available_margin is None:
            print("[SIZING] invalid balance")
            return 0.0

        if not price or price <= 0:
            print("[SIZING] invalid price")
            return 0.0

        # =========================
        # MARKET SPECS (EXCHANGE TRUTH)
        # =========================
        specs = None
        if self.market_specs:
            specs = self.market_specs.get(symbol)

        # fallback safety
        step = float(
            specs.get("size_step")
            if specs else entry_cfg.get("size_step", 0.001)
        )

        min_size = float(
            specs.get("min_size")
            if specs else entry_cfg.get("min_size", 0.001)
        )

        max_size = float(
            specs.get("max_size")
            if specs else risk_cfg.get("max_position_size", 1e9)
        )

        if step <= 0:
            step = 0.001

        # =========================
        # CONFIG
        # =========================
        margin_fraction = float(
            signal.get("margin_fraction", entry_cfg.get("margin_fraction", 0.1))
        )

        min_usd = float(entry_cfg.get("min_usd_size", 0.0))

        # =========================
        # CORE CALCULATION
        # =========================
        usd_size = available_margin * margin_fraction

        if usd_size < min_usd:
            print("[SIZING] usd_size below min_usd -> skip")
            return 0.0

        raw_size = usd_size / float(price)

        # round DOWN to exchange step
        size = math.floor(raw_size / step) * step

        # =========================
        # SAFETY
        # =========================
        if size <= 0:
            print("[SIZING] size too small after step rounding -> skip")
            return 0.0

        if size < min_size:
            print("[SIZING] size below min_size -> skip")
            return 0.0

        size = min(size, max_size)

        size = round(size, 8)

        print("[SIZING] symbol =", symbol)
        print("[SIZING] step =", step)
        print("[SIZING] raw_size =", raw_size)
        print("[SIZING] final_size =", size)

        return size

    def _extract_margin(self, balance):
        if not balance:
            return None

        try:
            return float(
                balance.get("accounts", {})
                .get("flex", {})
                .get("availableMargin", 0)
            )
        except:
            return None
