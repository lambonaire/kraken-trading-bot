import time

from bot.exchange.kraken_futures import build_snapshot
from bot.exchange.client import KrakenClient

from bot.state.store import StateStore
from bot.state.sync import sync_state_from_exchange

from bot.strategy.ladders.loader import load_ladder
from bot.strategy.basic_ladder import BasicLadderStrategy

from bot.execution.order_manager import OrderManager
from bot.state.reconciliation import reconcile_orders


# -------------------------
# INIT
# -------------------------
state_store = StateStore()

config = load_ladder("bot/strategy/ladders/doge_ladder.yaml")
strategy = BasicLadderStrategy(config)

exchange = KrakenClient()

order_manager = OrderManager(exchange, state_store)


# -------------------------
# MAIN LOOP
# -------------------------
def run_bot():
    print("🚀 Bot started...")

    while True:
        try:
            # -------------------------
            # SNAPSHOT (market + account)
            # -------------------------
            snapshot = build_snapshot()

            ticker = snapshot.get("ticker")
            market_data = {"price": ticker}

            accounts = snapshot.get("accounts", {})
            positions = snapshot.get("positions", {})
            orders = snapshot.get("orders", {})

            flex = accounts.get("accounts", {}).get("flex", {})
            open_positions = positions.get("openPositions", [])
            open_orders = orders.get("openOrders", [])

            # -------------------------
            # STATE SYNC (Kraken → store)
            # -------------------------
            sync_state_from_exchange(exchange, state_store)

            # -------------------------
            # ORDER RECONCILIATION
            # -------------------------
            reconcile_orders(exchange, state_store)

            # -------------------------
            # STATE
            # -------------------------
            state = state_store.get()

            print("\n==============================")
            print("CURRENT STATE")
            print("==============================")
            print(state)

            # -------------------------
            # STRATEGY
            # -------------------------
            signal = strategy.on_tick(market_data, state)

            print("\n==============================")
            print("SIGNAL RAW")
            print("==============================")
            print(signal)

            if signal:
                print("ACTION:", signal.get("action"))
            else:
                print("ACTION: NONE")

            # -------------------------
            # EXECUTION
            # -------------------------
            result = order_manager.execute(signal, market_data)

            print("\n==============================")
            print("EXEC RESULT")
            print("==============================")
            print(result)

            # -------------------------
            # DEBUG OUTPUT
            # -------------------------
            print("\n==============================")
            print("BOT LOOP")
            print("==============================")

            print(f"Timestamp: {snapshot.get('timestamp')}")
            print(f"DOGE Price: {ticker}")

            print(f"Portfolio Value: {flex.get('portfolioValue')}")
            print(f"Available Margin: {flex.get('availableMargin')}")
            print(f"Collateral Value: {flex.get('collateralValue')}")

            print(f"Open Positions: {len(open_positions)}")

            if open_positions:
                print("\n--- POSITION DETAILS ---")

                for pos in open_positions:
                    print(
                        f"Symbol: {pos.get('symbol')} | "
                        f"Side: {pos.get('side')} | "
                        f"Size: {pos.get('size')} | "
                        f"Entry: {pos.get('price')} | "
                        f"PnL: {pos.get('pnl')}"
                    )

            print(f"Open Orders: {len(open_orders)}")

            if open_orders:
                print("\n--- ORDER DETAILS ---")

                for order in open_orders:
                    print(
                        f"Symbol: {order.get('symbol')} | "
                        f"Side: {order.get('side')} | "
                        f"Type: {order.get('type')} | "
                        f"Size: {order.get('size')} | "
                        f"Price: {order.get('limitPrice')}"
                    )

        except Exception as e:
            print(f"\n[ERROR loop] {e}")

        time.sleep(2)
