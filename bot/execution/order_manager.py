class OrderManager:

    def __init__(self, exchange, state_store, strategy=None):
        self.exchange = exchange
        self.state_store = state_store
        self.strategy = strategy
        self.sizing = None  # injected sizing engine

    def set_sizing_engine(self, sizing_engine):
        self.sizing = sizing_engine

    # =========================
    # MAIN ENTRY POINT
    # =========================

    def execute(self, signal, market_data):

        if not signal:
            return None

        action = signal.get("action")

        if action == "OPEN_ENTRY":
            return self._open_entry(signal, market_data)

        if action == "TAKE_PROFIT":
            return self._take_profit(signal, market_data)

        return None

    # =========================
    # ENTRY
    # =========================

    def _open_entry(self, signal, market_data):

        symbol = signal["symbol"]
        price = float(market_data["price"])

        balance = self.exchange.balance()

        if not self.sizing:
            raise ValueError("Sizing engine not injected")

        # ✅ ALL sizing logic now delegated
        size = self.sizing.calculate_size(
            symbol=symbol,
            price=price,
            signal=signal,
            balance=balance
        )

        print("ENTRY SIZE:", size)

        if size <= 0:
            return None

        direction = getattr(self.strategy, "direction", "long")

        order = (
            self.exchange.sell_market if direction == "short"
            else self.exchange.buy_market
        )(
            symbol=symbol,
            size=size
        )

        self.state_store.set_entry(
            price=price,
            size=size,
            order_id=self._extract_order_id(order),
            symbol=symbol
        )

        self.create_ladder_orders(symbol, price, size, 1)

        return order

    # =========================
    # LADDER ORDERS
    # =========================

    def create_ladder_orders(self, symbol, entry_price, size, level):

        state = self.state_store.get(symbol)

        direction = getattr(self.strategy, "direction", "long")
        level_cfg = self.strategy.reentry_levels[level - 1]

        # -------------------------
        # TP PRICE
        # -------------------------

        tp_pct = float(level_cfg.get("take_profit_pct", 0.003))

        tp_price = (
            entry_price * (1 - tp_pct)
            if direction == "short"
            else entry_price * (1 + tp_pct)
        )

        tp_price = self._round_price(symbol, tp_price)

        tp_order = (
            self.exchange.buy_limit if direction == "short"
            else self.exchange.sell_limit
        )(
            symbol=symbol,
            size=size,
            price=tp_price,
            reduce_only=True
        )

        if tp_order.get("sendStatus", {}).get("status") == "placed":
            state["tp_order_id"] = self._extract_order_id(tp_order)
            state["tp_price"] = tp_price
            state["tp_size"] = size
        else:
            print("TP FAILED:", tp_order)

        # -------------------------
        # REENTRY PRICE
        # -------------------------

        drop_pct = float(level_cfg.get("drop_pct", 0.01))
        size_mult = float(level_cfg.get("size_multiplier", 1.0))

        reentry_price = (
            entry_price * (1 + drop_pct)
            if direction == "short"
            else entry_price * (1 - drop_pct)
        )

        reentry_price = self._round_price(symbol, reentry_price)

        reentry_size = int(size * size_mult)

        # TURBO SAFETY ONLY (no logic anywhere else!)
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

        if reentry_order.get("sendStatus", {}).get("status") == "placed":
            state["reentry_order_id"] = self._extract_order_id(reentry_order)
            state["reentry_price"] = reentry_price
            state["reentry_size"] = reentry_size
        else:
            print("REENTRY FAILED:", reentry_order)

    # =========================
    # TAKE PROFIT (optional)
    # =========================

    def _take_profit(self, signal, market_data):

        symbol = signal["symbol"]
        state = self.state_store.get(symbol)

        size = float(state.get("position_size") or 0)

        if size <= 0:
            return None

        direction = getattr(self.strategy, "direction", "long")

        order = (
            self.exchange.buy_market if direction == "short"
            else self.exchange.sell_market
        )(
            symbol=symbol,
            size=size
        )

        state["tp_order_id"] = self._extract_order_id(order)

        return order

    # =========================
    # PRICE SAFETY LAYER
    # =========================

    def _round_price(self, symbol, price):

        # BTC / XBT tick safety
        if "XBT" in symbol or "BTC" in symbol:
            return round(price, 1)

        # XRP precision
        if "XRP" in symbol:
            return round(price, 5)

        # alts default
        return round(price, 6)

    # =========================
    # HELPERS
    # =========================

    def _extract_order_id(self, order_response):

        if not order_response:
            return None

        if isinstance(order_response, dict):

            if "order_id" in order_response:
                return str(order_response["order_id"])

            send = order_response.get("sendStatus", {})
            return send.get("order_id")
