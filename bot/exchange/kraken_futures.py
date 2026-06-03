import os
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

if not API_KEY or not API_SECRET:
    raise RuntimeError("Missing API keys in .env")

BASE_URL = "https://futures.kraken.com"

ACCOUNTS_ENDPOINT = "/derivatives/api/v3/accounts"
OPEN_POSITIONS_ENDPOINT = "/derivatives/api/v3/openpositions"
OPEN_ORDERS_ENDPOINT = "/derivatives/api/v3/openorders"
TICKERS_ENDPOINT = "/derivatives/api/v3/tickers"
INSTRUMENTS_ENDPOINT = "/derivatives/api/v3/instruments"


# =========================
# SIGNING
# =========================
def generate_signature(endpoint_path: str, postdata: str, nonce: str) -> str:
    endpoint_path = endpoint_path.replace("/derivatives", "")

    message = (postdata + nonce + endpoint_path).encode()
    sha256_hash = hashlib.sha256(message).digest()

    secret = base64.b64decode(API_SECRET)

    signature = hmac.new(secret, sha256_hash, hashlib.sha512).digest()
    return base64.b64encode(signature).decode()


# =========================
# REQUEST CORE
# =========================
def private_request(method: str, endpoint: str, data: dict | None = None):
    data = data or {}

    nonce = str(int(time.time() * 1000))
    postdata = urlencode(data) if data else ""

    signature = generate_signature(endpoint, postdata, nonce)

    headers = {
        "APIKey": API_KEY,
        "Authent": signature,
        "Nonce": nonce
    }

    url = BASE_URL + endpoint

    try:
        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, params=data, timeout=15)
        else:
            resp = requests.post(url, headers=headers, data=postdata, timeout=15)

        return resp.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# PUBLIC DATA
# =========================
def get_ticker(symbol: str):
    try:
        resp = requests.get(BASE_URL + TICKERS_ENDPOINT, timeout=10)
        if resp.status_code != 200:
            return None

        data = resp.json()
        for t in data.get("tickers", []):
            if t.get("symbol") == symbol:
                price = t.get("markPrice") or t.get("last")
                return float(price) if price else None
    except:
        return None

    return None


# =========================
# ACCOUNT / POSITIONS
# =========================
def get_account_balance():
    return private_request("GET", ACCOUNTS_ENDPOINT)

def get_open_positions():
    return private_request("GET", OPEN_POSITIONS_ENDPOINT)

def get_open_orders():
    return private_request("GET", OPEN_ORDERS_ENDPOINT)

def cancel_order(order_id):
    return private_request(
        "POST",
        "/derivatives/api/v3/cancelorder",
        {"order_id": order_id}
    )


# =========================
# SNAPSHOT
# =========================
def build_snapshot(symbol: str):
    return {
        "timestamp": int(time.time() * 1000),
        "ticker": get_ticker(symbol),
        "accounts": get_account_balance(),
        "positions": get_open_positions(),
        "orders": get_open_orders()
    }


# =========================
# ORDERS
# =========================
def place_market_order(symbol: str, side: str, size: float):
    return private_request(
        "POST",
        "/derivatives/api/v3/sendorder",
        {
            "orderType": "mkt",
            "symbol": symbol,
            "side": side,
            "size": str(size)
        }
    )


def place_limit_order(symbol: str, side: str, size: float, price: float, reduce_only: bool = True):
    data = {
        "orderType": "lmt",
        "symbol": symbol,
        "side": side,
        "size": str(size),
        "limitPrice": str(price),
    }

    if reduce_only:
        data["reduceOnly"] = "true"

    return private_request("POST", "/derivatives/api/v3/sendorder", data)


# =========================
# FIX: compatibility hook (IMPORTANT)
# =========================
# =========================
# INSTRUMENT METADATA
# =========================

_instruments_cache = None
_instruments_cache_ts = 0


def get_instruments():
    global _instruments_cache
    global _instruments_cache_ts

    now = time.time()

    # cache 5 minuten
    if _instruments_cache and (now - _instruments_cache_ts < 300):
        return _instruments_cache

    try:
        resp = requests.get(
            BASE_URL + INSTRUMENTS_ENDPOINT,
            timeout=10
        )

        data = resp.json()

        _instruments_cache = data
        _instruments_cache_ts = now

        return data

    except Exception:
        return {"instruments": []}


def get_tick_size(symbol: str):
    data = get_instruments()

    for instrument in data.get("instruments", []):

        if instrument.get("symbol") == symbol:

            tick = instrument.get("tickSize")

            if tick:
                return float(tick)

    return 0.0001


def round_to_tick(price: float, tick: float):
    if price is None:
        return None

    return round(
        round(price / tick) * tick,
        10
    )


def get_price_precision(symbol: str):

    tick = get_tick_size(symbol)

    tick_str = (
        f"{tick:.10f}"
        .rstrip("0")
        .rstrip(".")
    )

    if "." not in tick_str:
        return 0

    return len(
        tick_str.split(".")[1]
    )
