def reconcile_orders(exchange, state_store):
    """
    Reconciles open orders against the current position.
    - If TP filled and position is flat: cancel old reentry and reset.
    - If reentry filled and position increased: cancel old TP, mark ladder rebuild.
    """

    state = state_store.get()

    orders_response = exchange.open_orders()
    open_positions_response = exchange.positions()

    live_ids = set()
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

    current_pos_size = 0.0
    current_pos = None

    if open_positions_response:
        open_positions = open_positions_response.get("openPositions", [])
        if open_positions:
            current_pos = open_positions[0]
            try:
                current_pos_size = float(current_pos.get("size") or 0)
            except Exception:
                current_pos_size = 0.0

    tp_id = state.get("tp_order_id")
    re_id = state.get("reentry_order_id")

    # -------------------------
    # TP FILLED → FLAT RESET
    # -------------------------
    if tp_id and str(tp_id) not in live_ids and current_pos_size <= 0:
        print("[RECONCILE] TP filled, position flat")

        if re_id:
            try:
                print("[RECONCILE] Cancelling old re-entry:", re_id)
                cancel_response = exchange.cancel_order(re_id)
                print("[RECONCILE] CANCEL RESPONSE:", cancel_response)
            except Exception as e:
                print("[RECONCILE] Cancel re-entry failed:", e)

        state_store.clear_position()
        state["tp_order_id"] = None
        state["reentry_order_id"] = None
        state["reentry_pending"] = False
        state["needs_new_ladder"] = False
        state["last_reentry_level"] = 0
        return state

    # -------------------------
    # REENTRY FILLED → REBUILD LADDER
    # -------------------------
    if re_id and str(re_id) not in live_ids and current_pos_size > 0:
        print("[RECONCILE] Re-entry filled, rebuilding ladder")

        if tp_id:
            try:
                print("[RECONCILE] Cancelling old TP:", tp_id)
                cancel_response = exchange.cancel_order(tp_id)
                print("[RECONCILE] TP CANCEL RESPONSE:", cancel_response)
            except Exception as e:
                print("[RECONCILE] Cancel TP failed:", e)

        state["tp_order_id"] = None
        state["reentry_order_id"] = None
        state["reentry_pending"] = False
        state["needs_new_ladder"] = True

        current_level = int(state.get("level") or 1)
        state["level"] = current_level + 1

        return state

    return state
