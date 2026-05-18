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

# =========================
# CONFIG
# =========================

BASE_URL = "https://futures.kraken.com"

ACCOUNTS_ENDPOINT = "/derivatives/api/v3/accounts"
OPEN_POSITIONS_ENDPOINT = "/derivatives/api/v3/openpositions"
OPEN_ORDERS_ENDPOINT = "/derivatives/api/v3/openorders"
TICKERS_ENDPOINT = "/derivatives/api/v3/tickers"


# =========================
# SIGNING
# =========================

def generate_signature(endpoint_path: str, postdata: str, nonce: str) -> str:
    endpoint_path = endpoint_path.replace("/derivatives", "")

    message = (postdata + nonce + endpoint_path).encode()
    sha256_hash = hashlib.sha256(message).digest()

    secret = base64.b64decode(API_SECRET)

    signature = hmac.new(
        secret,
        sha256_hash,
        hashlib.sha512
    ).digest()

    return base64.b64encode(signature).decode()


# =========================
# REQUEST CORE
# =========================

def private_request(method: str, endpoint: str, data: dict | None = None):
    if data is None:
        data = {}

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
            response = requests.get(url, headers=headers, params=data, timeout=15)
        else:
            response = requests.post(url, headers=headers, data=postdata, timeout=15)

        try:
            return response.json()
        except Exception:
            return {
                "error": "invalid_json",
                "raw": response.text,
                "status_code": response.status_code
            }

    except Exception as e:
        return {"error": str(e)}


# =========================
# PUBLIC DATA
# =========================

def get_ticker(symbol="PF_DOGEUSD"):
    url = BASE_URL + TICKERS_ENDPOINT

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return {"error": "ticker_http_error", "code": response.status_code}

        data = response.json()

        tickers = data.get("tickers") or []

        for t in tickers:
            if t.get("symbol") == symbol or "DOGE" in (t.get("symbol") or ""):
                price = t.get("markPrice") or t.get("last")
                return float(price) if price else None

    except Exception as e:
        return {"error": str(e)}

    return None


# =========================
# PRIVATE API WRAPPERS
# =========================

def get_account_balance():
    return private_request("GET", ACCOUNTS_ENDPOINT)


def get_open_positions():
    return private_request("GET", OPEN_POSITIONS_ENDPOINT)


def get_open_orders():
    return private_request("GET", OPEN_ORDERS_ENDPOINT)


# =========================
# SNAPSHOT (voor later strategie)
# =========================

def build_snapshot():
    return {
        "timestamp": int(time.time() * 1000),
        "ticker": get_ticker(),
        "accounts": get_account_balance(),
        "positions": get_open_positions(),
        "orders": get_open_orders()
    }


# =========================
# MARKET ORDER
# =========================

def place_market_order(symbol: str, side: str, size: float):

    endpoint = "/derivatives/api/v3/sendorder"

    data = {
        "orderType": "mkt",
        "symbol": symbol,
        "side": side,
        "size": size
    }

    return private_request(
        "POST",
        endpoint,
        data
    )


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    print("🔥 SCRIPT STARTED")

    snapshot = build_snapshot()

    print(snapshot)
