class StateStore:

    def __init__(self):
        # 🔥 MULTI-BOT SAFE: state per symbol
        self.states = {}

    # =========================
    # INTERNAL
    # =========================

    def _get_symbol(self, symbol: str):
        if symbol not in self.states:
            self.states[symbol] = {
                "symbol": symbol,
                "position_size": 0,
                "entry_price": None,
                "level": 1,
                "entry_order_id": None,
                "tp_order_id": None,
                "reentry_order_id": None,
                "reentry_pending": False,
                "needs_new_ladder": False,
                "tp_price": None,
                "tp_size": None,
                "reentry_price": None,
                "reentry_size": None,
            }
        return self.states[symbol]

    # =========================
    # READ
    # =========================

    def get(self, symbol: str):
        if not symbol:
            raise ValueError("Symbol is required for multi-bot isolation")

        return self._get_symbol(symbol)

    # =========================
    # RESET FULL SYMBOL STATE
    # =========================

    def reset(self, symbol: str):
        if symbol in self.states:
            del self.states[symbol]

    # =========================
    # ENTRY UPDATE
    # =========================

    def set_entry(self, symbol, price, size, order_id=None):
        state = self._get_symbol(symbol)

        state["symbol"] = symbol
        state["entry_price"] = price
        state["position_size"] = size
        state["entry_order_id"] = order_id
        state["level"] = 1
        state["needs_new_ladder"] = False

    # =========================
    # LEVEL MANAGEMENT
    # =========================

    def increase_level(self, symbol):
        state = self._get_symbol(symbol)
        state["level"] += 1

    # =========================
    # POSITION UPDATE
    # =========================

    def update_position_size(self, symbol, size):
        state = self._get_symbol(symbol)
        state["position_size"] = size

    # =========================
    # FLAG LADDER REBUILD
    # =========================

    def trigger_ladder_rebuild(self, symbol):
        state = self._get_symbol(symbol)
        state["needs_new_ladder"] = True

    # =========================
    # CLEAR POSITION (FULL RESET STATE)
    # =========================

    def clear_position(self, symbol):
        state = self._get_symbol(symbol)

        state["position_size"] = 0
        state["entry_price"] = None
        state["entry_order_id"] = None
        state["tp_order_id"] = None
        state["reentry_order_id"] = None
        state["reentry_pending"] = False
        state["needs_new_ladder"] = False
        state["level"] = 1
