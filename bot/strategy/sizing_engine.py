import math


class SizingEngine:
    """
    Unified sizing engine:
    - supports BTC / ETH / XRP / DOGE / TURBO
    - respects min/max constraints
    - safe rounding
    - no loop dependencies
    """

    def __init__(self, strategy):
        self.strategy = strategy

    # =========================
    # PUBLIC ENTRY
    # =========================
    def calculate_size(self, symbol, price, signal, balance):

        entry_cfg = getattr(self.strategy, "entry", {})

        margin_fraction = float(
            signal.get(
                "margin_fraction",
                entry_cfg.get("margin_fraction", 0.1)
            )
        )

        available_margin = self._extract_margin(balance)

        if available_margin <= 0:
            print("[SIZING] No margin available")
            return 0

        # =========================
        # USD ALLOCATION
        # =========================
        usd_size = available_margin * margin_fraction

        min_usd = float(
            entry_cfg.get("min_usd_size", 0)
        )

        if usd_size < min_usd:
            print(f"[SIZING] SKIP (min usd): {usd_size}")
            return 0

        # =========================
        # RAW SIZE
        # =========================
        raw_size = usd_size / price

        # =========================
        # STEP LOGIC
        # =========================
        size_step = int(entry_cfg.get("size_step", 1))
        min_size = int(entry_cfg.get("min_size", 1))

        size = math.floor(raw_size / size_step) * size_step

        if size < min_size:
            size = 0

        # =========================
        # TURBO MODE SAFETY
        # =========================
        if "TURBO" in symbol:

            size = (size // 100) * 100

            if size <= 0:
                size = 100

        # =========================
        # MAX RISK CAP (optional)
        # =========================
        risk_cfg = getattr(self.strategy, "risk", {})
        max_size = risk_cfg.get("max_position_size")

        if max_size:
            size = min(size, int(max_size))

        print(f"[SIZING] FINAL SIZE {symbol}: {size}")

        return size

    # =========================
    # BACKWARD COMPATIBILITY
    # =========================
    def calculate_entry_size(self, symbol, price, signal, available_margin):

        usd_size = available_margin * float(
            signal.get("margin_fraction", 0.1)
        )

        raw_size = usd_size / price

        entry_cfg = getattr(self.strategy, "entry", {})

        size_step = int(entry_cfg.get("size_step", 1))
        min_size = int(entry_cfg.get("min_size", 1))

        size = math.floor(raw_size / size_step) * size_step

        if size < min_size:
            return 0

        if "TURBO" in symbol:
            size = (size // 100) * 100
            if size <= 0:
                size = 100

        return size

    # =========================
    # COMPATIBILITY FIX (loop expects this)
    # =========================
    def _extract_margin(self, balance):

        if not balance:
            return 0

        try:
            return float(
                balance.get("accounts", {})
                .get("flex", {})
                .get("availableMargin", 0)
            )
        except:
            return 0
