class OrderManager:

    def __init__(self, exchange, state_store, strategy=None, sizing=None):
        self.exchange = exchange
        self.state_store = state_store
        self.strategy = strategy
        self.sizing = sizing

    # ==================================================
    # MAIN EXECUTION
    # ==================================================

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

        return None

    # ==================================================
    # OPEN ENTRY
    # ==================================================

    def _open_entry(self, signal, market_data):

        symbol = signal["symbol"]
        price = float(market_data["price"])

        if not self.sizing:
            raise ValueError("Sizing engine not injected")

        balance = self.exchange.balance()

        size = self.sizing.calculate_size(
            symbol=symbol,
            price=price,
            signal=signal,
            balance=balance
        )

        print("[ENTRY SIZE]", size)

        if size <= 0:
            return None

        direction = getattr(self.strategy, "direction", "long")

        # -------------------------
        # MARKET ENTRY
        # -------------------------

        order = (
            self.exchange.sell_market
            if direction == "short"
            else self.exchange.buy_market
        )(
            symbol=symbol,
            size=size
        )

        print("[ENTRY RESPONSE]", order)

        order_id = self._extract_order_id(order)

        # -------------------------
        # STATE UPDATE
        # -------------------------

        self.state_store.set_entry(
            symbol=symbol,
            price=price,
            size=size,
            order_id=order_id
        )

        self.state_store.set_level(
            symbol,
            1
        )

        # -------------------------
        # CREATE LADDER
        # -------------------------

        self.create_ladder_orders(
            symbol=symbol,
            entry_price=price,
            size=size,
            level=1
        )

        return order

    # ==================================================
    # CREATE LADDER ORDERS
    # ==================================================

    def create_ladder_orders(
        self,
        symbol,
        entry_price,
        size,
        level
    ):

        state = self.state_store.get(symbol)

        direction = getattr(
            self.strategy,
            "direction",
            "long"
        )

        cfg = self.strategy.reentry_levels[
            level - 1
        ]

        # -------------------------
        # CANCEL OLD ORDERS
        # -------------------------

        for key in [
            "tp_order_id",
            "reentry_order_id"
        ]:

            old_order_id = state.get(key)

            if old_order_id:

                try:
                    self.exchange.cancel_order(
                        old_order_id
                    )

                    print(
                        "[CANCELLED]",
                        old_order_id
                    )

                except Exception as e:

                    print(
                        "[CANCEL ERROR]",
                        e
                    )

        # ==================================================
        # TAKE PROFIT
        # ==================================================

        tp_pct = float(
            cfg.get(
                "take_profit_pct",
                0.003
            )
        )

        tp_price = (
            entry_price * (1 - tp_pct)
            if direction == "short"
            else entry_price * (1 + tp_pct)
        )

        tp_price = self._round_price(
            symbol,
            tp_price
        )

        tp_order = (
            self.exchange.buy_limit
            if direction == "short"
            else self.exchange.sell_limit
        )(
            symbol=symbol,
            size=size,
            price=tp_price,
            reduce_only=True
        )

        print("[TP RESPONSE]", tp_order)

        tp_status = (
            tp_order
            .get("sendStatus", {})
            .get("status")
        )

        if tp_status == "placed":

            self.state_store.set_tp(
                symbol=symbol,
                order_id=self._extract_order_id(tp_order),
                price=tp_price,
                size=size
            )

        else:

            print(
                "[TP FAILED]",
                tp_status
            )

        # ==================================================
        # MAX LEVEL STOP
        # ==================================================

        if level >= self.strategy.max_level:

            print("[MAX LEVEL REACHED]")

            self.state_store.set_reentry(
                symbol=symbol,
                order_id=None,
                price=None,
                size=None
            )

            return

        # ==================================================
        # REENTRY
        # ==================================================

        drop_pct = float(
            cfg.get(
                "drop_pct",
                0.01
            )
        )

        size_mult = float(
            cfg.get(
                "size_multiplier",
                1.0
            )
        )

        reentry_price = (
            entry_price * (1 + drop_pct)
            if direction == "short"
            else entry_price * (1 - drop_pct)
        )

        reentry_price = self._round_price(
            symbol,
            reentry_price
        )

        reentry_size = int(
            size * size_mult
        )

        # -------------------------
        # TURBO SAFE
        # -------------------------

        if "TURBO" in symbol:

            reentry_size = (
                int(reentry_size / 100) * 100
            )

            if reentry_size <= 0:
                reentry_size = 100

        reentry_order = (
            self.exchange.sell_limit
            if direction == "short"
            else self.exchange.buy_limit
        )(
            symbol=symbol,
            size=reentry_size,
            price=reentry_price,
            reduce_only=False
        )

        print(
            "[REENTRY RESPONSE]",
            reentry_order
        )

        reentry_status = (
            reentry_order
            .get("sendStatus", {})
            .get("status")
        )

        if reentry_status == "placed":

            self.state_store.set_reentry(
                symbol=symbol,
                order_id=self._extract_order_id(
                    reentry_order
                ),
                price=reentry_price,
                size=reentry_size
            )

        else:

            print(
                "[REENTRY FAILED]",
                reentry_status
            )

    # ==================================================
    # TAKE PROFIT EXECUTION
    # ==================================================

    def _take_profit(
        self,
        signal,
        market_data
    ):

        symbol = signal["symbol"]

        state = self.state_store.get(symbol)

        size = float(
            state.get(
                "position_size"
            ) or 0
        )

        if size <= 0:
            return None

        direction = getattr(
            self.strategy,
            "direction",
            "long"
        )

        order = (
            self.exchange.buy_market
            if direction == "short"
            else self.exchange.sell_market
        )(
            symbol=symbol,
            size=size
        )

        print(
            "[TP MARKET RESPONSE]",
            order
        )

        self.state_store.clear_position(
            symbol
        )

        return order

    # ==================================================
    # REENTRY EXECUTION
    # ==================================================

    def _reentry(
        self,
        signal,
        market_data
    ):

        symbol = signal["symbol"]

        state = self.state_store.get(symbol)

        current_level = int(
            state.get("level") or 1
        )

        next_level = current_level + 1

        self.state_store.set_level(
            symbol,
            next_level
        )

        self.state_store.trigger_ladder_rebuild(
            symbol
        )

        print(
            "[REENTRY LEVEL]",
            next_level
        )

        return True

    # ==================================================
    # PRICE ROUNDING
    # ==================================================

    def _round_price(
        self,
        symbol,
        price
    ):

        if "XBT" in symbol:
            return round(price, 1)

        if "ETH" in symbol:
            return round(price, 2)

        if "XRP" in symbol:
            return round(price, 5)

        if "DOGE" in symbol:
            return round(price, 5)

        if "TURBO" in symbol:
            return round(price, 6)

        return round(price, 6)

    # ==================================================
    # ORDER ID EXTRACTION
    # ==================================================

    def _extract_order_id(
        self,
        order_response
    ):

        if not order_response:
            return None

        if isinstance(order_response, dict):

            if order_response.get("order_id"):
                return str(
                    order_response["order_id"]
                )

            send = order_response.get(
                "sendStatus",
                {}
            )

            if send.get("order_id"):
                return str(
                    send["order_id"]
                )

        return None
