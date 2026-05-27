class LadderStateMachine:
    """
    Deterministic ladder state machine.

    States:
    - FLAT
    - ENTRY_FILLED
    - LADDER_ACTIVE
    - MAX_LEVEL_REACHED
    """

    FLAT = "FLAT"
    ENTRY_FILLED = "ENTRY_FILLED"
    LADDER_ACTIVE = "LADDER_ACTIVE"
    MAXED = "MAX_LEVEL_REACHED"

    def __init__(self, state_store, reconciler, strategy):
        self.state_store = state_store
        self.reconciler = reconciler
        self.strategy = strategy

    # =========================
    # MAIN ENTRY
    # =========================
    def on_tick(self, symbol, market_price):

        state = self.state_store.get(symbol)

        position_size = float(state.get("position_size") or 0)
        entry_price = state.get("entry_price")
        level = int(state.get("level") or 1)

        # =========================
        # STATE RESOLUTION
        # =========================
        current_state = self._resolve_state(position_size, entry_price, level)

        # =========================
        # STATE MACHINE ROUTING
        # =========================

        if current_state == self.FLAT:
            return self._handle_flat(symbol)

        if current_state == self.ENTRY_FILLED:
            return self._handle_entry(symbol, state)

        if current_state == self.LADDER_ACTIVE:
            return self._handle_ladder(symbol, state)

        if current_state == self.MAXED:
            return None

        return None

    # =========================
    # STATE RESOLVER
    # =========================
    def _resolve_state(self, position_size, entry_price, level):

        if position_size == 0 or entry_price is None:
            return self.FLAT

        if level >= self.strategy.max_level:
            return self.MAXED

        if level == 1:
            return self.ENTRY_FILLED

        return self.LADDER_ACTIVE

    # =========================
    # HANDLERS
    # =========================

    def _handle_flat(self, symbol):

        return {
            "action": "OPEN_ENTRY",
            "symbol": symbol,
            "margin_fraction": self.strategy.config["entry"]["margin_fraction"],
            "level": 1,
            "next_level": 1
        }

    def _handle_entry(self, symbol, state):

        entry_price = state["entry_price"]
        size = state["position_size"]

        self.reconciler.reconcile(
            symbol=symbol,
            entry_price=entry_price,
            position_size=size,
            level=1
        )

        state["level"] = 1
        state["ladder_active"] = True

        return None

    def _handle_ladder(self, symbol, state):

        entry_price = state["entry_price"]
        size = state["position_size"]
        level = int(state.get("level") or 1)

        # IMPORTANT: only reconcile if ladder must advance
        if state.get("needs_new_ladder"):

            next_level = min(level + 1, self.strategy.max_level)

            state["level"] = next_level

            self.reconciler.reconcile(
                symbol=symbol,
                entry_price=entry_price,
                position_size=size,
                level=next_level
            )

        return None
