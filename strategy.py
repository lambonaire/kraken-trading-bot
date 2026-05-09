def simple_strategy(price):
    if price is None:
        return "HOLD"

    if price < 0.08:
        return "BUY"
    elif price > 0.12:
        return "SELL"
    else:
        return "HOLD"
