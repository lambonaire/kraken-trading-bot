import math


class SizingEngine:

    def __init__(self, strategy):
        self.strategy = strategy

    def calculate_size(self, symbol, price, signal, balance):

        entry_cfg = getattr(self.strategy, "entry", {})
        risk_cfg = getattr(self.strategy, "risk", {})

        # -------------------------
        # SAFE MARGIN EXTRACTION
        # -------------------------
        available_margin = self._extract_margin(balance)
        if available_margin is None:
            print("[SIZING] no margin")
            return 0

        margin_fraction = float(
            signal.get("margin_fraction", entry_cfg.get("margin_fraction", 0.1))
        )

        usd_size = available_margin * margin_fraction

        min_usd = float(entry_cfg.get("min_usd_size", 0))
        if usd_size < min_usd:
            return 0

        raw_size = usd_size / price

        # -------------------------
        # STEP LOGIC
        # -------------------------
        step = int(entry_cfg.get("size_step", 1))
        size = math.floor(raw_size / step) * step

        min_size = int(entry_cfg.get("min_size", 1))
        if size < min_size:
            return 0

        # -------------------------
        # TURBO MODE
        # -------------------------
        if "TURBO" in symbol:
            size = (size // 100) * 100
            if size <= 0:
                size = 100

        # -------------------------
        # MAX CAP
        # -------------------------
        max_size = risk_cfg.get("max_position_size")
        if max_size:
            size = min(size, int(max_size))

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
