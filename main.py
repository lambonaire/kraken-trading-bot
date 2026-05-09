from exchange import get_doge_price
from strategy import simple_strategy

price = get_doge_price()
signal = simple_strategy(price)

print("DOGE price:", price)
print("Signal:", signal)
