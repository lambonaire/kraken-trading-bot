class StateStore:
    """
    Multi-symbol safe state store.

    Responsibilities:
    - keep one isolated state bucket per symbol
    - provide consistent defaults
    - centralize entry / TP / reentry / level updates
    - support clean reset on flat position
    """

    def __init__(self):
        self.states = {}

    # =========================
    # INTERNAL
    # =========================
    def _default_state(self, symbol: str):
        return {
            "symbol": symbol,
            "position_size": 0.0,
            "entry_price": None,
            "level": 1,
            "entry_order_id": None,
            "tp_order_id": None,
            "reentry_order_id": None,
            "reentry_pending": False,
            "needs_new_ladder": True,
            "ladder_active": False,
            "tp_price": None,
            "tp_size": None,
            "reentry_price": None,
            "reentry_size": None,
            "last_reconciled_position_size": 0.0,
        }

    def _get_symbol(self, symbol: str):
        if symbol not in self.states:
            self.states[symbol] = self._default_state(symbol)
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
        if not symbol:
            raise ValueError("Symbol is required for multi-bot isolation")
        self.states[symbol] = self._default_state(symbol)
        return self.states[symbol]

    # =========================
    # ENTRY UPDATE
    # =========================
    def set_entry(self, symbol, price, size, order_id=None):
        state = self._get_symbol(symbol)

        state["symbol"] = symbol
        state["entry_price"] = price
        state["position_size"] = float(size)
        state["entry_order_id"] = order_id
        state["level"] = 1

        # after entry we usually want ladder creation / sync to be possible
        state["reentry_pending"] = False
        state["needs_new_ladder"] = False

        self.states[symbol] = state
        return state

    # =========================
    # LEVEL MANAGEMENT
    # =========================
    def set_level(self, symbol, level: int):
        state = self._get_symbol(symbol)
        state["level"] = int(level)
        self.states[symbol] = state
        return state

    def increase_level(self, symbol):
        state = self._get_symbol(symbol)
        state["level"] = int(state.get("level") or 1) + 1
        self.states[symbol] = state
        return state

    # =========================
    # POSITION UPDATE
    # =========================
    def update_position_size(self, symbol, size):
        state = self._get_symbol(symbol)
        state["position_size"] = float(size)
        self.states[symbol] = state
        return state

    # =========================
    # LADDER FLAGS
    # =========================
    def trigger_ladder_rebuild(self, symbol):
        state = self._get_symbol(symbol)
        state["needs_new_ladder"] = True
        self.states[symbol] = state
        return state

    def clear_ladder_rebuild(self, symbol):
        state = self._get_symbol(symbol)
        state["needs_new_ladder"] = False
        self.states[symbol] = state
        return state

    def set_reentry_pending(self, symbol, pending: bool):
        state = self._get_symbol(symbol)
        state["reentry_pending"] = bool(pending)
        self.states[symbol] = state
        return state

    # =========================
    # TP / REENTRY
    # =========================
    def set_tp(self, symbol, order_id=None, price=None, size=None):
        state = self._get_symbol(symbol)
        state["tp_order_id"] = order_id
        state["tp_price"] = price
        state["tp_size"] = size
        self.states[symbol] = state
        return state

    def set_reentry(self, symbol, order_id=None, price=None, size=None):
        state = self._get_symbol(symbol)
        state["reentry_order_id"] = order_id
        state["reentry_price"] = price
        state["reentry_size"] = size
        state["reentry_pending"] = False
        self.states[symbol] = state
        return state

    # =========================
    # CLEAR POSITION (keep symbol bucket, wipe trade state)
    # =========================
    def clear_position(self, symbol):
        state = self._get_symbol(symbol)

        state["position_size"] = 0.0
        state["entry_price"] = None
        state["level"] = 1
        state["entry_order_id"] = None
        state["tp_order_id"] = None
        state["reentry_order_id"] = None
        state["reentry_pending"] = False
        state["needs_new_ladder"] = True
        state["ladder_active"] = False
        state["tp_price"] = None
        state["tp_size"] = None
        state["reentry_price"] = None
        state["reentry_size"] = None
        state["last_reconciled_position_size"] = 0.0

        self.states[symbol] = state
        return state

    # =========================
    # FULL LADINGER HELPER
    # =========================
    def update_ladder(
        self,
        symbol,
        tp_order_id=None,
        reentry_order_id=None,
        tp_price=None,
        tp_size=None,
        reentry_price=None,
        reentry_size=None,
        level=None,
        needs_new_ladder=None,
        reentry_pending=None,
    ):
        state = self._get_symbol(symbol)

        if tp_order_id is not None:
            state["tp_order_id"] = tp_order_id
        if reentry_order_id is not None:
            state["reentry_order_id"] = reentry_order_id
        if tp_price is not None:
            state["tp_price"] = tp_price
        if tp_size is not None:
            state["tp_size"] = tp_size
        if reentry_price is not None:
            state["reentry_price"] = reentry_price
        if reentry_size is not None:
            state["reentry_size"] = reentry_size
        if level is not None:
            state["level"] = int(level)
        if needs_new_ladder is not None:
            state["needs_new_ladder"] = bool(needs_new_ladder)
        if reentry_pending is not None:
            state["reentry_pending"] = bool(reentry_pending)

        self.states[symbol] = state
        return state
