import os
import time
import traceback
import yaml

from bot.strategy.basic_ladder import BasicLadderStrategy
from bot.strategy.sizing_engine import SizingEngine
from bot.execution.order_manager import OrderManager
from bot.exchange.client import KrakenClient as Exchange
from bot.exchange.market_specs import MarketSpecs
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
        raise ValueError(f"Invalid config file: {config_path}")

    if "symbol" not in config:
        raise ValueError("Missing 'symbol' in config")

    print(f"🚀 Bot started with config: {config_path}")

    # init core components
    exchange = Exchange()
    state_store = StateStore()

    strategy = BasicLadderStrategy(config)

    market_specs = MarketSpecs()
    market_specs.refresh()

    sizing_engine = SizingEngine(
        strategy=strategy,
        market_specs=market_specs
    )

    order_manager = OrderManager(
        exchange=exchange,
        state_store=state_store,
        strategy=strategy,
        sizing=sizing_engine,
    )

    symbol = config["symbol"]

    while True:
        try:

            # 1. SYNC
            sync_state_from_exchange(exchange, state_store, symbol)

            state = state_store.get(symbol) or {}

            if float(state.get("position_size", 0) or 0) == 0 and float(state.get("last_reconciled_position_size", 0) or 0) > 0:
                state["flat_cooldown_until"] = time.time() + 3
                print("[LOOP] flat transition detected -> cooldown 3s")


            # 2. RECONCILE
            reconcile_orders(exchange, state_store, strategy, symbol)
            print("[LOOP] reconciliation complete")

            # 3. MARKET DATA
            price = exchange.get_price(symbol)
            market_data = {"price": price}
            state = state_store.get(symbol)

            # 4. STRATEGY
            signal = strategy.on_tick(market_data, state)

            print("\n==============================")
            print("STATE")
            print("==============================")
            print(state)

            print("\n==============================")
            print("SIGNAL")
            print("==============================")
            print(signal)

            # 5. SAFE SIGNAL GUARD (🔥 FIX FOR YOUR CRASH)
            if not signal:
                print("[STRATEGY] no signal → skip execution")
                time.sleep(2)
                continue

            if not isinstance(signal, dict):
                print("[STRATEGY] invalid signal type → skip")
                time.sleep(2)
                continue

            action = signal.get("action")

            # 6. EXECUTION ROUTING
            if action == "OPEN_ENTRY":
                result = order_manager.execute(signal, market_data)

                print("\n==============================")
                print("EXECUTION")
                print("==============================")
                print(result)

            else:
                print(f"[STRATEGY] no executable action: {action}")
                result = None

            # 7. PRICE DEBUG
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
