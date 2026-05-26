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
            }
        return self.states[symbol]

    # =========================
    # READ
    # =========================

    def get(self, symbol: str = None):
        if symbol:
            return self._get_symbol(symbol)

        # fallback (veilig voor oude code)
        return next(iter(self.states.values()), {})

    # =========================
    # RESET
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

    # =========================
    # LEVEL
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
    # CLEAR POSITION
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
