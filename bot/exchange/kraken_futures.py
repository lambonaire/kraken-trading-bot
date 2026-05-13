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
# AUTH
# =========================


def generate_signature(endpoint, data, nonce):

    postdata = urlencode(data) if isinstance(data, dict) else ""

    encoded = (postdata + nonce + endpoint).encode()

    message = hashlib.sha256(encoded).digest()

    secret = base64.b64decode(API_SECRET)

    signature = hmac.new(secret, message, hashlib.sha512)

    return base64.b64encode(signature.digest()).decode()

def private_request(method, endpoint, data=None):

    if data is None:
        data = {}

    nonce = str(int(time.time() * 1000))

    signature = generate_signature(endpoint, data, nonce)

    headers = {
        "APIKey": API_KEY,
        "Authent": signature,
        "Nonce": nonce
    }

    url = BASE_URL + endpoint

    try:

        if method == "GET":
            response = requests.get(
                url,
                headers=headers,
                params=data,
                timeout=10
            )

        else:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                timeout=10
            )

        return response.json()

    except Exception as e:
        print(f"[ERROR private_request] {e}")
        return None

# =========================
# PUBLIC
# =========================

def get_ticker(symbol="PF_DOGEUSD"):
    url = f"{BASE_URL}/tickers"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        tickers = data.get("tickers")
        if tickers is None:
            tickers = data if isinstance(data, list) else []

        for t in tickers:
            sym = t.get("symbol")

            if sym == symbol or (sym and "DOGE" in sym):
                price = t.get("markPrice") or t.get("last")
                return float(price) if price else None

    except Exception as e:
        print(f"[ERROR get_ticker] {e}")

    return None


# =========================
# PRIVATE WRAPPERS
# =========================

def get_account_balance():
    return private_request("GET", "/accounts")

def get_open_positions():
    return private_request("GET", "/positions")

def get_open_orders():
    return private_request("GET", "/orders")

def place_market_order(symbol="PF_DOGEUSD", side="buy", size=10):
    data = {
        "orderType": "mkt",
        "symbol": symbol,
        "side": side,
        "size": size
    }

    return private_request("POST", "/sendorder", data)
