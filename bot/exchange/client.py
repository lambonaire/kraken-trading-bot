from bot.exchange.kraken_futures import (
    get_ticker,
    get_account_balance,
    get_open_positions,
    get_open_orders,
    place_market_order,
)


class KrakenClient:

    # =========================
    # MARKET DATA
    # =========================

    def ticker(self, symbol="PF_DOGEUSD"):
        return get_ticker(symbol)

    # =========================
    # ACCOUNT
    # =========================

    def balance(self):
        return get_account_balance()

    def positions(self):
        return get_open_positions()

    def open_orders(self):
        return get_open_orders()

    # =========================
    # EXECUTION
    # =========================

    def buy_market(self, symbol, size):
        return place_market_order(
            symbol=symbol,
            side="buy",
            size=size
        )

    def sell_market(self, symbol, size):
        return place_market_order(
            symbol=symbol,
            side="sell",
            size=size
        )
