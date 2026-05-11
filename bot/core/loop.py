import time
from bot.exchange.kraken_futures import get_ticker

def run_bot():
    print("Bot started...")

    while True:
        try:
            price = get_ticker("PF_DOGEUSD")
            print("DOGE price:", price)

        except Exception as e:
            print("[ERROR loop]", e)

        time.sleep(2)
