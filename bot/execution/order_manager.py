class OrderManager:
    def __init__(self, exchange, state_store):
        self.exchange = exchange
        self.state_store = state_store

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

    # -------------------------
    # ENTRY
    # -------------------------
    def _open_entry(self, signal, market_data):
        symbol = signal["symbol"]
        margin_fraction = float(signal["margin_fraction"])

        balance = self.exchange.balance()

        available_margin = self._extract_available_margin(balance)
        if available_margin is None:
            raise ValueError("Could not extract available margin")

        price = float(market_data["price"])

        usd_size = available_margin * margin_fraction
        size = usd_size / price

        order = self.exchange.buy_market(
            symbol=symbol,
            size=size
        )

        order_id = self._extract_order_id(order)

        self.state_store.set_entry(
            price=price,
            size=size,
            order_id=order_id,
            symbol=symbol
        )

        return order

    # -------------------------
    # TAKE PROFIT
    # -------------------------
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

        order_id = self._extract_order_id(order)
        state["tp_order_id"] = order_id

        return order

    # -------------------------
    # RE-ENTRY
    # -------------------------
    def _reentry(self, signal, market_data):
        state = self.state_store.get()

        symbol = signal["symbol"]

        base_size = float(state.get("position_size") or 0)
        multiplier = float(signal.get("size_multiplier", 1.0))

        new_size = base_size * multiplier

        order = self.exchange.buy_market(
            symbol=symbol,
            size=new_size
        )

        order_id = self._extract_order_id(order)
        state["reentry_order_id"] = order_id


        # PENDING REENTRY STATE
        # -------------------------
        state["reentry_pending"] = True
        state["pending_level"] = signal.get("next_level")

        # Prevent duplicate trigger spam
        state["last_reentry_level"] = signal.get(
            "level",
            state.get("level", 1)
        )

        return order

    # -------------------------
    # HELPERS
    # -------------------------
    def _extract_available_margin(self, balance_response):
        if not balance_response:
            return None

        if isinstance(balance_response, dict):
            for key in ("availableMargin", "available_margin", "available", "freeMargin"):
                value = balance_response.get(key)
                if value is not None:
                    try:
                        return float(value)
                    except:
                        pass

            accounts = balance_response.get("accounts", {})
            if isinstance(accounts, dict):
                flex = accounts.get("flex", {})
                if isinstance(flex, dict):
                    for key in ("availableMargin", "available_margin"):
                        value = flex.get(key)
                        if value is not None:
                            try:
                                return float(value)
                            except:
                                pass

        return None

    def _extract_order_id(self, order_response):
        if not order_response:
            return None

        if isinstance(order_response, dict):
            for key in ("order_id", "orderId", "uid", "id"):
                if key in order_response:
                    return str(order_response[key])

        return None
