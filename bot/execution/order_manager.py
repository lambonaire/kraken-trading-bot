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

    def create_ladder_orders(self, symbol, entry_price, size, level):
        state = self.state_store.get()

        old_tp = state.get("tp_order_id")
        if old_tp:
            try:
                print("CANCELLING OLD TP:", old_tp)
                self.exchange.cancel_order(old_tp)
            except Exception as e:
                print("TP CANCEL ERROR:", e)

        old_reentry = state.get("reentry_order_id")
        if old_reentry:
            try:
                print("CANCELLING OLD REENTRY:", old_reentry)
                self.exchange.cancel_order(old_reentry)
            except Exception as e:
                print("REENTRY CANCEL ERROR:", e)

        level_cfg = self.strategy.reentry_levels[level - 1]

        tp_pct = float(level_cfg.get("take_profit_pct", 0.003))
        drop_pct = float(level_cfg.get("drop_pct", 0.01))
        size_multiplier = float(level_cfg.get("size_multiplier", 1.0))

        tp_price = entry_price * (1 + tp_pct)
        print("NEW TP:", tp_price)

        tp_order = self.exchange.sell_limit(
            symbol=symbol,
            size=size,
            price=tp_price,
            reduce_only=True
        )
        print("NEW TP RESPONSE:", tp_order)
        state["tp_order_id"] = self._extract_order_id(tp_order)

        if level < self.strategy.max_level:
            reentry_price = entry_price * (1 - drop_pct)
            reentry_size = int(size * size_multiplier)
            if reentry_size <= 0:
                reentry_size = 1

            print("NEW REENTRY:", reentry_price, reentry_size)

            reentry_order = self.exchange.buy_limit(
                symbol=symbol,
                size=reentry_size,
                price=reentry_price,
                reduce_only=False
            )
            print("NEW REENTRY RESPONSE:", reentry_order)
            state["reentry_order_id"] = self._extract_order_id(reentry_order)
        else:
            state["reentry_order_id"] = None

        state["reentry_pending"] = False
        state["needs_new_ladder"] = False

    # =========================
    # CREATE LADDER ORDERS
    # =========================

    def create_ladder_orders(
        self,
        symbol,
        entry_price,
        size,
        level
    ):

        state = self.state_store.get()

        # -------------------------
        # CANCEL OLD TP
        # -------------------------

        old_tp = state.get("tp_order_id")

        if old_tp:

            try:

                print("CANCELLING OLD TP")

                self.exchange.cancel_order(old_tp)

            except Exception as e:

                print("TP CANCEL ERROR:", e)

        # -------------------------
        # LEVEL CONFIG
        # -------------------------

        level_cfg = self.strategy.reentry_levels[
            level - 1
        ]

        # -------------------------
        # CREATE TP
        # -------------------------

        tp_pct = float(
            level_cfg.get(
                "take_profit_pct",
                0.003
            )
        )

        tp_price = entry_price * (
            1 + tp_pct
        )

        print("NEW TP:", tp_price)

        tp_order = self.exchange.sell_limit(
            symbol=symbol,
            size=size,
            price=tp_price,
            reduce_only=True
        )

        print("NEW TP RESPONSE:", tp_order)

        tp_order_id = self._extract_order_id(
            tp_order
        )

        state["tp_order_id"] = tp_order_id

        # -------------------------
        # MAX LEVEL STOP
        # -------------------------

        if level >= self.strategy.max_level:

            print("MAX LEVEL REACHED")

            return

        # -------------------------
        # CREATE REENTRY
        # -------------------------

        drop_pct = float(
            level_cfg.get(
                "drop_pct",
                0.01
            )
        )

        size_multiplier = float(
            level_cfg.get(
                "size_multiplier",
                1.0
            )
        )

        reentry_price = entry_price * (
            1 - drop_pct
        )

        reentry_size = int(
            size * size_multiplier
        )

        if reentry_size <= 0:
            reentry_size = 1

        print(
            "NEW REENTRY:",
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
            "NEW REENTRY RESPONSE:",
            reentry_order
        )

        reentry_order_id = self._extract_order_id(
            reentry_order
        )

        state["reentry_order_id"] = (
            reentry_order_id
        )

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

        # =========================
        # CREATE FIRST LADDER
        # =========================

        self.create_ladder_orders(
            symbol=symbol,
            entry_price=price,
            size=size,
            level=1
        )

        return order

    # =========================
    # TAKE PROFIT
    # =========================

    def _take_profit(self, signal, market_data):

        state = self.state_store.get()

        symbol = signal["symbol"]

        size = float(
            state.get("position_size") or 0
        )

        if size <= 0:
            return None

        order = self.exchange.sell_market(
            symbol=symbol,
            size=size
        )

        state["tp_order_id"] = (
            self._extract_order_id(order)
        )

        return order

    # =========================
    # REENTRY
    # =========================

    def _reentry(self, signal, market_data):

        print("REENTRY DISABLED")

        return None

    # =========================
    # HELPERS
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

    def _extract_order_id(self, order_response):

        if not order_response:
            return None

        # =========================
        # TOP LEVEL
        # =========================

        if isinstance(order_response, dict):

            for key in (
                "order_id",
                "orderId",
                "uid",
                "id"
            ):

                if (
                    key in order_response
                    and order_response[key]
                ):
                    return str(order_response[key])

            # =========================
            # KRAKEN sendStatus
            # =========================

            send_status = order_response.get(
                "sendStatus"
            )

            if isinstance(send_status, dict):

                for key in (
                    "order_id",
                    "orderId",
                    "uid",
                    "id"
                ):

                    if (
                        key in send_status
                        and send_status[key]
                    ):
                        return str(send_status[key])

                # =========================
                # orderEvents fallback
                # =========================

                order_events = send_status.get(
                    "orderEvents",
                    []
                )

                if (
                    isinstance(order_events, list)
                    and order_events
                ):

                    first_event = order_events[0]

                    if isinstance(first_event, dict):

                        order_data = first_event.get(
                            "order"
                        )

                        if isinstance(order_data, dict):

                            for key in (
                                "order_id",
                                "orderId",
                                "uid",
                                "id"
                            ):

                                if (
                                    key in order_data
                                    and order_data[key]
                                ):
                                    return str(
                                        order_data[key]
                                    )

        return None
