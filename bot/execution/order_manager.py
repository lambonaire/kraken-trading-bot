class OrderManager:
    def __init__(self, exchange):
        self.exchange = exchange

    def execute(self, signal, state):
        if signal is None:
            return

        action = signal.get("action")

        if action == "OPEN_ENTRY":
            return self._open_entry(signal, state)

        if action == "TAKE_PROFIT":
            return self._take_profit(signal, state)

        if action == "REENTRY":
            return self._reentry(signal, state)

        raise ValueError(f"Unknown action: {action}")

    def _open_entry(self, signal, state):
        symbol = signal["symbol"]
        margin_fraction = signal["margin_fraction"]

        # voorbeeld: jij bepaalt size later preciezer via balance
        order = self.exchange.buy(
            symbol=symbol,
            size=margin_fraction
        )

        return order

    def _take_profit(self, signal, state):
        symbol = signal["symbol"]

        # sluit volledige positie
        order = self.exchange.sell(
            symbol=symbol,
            size=state["position_size"]
        )

        return order

    def _reentry(self, signal, state):
        symbol = signal["symbol"]

        base_size = state["position_size"]
        multiplier = signal.get("size_multiplier", 1.0)

        new_size = base_size * multiplier

        order = self.exchange.buy(
            symbol=symbol,
            size=new_size
        )

        return order
