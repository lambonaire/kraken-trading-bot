class OrderManager:

    def __init__(self, exchange, state_store, strategy=None):
        self.exchange = exchange
        self.state_store = state_store
        self.strategy = strategy

    # =========================
    # MAIN
    # =========================
    def execute(self, signal, market_data):
        if not signal:
            return None

        action = signal.get("action")

        if action == "OPEN_ENTRY":
            return self._open_entry(signal, market_data)

        if action == "TAKE_PROFIT":
            return self._take_profit(signal, market_data)

        if action == "REENTRY":
            return self._reentry(signal, market_data)

        raise ValueError(f"Unknown action: {action}")

    # =========================
    # ENTRY
    # =========================
    def _open_entry(self, signal, market_data):

        symbol = signal["symbol"]

        margin_fraction = float(
            signal["margin_fraction"]
        )

        balance = self.exchange.balance()

        available_margin = self._extract_available_margin(
            balance
        )

        if available_margin is None:
            raise ValueError(
                "Could not extract available margin"
            )

        price = float(market_data["price"])

        usd_size = available_margin * margin_fraction

        raw_size = usd_size / price

        size = int(raw_size)

        print("ENTRY SIZE:", size)

        if size <= 0:
            return None

        # =========================
        # MARKET ENTRY
        # =========================

        order = self.exchange.buy_market(
            symbol=symbol,
            size=size
        )

        print("ENTRY RESPONSE:", order)

        order_id = self._extract_order_id(order)

        self.state_store.set_entry(
            price=price,
            size=size,
            order_id=order_id,
            symbol=symbol
        )

        state = self.state_store.get()

        # =========================
        # TP LIMIT
        # =========================

        tp_pct = float(
            signal.get("tp_pct", 0.003)
        )

        tp_price = price * (1 + tp_pct)

        print("TP PRICE:", tp_price)

        tp_order = self.exchange.sell_limit(
            symbol=symbol,
            size=size,
            price=tp_price,
            reduce_only=True
        )

        print("TP RESPONSE:", tp_order)

        tp_order_id = self._extract_order_id(
            tp_order
        )

        state["tp_order_id"] = tp_order_id

        # =========================
        # REENTRY LIMIT BUY
        # =========================

        drop_pct = float(
            signal.get("drop_pct", 0.01)
        )

        size_multiplier = float(
            signal.get("size_multiplier", 1.0)
        )

        reentry_price = price * (
            1 - drop_pct
        )

        reentry_size = int(
            size * size_multiplier
        )

        if reentry_size <= 0:
            reentry_size = 1

        print(
            "REENTRY LIMIT:",
            reentry_price,
            reentry_size
        )

        reentry_order = self.exchange.buy_limit(
            symbol=symbol,
            size=reentry_size,
            price=reentry_price,
            reduce_only=False
        )

        print(
            "REENTRY RESPONSE:",
            reentry_order
        )

        reentry_order_id = self._extract_order_id(
            reentry_order
        )

        state["reentry_order_id"] = (
            reentry_order_id
        )

        return order

    # =========================
    # TAKE PROFIT
    # =========================
    def _take_profit(self, signal, market_data):

        state = self.state_store.get()

        symbol = signal["symbol"]
        size = float(state.get("position_size") or 0)

        if size <= 0:
            return None

        order = self.exchange.sell_market(
            symbol=symbol,
            size=size
        )

        state["tp_order_id"] = self._extract_order_id(order)

        return order

    # =========================
    # REENTRY (FIXED)
    # =========================
    def _reentry(self, signal, market_data):

        state = self.state_store.get()

        symbol = signal["symbol"]

        base_size = float(state.get("position_size") or 0)
        multiplier = float(signal.get("size_multiplier", 1.0))

        new_size = int(base_size * multiplier)

        if new_size <= 0:
            return None

        # 🔴 CRITICAL FIX: price eerst bepalen
        reentry_price = float(signal["reentry_price"])

        state["reentry_pending"] = True

        # =========================
        # LIMIT BUY (REENTRY)
        # =========================
        order = self.exchange.buy_limit(
            symbol=symbol,
            size=new_size,
            price=reentry_price,
            reduce_only=False
        )

        state["reentry_order_id"] = self._extract_order_id(order)

        # level update
        state["level"] = signal.get(
            "next_level",
            state.get("level", 1) + 1
        )

        state["last_reentry_level"] = state["level"]
        state["pending_level"] = signal.get("next_level")

        # =========================
        # NEW TP DIRECT AFTER REENTRY
        # =========================
        entry_price = float(state.get("entry_price") or market_data["price"])
        level = int(state["level"])

        tp_pct = self.strategy.reentry_levels[level - 1]["take_profit_pct"]
        tp_price = entry_price * (1 + tp_pct)

        tp_order = self.exchange.sell_limit(
            symbol=symbol,
            size=new_size,
            price=tp_price,
            reduce_only=True
        )

        state["tp_order_id"] = self._extract_order_id(tp_order)

        state["reentry_pending"] = False

        return order

    # =========================
    # HELPERS (BELANGRIJK - FIX VOOR JE ERROR)
    # =========================
    def _extract_available_margin(self, balance):

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

    def _extract_order_id(self, order):

        if not order:
            return None

        if isinstance(order, dict):
            for k in ("order_id", "orderId", "uid", "id"):
                if k in order:
                    return str(order[k])

        return None
