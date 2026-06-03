class OrderManager:

    def __init__(self, exchange, state_store, strategy, sizing):
        self.exchange = exchange
        self.state_store = state_store
        self.strategy = strategy
        self.sizing = sizing

        from bot.execution.ladder_reconciler import LadderReconciler
        self.reconciler = LadderReconciler(exchange, state_store, strategy)

    def execute(self, signal, market_data):

        if not signal:
            return None

        symbol = signal["symbol"]

        state = self.state_store.get(symbol)

        price = market_data["price"]

        # =========================
        # ENTRY LOGIC
        # =========================
        if signal["action"] == "OPEN_ENTRY":

            balance = self.exchange.get_account_balance()

            size = self.sizing.calculate_size(
                symbol=symbol,
                price=price,
                signal=signal,
                balance=balance
            )

            if size <= 0:
                print("[ORDER] skip entry size 0")
                return None

            order = self.exchange.place_market_order(
                symbol=symbol,
                side=signal["side"],
                size=size
            )

            if order and order.get("sendStatus", {}).get("status") == "placed":
                order_id = order["sendStatus"]["order_id"]

                self.state_store.set_entry(
                    symbol=symbol,
                    price=price,
                    size=size,
                    order_id=order_id
                )

                # trigger ladder after entry
                state["needs_new_ladder"] = True

                self.reconciler.reconcile(
                    symbol=symbol,
                    entry_price=price,
                    position_size=size,
                    level=1
                )

                return order

        return None
