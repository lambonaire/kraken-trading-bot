from bot.execution.ladder_reconciler import LadderReconciler


def reconcile_orders(exchange, state_store, strategy, symbol):
    """
    Reconciles open orders against the current position.

    Rules:
    - flat position -> clear state and cancel ladder orders
    - position size changed -> rebuild ladder
    - TP/reentry missing -> repair ladder
    - true reentry fill -> increment level and rebuild ladder
    """

    state = state_store.get(symbol)

    orders_response = exchange.open_orders()
    positions_response = exchange.positions()

    live_ids = set()

    # =========================
    # OPEN ORDERS
    # =========================
    open_orders = []
    if orders_response:
        open_orders = orders_response.get("openOrders", []) or []

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
    current_pos = None
    current_pos_size = 0.0
    current_pos_entry_price = None

    if positions_response:
        open_positions = positions_response.get("openPositions", []) or []

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

            raw_entry = (
                current_pos.get("entryPrice")
                or current_pos.get("price")
                or current_pos.get("avgEntryPrice")
            )

            try:
                current_pos_entry_price = float(raw_entry) if raw_entry else None
            except Exception:
                current_pos_entry_price = None

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

    prev_size = float(state.get("last_reconciled_position_size") or 0.0)
    size_changed = abs(current_pos_size - prev_size) > 1e-9

    tp_missing = (not tp_id) or (str(tp_id) not in live_ids)
    re_missing = (not re_id) or (str(re_id) not in live_ids)

    entry_price = current_pos_entry_price or state.get("entry_price")
    if entry_price is None:
        print("[RECONCILE] missing entry_price -> skip rebuild for", symbol)
        state["position_size"] = current_pos_size
        state["last_reconciled_position_size"] = current_pos_size
        return state

    level = int(state.get("level") or 1)

    # True reentry fill heuristic:
    # reentry order vanished AND position size increased vs last reconciliation

    print(
        "[DEBUG LEVEL]",
        "level=", level,
        "prev_size=", prev_size,
        "current_size=", current_pos_size,
        "re_id=", re_id,
        "re_exists=", str(re_id) in live_ids if re_id else False,
    )

    if re_id and str(re_id) not in live_ids and current_pos_size > prev_size + 1e-9:
        print("[RECONCILE] Re-entry filled -> rebuild ladder for", symbol)
        level = min(level + 1, int(getattr(strategy, "max_level", level)))
        state["level"] = level
        state["needs_new_ladder"] = True
        state["ladder_active"] = True
        state["reentry_pending"] = False

        reconciler = LadderReconciler(exchange, state_store, strategy)
        reconciler.reconcile(
            symbol=symbol,
            entry_price=entry_price,
            position_size=current_pos_size,
            level=level,
        )

        state["last_reconciled_position_size"] = current_pos_size
        state["last_reconciled_level"] = level
        return state

    # Manual add / TP missing / reentry missing => repair at same level
    if size_changed or tp_missing or re_missing:
        print("[RECONCILE] Position changed or ladder incomplete -> rebuild ladder for", symbol)

        state["position_size"] = current_pos_size
        state["entry_price"] = entry_price
        state["level"] = level
        state["needs_new_ladder"] = True
        state["ladder_active"] = True
        state["reentry_pending"] = False

        reconciler = LadderReconciler(exchange, state_store, strategy)
        reconciler.reconcile(
            symbol=symbol,
            entry_price=entry_price,
            position_size=current_pos_size,
            level=level,
        )

        state["last_reconciled_position_size"] = current_pos_size
        state["last_reconciled_level"] = level
        return state

    state["last_reconciled_position_size"] = current_pos_size
    state["last_reconciled_level"] = level
    return state
