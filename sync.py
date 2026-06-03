def sync_state_from_exchange(exchange, state_store, symbol):

    state = state_store.get(symbol)

    positions_response = exchange.positions()

    if not positions_response:
        return state

    open_positions = positions_response.get("openPositions", [])

    current_pos = None

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

    # =========================
    # SOFT STATE RESET ONLY
    # =========================
    if not current_pos:
        print("[SYNC] no position -> soft reset")

        state["position_size"] = 0.0
        state["entry_price"] = None
        state["level"] = 1

        # DO NOT TOUCH LADDER FLAGS
        return state

    # =========================
    # UPDATE FROM EXCHANGE
    # =========================
    try:
        size = float(current_pos.get("size") or 0)
    except:
        size = 0.0

    try:
        entry_price = float(current_pos.get("entryPrice"))
    except:
        entry_price = None

    state["position_size"] = size

    if entry_price and entry_price > 0:
        state["entry_price"] = entry_price

    # IMPORTANT: ladder state stays intact
    return state
