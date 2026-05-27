def sync_state_from_exchange(exchange, state_store, symbol):
    """
    Sync ONLY the given symbol from exchange into local state.
    Kraken is the source of truth.
    """

    state = state_store.get(symbol)

    positions_response = exchange.positions()

    # If the API fails or returns nothing, do not aggressively wipe state here.
    if not positions_response:
        return state

    open_positions = positions_response.get("openPositions", [])

    # =========================
    # FIND MATCHING POSITION
    # =========================

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
    # NO POSITION FOUND -> HARD RESET LOCAL STATE
    # =========================

    if not current_pos:
        print("[SYNC] No matching position found for", symbol)

        state_store.clear_position(symbol)
        return state_store.get(symbol)

    # =========================
    # UPDATE STATE SAFELY
    # =========================

    try:
        size = float(current_pos.get("size") or 0)
    except Exception:
        size = 0.0

    raw_entry = current_pos.get("entryPrice")

    try:
        entry_price = float(raw_entry) if raw_entry not in (None, "", 0, "0") else None
    except Exception:
        entry_price = None

    state["symbol"] = symbol
    state["position_size"] = size

    # Only overwrite if Kraken gives a real positive entry price
    if entry_price and entry_price > 0:
        state["entry_price"] = entry_price

    if size > 0 and state.get("entry_price"):
        state["needs_new_ladder"] = False

    return state
