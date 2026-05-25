from bot.state.store import StateStore


def cancel_all_ladder_orders(exchange, state):

    tp_order_id = state.get("tp_order_id")

    if tp_order_id:

        try:
            print("[SYNC] Cancelling TP:", tp_order_id)
            exchange.cancel_order(tp_order_id)
        except Exception as e:
            print("[SYNC] TP cancel failed:", e)

    reentry_order_id = state.get("reentry_order_id")

    if reentry_order_id:

        try:
            print("[SYNC] Cancelling REENTRY:", reentry_order_id)
            exchange.cancel_order(reentry_order_id)
        except Exception as e:
            print("[SYNC] Reentry cancel failed:", e)


def sync_state_from_exchange(exchange, state_store: StateStore):

    positions_response = exchange.positions()

    state = state_store.get()

    # =====================================
    # NO POSITIONS AT ALL
    # =====================================

    if not positions_response:

        print("[SYNC] No open positions")

        cancel_all_ladder_orders(
            exchange,
            state
        )

        state_store.clear_position()

        return state_store.get()

    open_positions = positions_response.get(
        "openPositions",
        []
    )

    symbol = state.get("symbol")

    matched = None

    for pos in open_positions:

        if pos.get("symbol") == symbol:
            matched = pos
            break

    # =====================================
    # NO MATCHING POSITION
    # =====================================

    if not matched:

        print("[SYNC] No matching position found")

        cancel_all_ladder_orders(
            exchange,
            state
        )

        state_store.clear_position()

        return state_store.get()

    # =====================================
    # EXTRACT POSITION
    # =====================================

    try:

        size = float(
            matched.get("size") or 0
        )

        entry_price = float(
            matched.get("price")
            or matched.get("entryPrice")
            or 0
        )

    except Exception:

        size = 0
        entry_price = 0

    # =====================================
    # VALID POSITION
    # =====================================

    if size > 0 and entry_price > 0:

        old_size = float(
            state.get("position_size") or 0
        )

        # =====================================
        # DETECT POSITION SIZE CHANGE
        # =====================================

        if old_size > 0 and size != old_size:

            print(
                "[SYNC] POSITION SIZE CHANGED:",
                old_size,
                "->",
                size
            )

            state["needs_new_ladder"] = True

        state_store.update_position_size(size)

        state["entry_price"] = entry_price

        state["symbol"] = matched.get("symbol")

        if state.get("level") in (None, 0):
            state["level"] = 1

        print(
            "[SYNC] Position synced:",
            size,
            entry_price
        )

    else:

        print("[SYNC] Invalid position")

        cancel_all_ladder_orders(
            exchange,
            state
        )

        state_store.clear_position()

    return state_store.get()
