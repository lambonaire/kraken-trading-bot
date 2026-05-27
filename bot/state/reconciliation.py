def reconcile_orders(exchange, state_store, symbol):
    """
    Reconciles open orders against the current position.
    Kraken is truth, state is follower.
    """

    state = state_store.get(symbol)

    orders_response = exchange.open_orders()
    open_positions_response = exchange.positions()

    live_ids = set()

    # =========================
    # OPEN ORDERS
    # =========================

    open_orders = []

    if orders_response:
        open_orders = orders_response.get("openOrders", [])

        for o in open_orders:
            oid = (
                o.get("order_id")
                or o.get("orderId")
                or o.get("uid")
                or o.get("id")
            )
            if oid:
                live_ids.add(str(oid))

    # =========================
    # MATCH CURRENT POSITION FOR THIS SYMBOL
    # =========================

    current_pos_size = 0.0
    current_pos = None

    if open_positions_response:
        open_positions = open_positions_response.get("openPositions", [])

        for pos in open_positions:
            pos_symbol = (
                pos.get("symbol")
                or pos.get("marketSymbol")
                or pos.get("instrument")
                or pos.get("contract")
            )

            if pos_symbol == symbol:
                current_pos = pos
                break

        if current_pos:
            try:
                current_pos_size = float(current_pos.get("size") or 0)
            except Exception:
                current_pos_size = 0.0

    tp_id = state.get("tp_order_id")
    re_id = state.get("reentry_order_id")

    # =========================
    # FLAT POSITION -> HARD CLEAN
    # =========================

    if current_pos_size <= 0:
        print("[RECONCILE] Position is flat -> cleaning state for", symbol)

        if tp_id:
            try:
                print("[RECONCILE] Cancelling TP:", tp_id)
                exchange.cancel_order(tp_id)
            except Exception as e:
                print("[RECONCILE] TP cancel failed:", e)

        if re_id:
            try:
                print("[RECONCILE] Cancelling REENTRY:", re_id)
                exchange.cancel_order(re_id)
            except Exception as e:
                print("[RECONCILE] REENTRY cancel failed:", e)

        state_store.clear_position(symbol)
        return state_store.get(symbol)

    # =========================
    # TP FILLED -> RESET
    # =========================

    if tp_id and str(tp_id) not in live_ids and current_pos_size <= 0:
        print("[RECONCILE] TP filled for", symbol)
        state_store.clear_position(symbol)
        return state_store.get(symbol)

    # =========================
    # REENTRY FILLED -> REBUILD LADDER
    # =========================

    if re_id and str(re_id) not in live_ids and current_pos_size > 0:
        print("[RECONCILE] Re-entry filled -> rebuild ladder for", symbol)

        if tp_id:
            try:
                print("[RECONCILE] Cancelling old TP:", tp_id)
                exchange.cancel_order(tp_id)
            except Exception as e:
                print("[RECONCILE] TP cancel failed:", e)

        state["tp_order_id"] = None
        state["tp_price"] = None
        state["tp_size"] = None

        state["reentry_order_id"] = None
        state["reentry_price"] = None
        state["reentry_size"] = None

        state["reentry_pending"] = False
        state["needs_new_ladder"] = True

        state["level"] = int(state.get("level") or 1) + 1

        return state

    return state
