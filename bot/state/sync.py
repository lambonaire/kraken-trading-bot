def sync_state_from_exchange(exchange, state_store, symbol):

    positions = exchange.positions()
    open_positions = positions.get("openPositions", []) if positions else []

    if not open_positions:
        print("[SYNC] No matching position found")
        state_store.clear_position(symbol)
        return

    # neem eerste positie
    pos = open_positions[0]

    try:
        size = float(pos.get("size") or 0)
        entry_price = float(pos.get("entryPrice") or 0)
    except:
        size = 0
        entry_price = 0

    if size <= 0:
        state_store.clear_position(symbol)
        return

    # update state per symbol
    state = state_store.get(symbol)

    state["symbol"] = symbol
    state["position_size"] = size
    state["entry_price"] = entry_price

    state_store.states[symbol] = state
