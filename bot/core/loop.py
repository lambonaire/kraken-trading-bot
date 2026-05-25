import time

from bot.exchange.kraken_futures import build_snapshot
from bot.exchange.client import KrakenClient

from bot.state.store import StateStore
from bot.state.sync import sync_state_from_exchange
from bot.state.reconciliation import reconcile_orders

from bot.strategy.ladders.loader import load_ladder
from bot.strategy.basic_ladder import BasicLadderStrategy

from bot.execution.order_manager import OrderManager


# =========================
# INIT
# =========================

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


# =========================
# MAIN LOOP
# =========================

def run_bot():

    print("🚀 Bot started...")

    while True:

        try:

            # =========================
            # FETCH SNAPSHOT
            # =========================
            snapshot = build_snapshot()

            ticker = snapshot.get("ticker")

            market_data = {
                "price": float(ticker)
            }

            # =========================
            # SYNC POSITION STATE
            # =========================
            sync_state_from_exchange(
                exchange,
                state_store
            )

            # =========================
            # RECONCILE ORDERS
            # =========================
            reconcile_orders(
                exchange,
                state_store
            )

            # =========================
            # GET STATE
            # =========================
            state = state_store.get()

            # =========================
            # REBUILD LADDER (SAFE ONCE ONLY)
            # =========================
            if state.get("needs_new_ladder"):

                print("\nREBUILDING LADDER")

                symbol = state.get("symbol")
                position_size = float(state.get("position_size") or 0)
                entry_price = float(state.get("entry_price") or 0)
                level = int(state.get("level") or 1)

                print("LEVEL:", level)
                print("POSITION:", position_size)
                print("ENTRY:", entry_price)

                if symbol and position_size > 0 and entry_price > 0:

                    order_manager.create_ladder_orders(
                        symbol=symbol,
                        entry_price=entry_price,
                        size=position_size,
                        level=level
                    )

                # 🔥 BELANGRIJK: meteen resetten om dubbele triggers te voorkomen
                state["needs_new_ladder"] = False
                state_store.state = state

            # =========================
            # CURRENT STATE
            # =========================
            print("\n==============================")
            print("CURRENT STATE")
            print("==============================")
            print(state)

            # =========================
            # STRATEGY
            # =========================
            signal = strategy.on_tick(
                market_data,
                state
            )

            print("\n==============================")
            print("SIGNAL")
            print("==============================")
            print(signal)

            # =========================
            # EXECUTION
            # =========================
            result = order_manager.execute(
                signal,
                market_data
            )

            print("\n==============================")
            print("EXECUTION")
            print("==============================")
            print(result)

            # =========================
            # MARKET
            # =========================
            print("\n==============================")
            print("MARKET")
            print("==============================")

            print(f"Price: {ticker}")

            print("\n==============================")
            print("LOOP COMPLETE")
            print("==============================")

        except Exception as e:
            print(f"\n[ERROR loop] {e}")

        # =========================
        # LOOP DELAY
        # =========================
        time.sleep(2)
