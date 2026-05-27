class LadderReconciler:
    """
    Single source of truth for:
    - TP orders
    - Reentry orders
    - Ladder progression
    - Order cleanup
    """

    def __init__(self, exchange, state_store, strategy):
        self.exchange = exchange
        self.state_store = state_store
        self.strategy = strategy

    # =========================
    # MAIN ENTRY
    # =========================
    def reconcile(self, symbol, entry_price, position_size, level):

        state = self.state_store.get(symbol)

        direction = getattr(self.strategy, "direction", "long")

        # =========================
        # LOAD LEVEL CONFIG
        # =========================
        level_cfg = self.strategy.reentry_levels[level - 1]

        # =========================
        # CANCEL OLD ORDERS (CRITICAL)
        # =========================
        self._cancel_if_exists(state.get("tp_order_id"))
        self._cancel_if_exists(state.get("reentry_order_id"))

        # =========================
        # TAKE PROFIT ORDER
        # =========================
        tp_pct = float(level_cfg.get("take_profit_pct", 0.003))

        if direction == "short":
            tp_price = entry_price * (1 - tp_pct)
        else:
            tp_price = entry_price * (1 + tp_pct)

        tp_price = self._round_price(symbol, tp_price)

        tp_order = (
            self.exchange.buy_limit if direction == "short"
            else self.exchange.sell_limit
        )(
            symbol=symbol,
            size=position_size,
            price=tp_price,
            reduce_only=True
        )

        if self._ok(tp_order):
            state["tp_order_id"] = self._extract_order_id(tp_order)
            state["tp_price"] = tp_price
        else:
            state["tp_order_id"] = None

        # =========================
        # MAX LEVEL STOP
        # =========================
        if level >= self.strategy.max_level:
            state["reentry_order_id"] = None
            state["reentry_price"] = None
            state["reentry_size"] = None
            state["needs_new_ladder"] = False
            return state

        # =========================
        # REENTRY ORDER
        # =========================
        drop_pct = float(level_cfg.get("drop_pct", 0.01))
        size_mult = float(level_cfg.get("size_multiplier", 1.0))

        if direction == "short":
            reentry_price = entry_price * (1 + drop_pct)
        else:
            reentry_price = entry_price * (1 - drop_pct)

        reentry_price = self._round_price(symbol, reentry_price)

        reentry_size = int(position_size * size_mult)

        # turbo safety
        if "TURBO" in symbol:
            reentry_size = max((reentry_size // 100) * 100, 100)

        reentry_order = (
            self.exchange.sell_limit if direction == "short"
            else self.exchange.buy_limit
        )(
            symbol=symbol,
            size=reentry_size,
            price=reentry_price,
            reduce_only=False
        )

        if self._ok(reentry_order):
            state["reentry_order_id"] = self._extract_order_id(reentry_order)
            state["reentry_price"] = reentry_price
            state["reentry_size"] = reentry_size
            state["reentry_pending"] = False
        else:
            state["reentry_order_id"] = None

        # =========================
        # UPDATE STATE
        # =========================
        state["level"] = level
        state["needs_new_ladder"] = False

        return state

    # =========================
    # HELPERS
    # =========================
    def _cancel_if_exists(self, order_id):
        if order_id:
            try:
                self.exchange.cancel_order(order_id)
            except Exception as e:
                print("[RECONCILE] cancel failed:", e)

    def _ok(self, order_response):
        return (
            order_response
            and order_response.get("sendStatus", {}).get("status") == "placed"
        )

    def _round_price(self, symbol, price):

        if "XBT" in symbol:
            return round(price, 1)

        if "XRP" in symbol:
            return round(price, 5)

        return round(price, 6)

    def _extract_order_id(self, order_response):

        if not order_response:
            return None

        send = order_response.get("sendStatus", {})

        return send.get("order_id")
