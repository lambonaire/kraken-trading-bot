def sync_state_from_exchange(exchange, state_store, symbol):

    positions = exchange.get_open_positions()

    open_positions = positions.get("openPositions", []) if positions else []

    matching_position = None

    for pos in open_positions:

        if pos.get("symbol") == symbol:
            matching_position = pos
            break

    # =========================
    # NO POSITION
    # =========================

    if not matching_position:

        print("[SYNC] No matching position found")

        state_store.clear_position(symbol)

        return

    # =========================
    # POSITION FOUND
    # =========================

    size = float(matching_position.get("size") or 0)
    entry_price = float(matching_position.get("entryPrice") or 0)

    state = state_store.get(symbol)

    state["symbol"] = symbol
    state["position_size"] = size
    state["entry_price"] = entry_price
