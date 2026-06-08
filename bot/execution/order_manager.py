import time


class OrderManager:
    def __init__(self, exchange, state_store, strategy, sizing, market_specs=None):
        self.exchange = exchange
        self.state_store = state_store
        self.strategy = strategy
        self.sizing = sizing
        self.market_specs = market_specs

        from bot.execution.ladder_reconciler import LadderReconciler
        self.reconciler = LadderReconciler(
            exchange,
            state_store,
            strategy,
            market_specs=market_specs
        )

    def execute(self, signal, market_data):
        print("[ORDER MANAGER] signal =", signal)
        print("[ORDER MANAGER] market_data =", market_data)

        if not signal:
            print("[ORDER MANAGER] no signal")
            return None

        symbol = signal.get("symbol")
        state = self.state_store.get(symbol) or {}

        now = time.time()

        # Hard safety: block entry during cooldown after a flat transition
        if now < float(state.get("flat_cooldown_until", 0) or 0):
            print("[SAFETY] flat cooldown active -> block entry")
            return None

        # Hard safety: block if an entry is already in flight
        if state.get("entry_order_pending", False):
            print("[SAFETY] entry already pending -> block entry")
            return None

        # HARD SAFETY
        if signal.get("action") == "OPEN_ENTRY":
            if float(state.get("position_size", 0) or 0) > 0:
                print("[SAFETY] position already open -> block entry")
                return None

            if state.get("ladder_active"):
                print("[SAFETY] ladder active -> block entry")
                return None

            if state.get("needs_new_ladder") is False:
                print("[SAFETY] ladder not reset -> block entry")
                return None

        if not market_data:
            print("[ORDER MANAGER] missing market_data")
            return None

        price = market_data.get("price")
        print("[ORDER MANAGER] price =", price)

        if price is None:
            print("[ORDER MANAGER] missing price -> skip")
            return None

        # =========================
        # ENTRY LOGIC
        # =========================
        if signal.get("action") == "OPEN_ENTRY":
            try:
                state["entry_order_pending"] = True

                print("[ORDER MANAGER] fetching balance")
                balance = self.exchange.get_account_balance()
                print("[ORDER MANAGER] balance =", balance)

                print("[ORDER MANAGER] calculating size")
                size = self.sizing.calculate_size(
                    symbol=symbol,
                    price=price,
                    signal=signal,
                    balance=balance,
                )
                print("[ORDER MANAGER] size =", size)

                if size <= 0:
                    print("[ORDER] skip entry size 0")
                    state["entry_order_pending"] = False
                    return None

                print(
                    "[ORDER MANAGER] sending entry order",
                    signal.get("side"),
                    size,
                )

                order = self.exchange.place_market_order(
                    symbol=symbol,
                    side=signal.get("side"),
                    size=size,
                )

                print("[ORDER MANAGER] order response =", order)

                if not order:
                    print("[ORDER MANAGER] entry order not placed")
                    state["entry_order_pending"] = False
                    return None

                if order.get("sendStatus", {}).get("status") != "placed":
                    print("[ORDER MANAGER] entry order not placed")
                    state["entry_order_pending"] = False
                    return order

                order_id = order["sendStatus"]["order_id"]

                # Extract actual fill(s) from Kraken response
                events = order["sendStatus"].get("orderEvents", []) or []
                fills = [e for e in events if e.get("type") == "EXECUTION"]

                total_amount = 0.0
                weighted_price_sum = 0.0

                for fill in fills:
                    fill_price = float(fill.get("price") or 0)
                    fill_amount = float(fill.get("amount") or 0)

                    if fill_price > 0 and fill_amount > 0:
                        total_amount += fill_amount
                        weighted_price_sum += fill_price * fill_amount

                if total_amount > 0:
                    fill_price = weighted_price_sum / total_amount
                    fill_size = total_amount
                else:
                    fill_price = float(price)
                    fill_size = float(size)

                self.state_store.set_entry(
                    symbol=symbol,
                    price=fill_price,
                    size=fill_size,
                    order_id=order_id,
                )

                state = self.state_store.get(symbol) or {}
                state["needs_new_ladder"] = False
                state["ladder_active"] = True
                state["reentry_pending"] = False
                state["level"] = 1
                state["last_reconciled_level"] = 0
                state["entry_order_pending"] = False

                print(
                    "[ORDER MANAGER] entry filled; building ladder "
                    f"fill_price={fill_price} fill_size={fill_size} order_id={order_id}"
                )

                # Build TP + reentry immediately from the confirmed fill
                self.reconciler.reconcile(
                    symbol=symbol,
                    entry_price=fill_price,
                    position_size=fill_size,
                    level=1,
                )

                state["last_reconciled_position_size"] = fill_size

                return order

            except Exception:
                state["entry_order_pending"] = False
                raise

        return None
