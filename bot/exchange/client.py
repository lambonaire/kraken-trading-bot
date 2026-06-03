from bot.exchange.kraken_futures import (
    get_ticker,
    get_account_balance as _get_account_balance,
    get_open_positions as _get_open_positions,
    get_open_orders as _get_open_orders,
    place_market_order,
    place_limit_order,
    cancel_order as _cancel_order,
)


class KrakenClient:
    """
    Clean exchange interface.

    Keeps backward compatibility with older method names
    while exposing the names the rest of the bot now expects.
    """

    # =========================
    # MARKET DATA
    # =========================
    def ticker(self, symbol: str):
        return get_ticker(symbol)

    def get_ticker(self, symbol: str):
        return self.ticker(symbol)

    def get_price(self, symbol: str):
        return self.ticker(symbol)

    # =========================
    # ACCOUNT
    # =========================
    def balance(self):
        return _get_account_balance()

    def get_account_balance(self):
        return self.balance()

    # =========================
    # POSITIONS
    # =========================
    def positions(self):
        return _get_open_positions()

    def get_open_positions(self):
        return self.positions()

    # =========================
    # OPEN ORDERS
    # =========================
    def open_orders(self):
        return _get_open_orders()

    def get_open_orders(self):
        return self.open_orders()

    # =========================
    # EXECUTION
    # =========================
    def buy_market(self, symbol, size):
        return place_market_order(
            symbol=symbol,
            side="buy",
            size=size,
        )

    def sell_market(self, symbol, size):
        return place_market_order(
            symbol=symbol,
            side="sell",
            size=size,
        )

    def market_order(self, symbol, side, size):
        return place_market_order(
            symbol=symbol,
            side=side,
            size=size,
        )

    def buy_limit(self, symbol, size, price, reduce_only=False):
        return place_limit_order(
            symbol=symbol,
            side="buy",
            size=size,
            price=price,
            reduce_only=reduce_only,
        )

    def sell_limit(self, symbol, size, price, reduce_only=True):
        return place_limit_order(
            symbol=symbol,
            side="sell",
            size=size,
            price=price,
            reduce_only=reduce_only,
        )

    def limit_order(self, symbol, side, size, price, reduce_only=True):
        return place_limit_order(
            symbol=symbol,
            side=side,
            size=size,
            price=price,
            reduce_only=reduce_only,
        )

    def place_market_order(self, symbol, side, size):
        return place_market_order(
            symbol=symbol,
            side=side,
            size=size
        )

    def place_limit_order(self, symbol, side, size, price, reduce_only=True):
        return place_limit_order(
            symbol=symbol,
            side=side,
            size=size,
            price=price,
            reduce_only=reduce_only
        )

    # =========================
    # CANCEL
    # =========================
    def cancel_order(self, order_id):
        return _cancel_order(order_id)
