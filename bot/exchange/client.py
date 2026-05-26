from bot.exchange.kraken_futures import (
    get_ticker,
    get_account_balance,
    get_open_positions,
    get_open_orders,
    place_market_order,
    place_limit_order,
    cancel_order,
)


class KrakenClient:

    # =========================
    # MARKET DATA
    # =========================

    def ticker(self, symbol: str):
        return get_ticker(symbol)

    # =========================
    # ACCOUNT
    # =========================

    def balance(self):
        return get_account_balance()

    def positions(self):
        return get_open_positions()

    def get_open_positions(self):
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

    def sell_limit(
        self,
        symbol,
        size,
        price,
        reduce_only=True
    ):
        return place_limit_order(
            symbol=symbol,
            side="sell",
            size=size,
            price=price,
            reduce_only=reduce_only
        )

    def buy_limit(
        self,
        symbol,
        size,
        price,
        reduce_only=False
    ):
        return place_limit_order(
            symbol=symbol,
            side="buy",
            size=size,
            price=price,
            reduce_only=reduce_only
        )

    # =========================
    # CANCEL
    # =========================

    def cancel_order(self, order_id):
        return cancel_order(order_id)
