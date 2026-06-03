import os
import time
import traceback
import yaml

from bot.strategy.basic_ladder import BasicLadderStrategy
from bot.strategy.sizing_engine import SizingEngine
from bot.execution.order_manager import OrderManager
from bot.exchange.client import KrakenClient as Exchange
from bot.state.store import StateStore
from bot.state.sync import sync_state_from_exchange
from bot.state.reconciliation import reconcile_orders


def run_bot():
    config_path = os.getenv("BOT_CONFIG")
    if not config_path:
        raise ValueError("BOT_CONFIG not set")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError(f"Invalid or empty config file: {config_path}")

    if "symbol" not in config:
        raise ValueError(f"Missing 'symbol' in config: {config_path}")

    print(f"🚀 Bot started with config: {config_path}")

    exchange = Exchange()
    state_store = StateStore()

    strategy = BasicLadderStrategy(config)
    sizing_engine = SizingEngine(strategy)

    order_manager = OrderManager(
        exchange=exchange,
        state_store=state_store,
        strategy=strategy,
        sizing=sizing_engine,
    )

    symbol = config["symbol"]

    while True:
        try:
            sync_state_from_exchange(exchange, state_store, symbol)

            reconcile_orders(exchange, state_store, strategy, symbol)
            print("[LOOP] reconciliation complete")

            price = exchange.get_price(symbol)
            market_data = {"price": price}

            state = state_store.get(symbol)

            signal = strategy.on_tick(market_data, state)

            print("\n==============================")
            print("STATE")
            print("==============================")
            print(state)

            print(">>> STRATEGY CALLED\n")

            print("==============================")
            print("SIGNAL")
            print("==============================")
            print(signal)

            result = order_manager.execute(signal, market_data)

            print("\n==============================")
            print("EXECUTION")
            print("==============================")
            print(result)

            print("\n==============================")
            print("PRICE")
            print("==============================")
            print(f"{symbol}: {price}")

            print("\n==============================")
            print("LOOP COMPLETE")
            print("==============================")

            time.sleep(2)

        except Exception as e:
            print("\n[ERROR loop]", str(e))
            traceback.print_exc()
            time.sleep(2)
