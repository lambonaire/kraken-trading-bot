import time
from bot.exchange.kraken_futures import get_ticker


def run_bot():
    print("Futures bot started...")

    while True:
        try:
            price = get_ticker("PF_DOGEUSD")

            print(f"[INFO] DOGE futures price={price}")

        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(10)
