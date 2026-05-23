from bot.state.store import StateStore


def sync_state_from_exchange(exchange, state_store: StateStore):
    """
    Sync exchange truth → local state store.
    """
    positions_response = exchange.positions()

    if not positions_response:
        state_store.clear_position()
        return state_store.get()

    open_positions = positions_response.get("openPositions", [])

    state = state_store.get()
    symbol = state.get("symbol")

    matched = None

    for pos in open_positions:
        if pos.get("symbol") == symbol:
            matched = pos
            break

    if not matched:
        state_store.clear_position()
        return state_store.get()

    try:
        size = float(matched.get("size") or 0)
        entry_price = float(matched.get("price") or matched.get("entryPrice") or 0)
    except Exception:
        size = 0
        entry_price = 0

    if size > 0 and entry_price > 0:
        state_store.update_position_size(size)
        state["entry_price"] = entry_price
        state["symbol"] = matched.get("symbol")

        # Reset reentry lock once a real position exists
        state["reentry_pending"] = False

        if state.get("level") in (None, 0):
            state["level"] = 1
    else:
        state_store.clear_position()

    return state_store.get()
