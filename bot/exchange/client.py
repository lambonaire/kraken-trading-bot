# bot/exchange/client.py

from bot.exchange.kraken_futures import (
    get_ticker,
    get_account_balance,
    get_open_positions,
    get_open_orders,
    place_market_order
)

# =========================
# PUBLIC API (SINGLE ENTRY POINT)
# =========================

def ticker(symbol="PF_DOGEUSD"):
    return get_ticker(symbol)


def balance():
    return get_account_balance()


def positions():
    return get_open_positions()


def open_orders():
    return get_open_orders()


def buy(symbol="PF_DOGEUSD", size=10):
    return place_market_order(symbol=symbol, side="buy", size=size)


def sell(symbol="PF_DOGEUSD", size=10):
    return place_market_order(symbol=symbol, side="sell", size=size)
