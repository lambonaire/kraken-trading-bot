def reconcile_orders(exchange, state_store):
    """
    Checks whether tracked orders still exist on exchange.
    Keeps store.py in sync with reality.
    """

    state = state_store.get()

    orders_response = exchange.open_orders()

    if not orders_response:
        return state

    open_orders = orders_response.get("openOrders", [])

    live_ids = set()

    for o in open_orders:
        oid = (
            o.get("order_id")
            or o.get("orderId")
            or o.get("uid")
        )
        if oid:
            live_ids.add(str(oid))

    # -------------------------
    # TP ORDER CHECK
    # -------------------------
    tp_id = state.get("tp_order_id")

    if tp_id and str(tp_id) not in live_ids:
        print("[RECONCILE] TP order no longer exists")
        state["tp_order_id"] = None

    # -------------------------
    # REENTRY ORDER CHECK
    # -------------------------
    re_id = state.get("reentry_order_id")

    if re_id and str(re_id) not in live_ids:
        print("[RECONCILE] Re-entry order no longer exists")
        state["reentry_order_id"] = None

    return state
