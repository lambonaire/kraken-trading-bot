from bot.exchange.kraken_futures import get_open_position
from bot.state.store import state


def sync_position_state():
    """
    Synchroniseert lokale state met Kraken.
    Kraken is de waarheid.
    """

    position = get_open_position()

    if not position:
        state["position_size"] = 0
        state["entry_price"] = None
        state["symbol"] = None

        print("🟡 Geen open positie op Kraken")

        return

    size = position["size"]
    entry_price = position["price"]
    symbol = position["symbol"]

    state["position_size"] = size
    state["entry_price"] = entry_price
    state["symbol"] = symbol

    print(
        f"✅ Position synced | "
        f"Size: {size} | "
        f"Entry: {entry_price}"
    )
