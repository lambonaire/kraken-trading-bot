import os
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
# ENV CONFIG
# =========================

BOT_CONFIG = os.getenv(
    "BOT_CONFIG",
    "bot/strategy/ladders/doge_ladder.yaml"
)


# =========================
# INIT
# =========================


state_store = StateStore()

config = load_ladder(BOT_CONFIG)

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

    print("🚀 Bot started with config:", BOT_CONFIG)

    while True:

        try:

            # =========================
            # SYMBOL FIRST (FIX CRASH)
            # =========================
            config_symbol = config.get("symbol")

            state = state_store.get(config_symbol)

            symbol = state.get("symbol") or config_symbol

            if not symbol:
                raise ValueError("No symbol found in state or config")

            # =========================
            # SNAPSHOT
            # =========================
            snapshot = build_snapshot(symbol)

            ticker = snapshot.get("ticker")

            if not ticker:
                print("[WARNING] No ticker data")
                time.sleep(2)
                continue

            market_data = {
                "price": float(ticker)
            }


            # =========================
            # SYNC POSITION STATE
            # =========================
            sync_state_from_exchange(
                exchange,
                state_store,
                symbol
            )

            # =========================
            # RECONCILE ORDERS
            # =========================
            reconcile_orders(
                exchange,
                state_store,
                symbol
            )

            # =========================
            # REFRESH STATE
            # =========================
            state = state_store.get(symbol)

            # =========================
            # REBUILD LADDER
            # =========================
            if state.get("needs_new_ladder"):

                print("\nREBUILDING LADDER")

                position_size = float(state.get("position_size") or 0)
                entry_price = float(state.get("entry_price") or 0)
                level = int(state.get("level") or 1)

                print("SYMBOL:", symbol)
                print("LEVEL:", level)
                print("POSITION:", position_size)
                print("ENTRY:", entry_price)

                if position_size > 0 and entry_price > 0:

                    order_manager.create_ladder_orders(
                        symbol=symbol,
                        entry_price=entry_price,
                        size=position_size,
                        level=level
                    )

                state["needs_new_ladder"] = False
                state_store.states[symbol] = state

            # =========================
            # DEBUG STATE
            # =========================
            print("\n==============================")
            print("STATE")
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
            # PRICE
            # =========================
            print("\n==============================")
            print("PRICE")
            print("==============================")

            print(f"{symbol}: {ticker}")

            print("\n==============================")
            print("LOOP COMPLETE")
            print("==============================")

        except Exception as e:
            print(f"\n[ERROR loop] {e}")

        time.sleep(2)
