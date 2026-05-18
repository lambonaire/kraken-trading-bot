import time
from bot.exchange.client import KrakenClient

from bot.exchange.kraken_futures import build_snapshot

from bot.state.store import StateStore

from bot.strategy.ladders.loader import load_ladder
from bot.strategy.basic_ladder import BasicLadderStrategy

state_store = StateStore()

config = load_ladder(
    "bot/strategy/ladders/doge_ladder.yaml"
)

strategy = BasicLadderStrategy(config)

exchange = KrakenClient()

def run_bot():
    print("🚀 Bot started...")

    while True:
        try:
            snapshot = build_snapshot()

            ticker = snapshot.get("ticker")
            market_data = {
                "price": ticker
            }
            accounts = snapshot.get("accounts", {})
            positions = snapshot.get("positions", {})
            orders = snapshot.get("orders", {})
            state = state_store.get()

            flex = accounts.get("accounts", {}).get("flex", {})
            open_positions = positions.get("openPositions", [])
            open_orders = orders.get("openOrders", [])
            signal = strategy.on_tick(
                market_data,
                state
            )

            print("\nSIGNAL:")
            print(signal)

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
            print(f"[ERROR loop] {e}")

        time.sleep(2)
