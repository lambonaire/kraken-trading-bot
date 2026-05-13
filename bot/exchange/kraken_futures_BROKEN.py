import os
import json
import time
import base64
import hashlib
import hmac
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

BASE_URL = "https://futures.kraken.com/derivatives/api/v3"

# =========================
# AUTH HELPERS
# =========================

def generate_signature(endpoint, data="", nonce=""):

    postdata = urlencode(data) if isinstance(data, dict) else data
    message = postdata + nonce + endpoint

    sha256_hash = hashlib.sha256(message.encode()).digest()
    secret = base64.b64decode(API_SECRET)

    signature = hmac.new(secret, sha256_hash, hashlib.sha512).digest()

    return base64.b64encode(signature).decode()

ata = {}

    nonce = str(int(time.time() * 1000))
    signature = generate_signature(endpoint, data, nonce)

    headers = {
        "APIKey": API_KEY,

def get_ticker(symbol="PF_DOGEUSD"):
    """
    Haalt markPrice of last price op van Kraken Futures.
    Robuust voor verschillende API response formats.
    """

    url = f"{BASE_URL}/tickers"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        # 🔥 Soms is het een dict met "tickers"
        tickers = data.get("tickers")

        # 🔥 Soms is het direct een list
        if tickers is None:
            tickers = data if isinstance(data, list) else []

        for t in tickers:
            sym = t.get("symbol")

            if sym == symbol or (sym and "DOGE" in sym):
                price = t.get("markPrice") or t.get("last")

                print(json.dumps(t, indent=2))

                return float(price) if price is not None else None

    except Exception as e:
        print(f"[ERROR get_ticker] {e}")

    return None

def get_account_balance():
    return private_request("GET", "/accountsummary")

def get_open_positions():
    endpoint = "/openpositions"
    return private_request("GET", endpoint)

def get_open_orders():
    endpoint = "/openorders"
    return private_request("GET", endpoint)

def place_market_order(symbol="PF_DOGEUSD", side="buy", size=10):
    endpoint = "/sendorder"

    data = {
        "orderType": "mkt",
        "symbol": symbol,
        "side": side,
        "size": size
    }

    return private_request("POST", endpoint, data)

