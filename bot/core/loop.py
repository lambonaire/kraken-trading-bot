import time

from bot.exchange.kraken_futures import build_snapshot
from bot.exchange.client import KrakenClient

from bot.state.store import StateStore
from bot.state.sync import sync_state_from_exchange
from bot.state.reconciliation import reconcile_orders

from bot.strategy.ladders.loader import load_ladder
from bot.strategy.basic_ladder import BasicLadderStrategy

from bot.execution.order_manager import OrderManager


# -------------------------
# INIT
# -------------------------
state_store = StateStore()

config = load_ladder(
    "bot/strategy/ladders/doge_ladder.yaml"
)

strategy = BasicLadderStrategy(config)

exchange = KrakenClient()

order_manager = OrderManager(
    exchange,
    state_store,
    strategy
)


# -------------------------
# MAIN LOOP
# -------------------------
def run_bot():

    print("🚀 Bot started...")

    while True:

        try:

            # -------------------------
            # FETCH SNAPSHOT
            # -------------------------
            snapshot = build_snapshot()

            ticker = snapshot.get("ticker")

            market_data = {
                "price": float(ticker)
            }

            # -------------------------
            # EXCHANGE → LOCAL STATE
            # -------------------------
            sync_state_from_exchange(
                exchange,
                state_store
            )

            # -------------------------
            # ORDER RECONCILIATION
            # -------------------------
            reconcile_orders(
                exchange,
                state_store
            )

            # -------------------------
            # CURRENT STATE
            # -------------------------
            state = state_store.get()

            print("\n==============================")
            print("CURRENT STATE")
            print("==============================")
            print(state)

            # -------------------------
            # STRATEGY
            # -------------------------
            signal = strategy.on_tick(
                market_data,
                state
            )

            print("\n==============================")
            print("SIGNAL")
            print("==============================")
            print(signal)

            # -------------------------
            # EXECUTION
            # -------------------------
            result = order_manager.execute(
                signal,
                market_data
            )

            print("\n==============================")
            print("EXECUTION")
            print("==============================")
            print(result)

            # -------------------------
            # DEBUG
            # -------------------------
            print("\n==============================")
            print("MARKET")
            print("==============================")

            print(f"Price: {ticker}")

            print("\n==============================")
            print("LOOP COMPLETE")
            print("==============================")

        except Exception as e:

            print(f"\n[ERROR loop] {e}")

        # Prevent spam loops
        time.sleep(2)
