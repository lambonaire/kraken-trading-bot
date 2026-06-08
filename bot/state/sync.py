def sync_state_from_exchange(exchange, state_store, symbol):

    state = state_store.get(symbol)

    positions_response = exchange.positions()

    if not positions_response:
        print("[SYNC] positions() returned nothing")
        return state

    open_positions = positions_response.get(
        "openPositions",
        []
    )

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

    # ==================================================
    # POSITION NOT FOUND
    # ==================================================

    if not current_pos:

        state["missing_position_count"] = (
            int(state.get("missing_position_count") or 0)
            + 1
        )

        print(
            f"[SYNC] no position detected "
            f"({state['missing_position_count']}/3)"
        )

        # Require 3 consecutive misses
        if state["missing_position_count"] < 3:
            return state

        print(
            "[SYNC] confirmed flat position "
            "after 3 misses"
        )

        state["position_size"] = 0.0
        state["entry_price"] = None

        state["needs_new_ladder"] = True
        state["ladder_active"] = False
        state["level"] = 1

        return state

    # ==================================================
    # POSITION FOUND
    # ==================================================

    state["missing_position_count"] = 0

    try:
        size = float(
            current_pos.get("size")
            or 0
        )
    except Exception:
        size = 0.0

    raw_entry = (
        current_pos.get("entryPrice")
        or current_pos.get("price")
        or current_pos.get("avgEntryPrice")
    )

    try:
        entry_price = (
            float(raw_entry)
            if raw_entry
            else None
        )
    except Exception:
        entry_price = None

    old_entry = state.get("entry_price")
    old_size = float(
        state.get("position_size") or 0
    )

    state["position_size"] = size

    if entry_price and entry_price > 0:
        state["entry_price"] = entry_price

    # ==================================================
    # NEW FILL DETECTION
    # ==================================================

    size_changed = abs(size - old_size) > 1e-9

    entry_changed = (
        old_entry is not None
        and entry_price is not None
        and abs(old_entry - entry_price) > 1e-9
    )

    if size_changed or entry_changed:

        print(
            "[SYNC] position changed "
            f"size {old_size} -> {size}"
        )

        state["needs_new_ladder"] = False
        state["ladder_active"] = True
        state["reentry_pending"] = False

    return state
