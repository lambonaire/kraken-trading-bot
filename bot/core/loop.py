import time

from bot.strategy.basic_ladder import BasicLadderStrategy
from bot.execution.order_manager import OrderManager
from bot.strategy.sizing_engine import SizingEngine

from bot.exchange.client import KrakenClient as Exchange
from bot.state.store import StateStore


def run_bot():

    # =========================
    # LOAD CONFIG
    # =========================
    import os
    import yaml

    config_path = os.getenv("BOT_CONFIG")

    if not config_path:
        raise ValueError("BOT_CONFIG not set")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    print(f"🚀 Bot started with config: {config_path}")

    # =========================
    # CORE OBJECTS
    # =========================
    exchange = Exchange()
    state_store = StateStore()

    # =========================
    # STRATEGY
    # =========================
    strategy = BasicLadderStrategy(config)

    # =========================
    # ORDER MANAGER
    # =========================
    order_manager = OrderManager(exchange, state_store, strategy)

    # =========================
    # SIZING ENGINE (FIX)
    # =========================
    sizing_engine = SizingEngine(strategy)

    order_manager.set_sizing_engine(sizing_engine)

    # =========================
    # MAIN LOOP
    # =========================
    symbol = config["symbol"]

    while True:

        try:

            # -------------------------
            # MARKET DATA
            # -------------------------
            price = exchange.get_price(symbol)

            market_data = {
                "price": price
            }

            # -------------------------
            # STATE
            # -------------------------
            state = state_store.get(symbol)

            # -------------------------
            # STRATEGY SIGNAL
            # -------------------------
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

            # -------------------------
            # EXECUTION
            # -------------------------
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
            time.sleep(2)
