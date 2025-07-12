import requests
import time
import hmac
import hashlib
import json

# BitMEX API credentials (from portfolio_app.py)
BITMEX_API_KEY = 'wZ6_u4IKRmWrwlt0NB8o_ACi'
BITMEX_API_SECRET = '22KthvDICWGThQ3_MAseFwiluDQPZz9yb1uQKaIyTw84EALY'
BITMEX_API_URL = 'https://www.bitmex.com/api/v1'

def bitmex_request(method, endpoint, params=None):
    """
    Make an authenticated request to the BitMEX API.
    method: 'GET', 'POST', etc.
    endpoint: e.g. '/user/walletSummary'
    params: dict of query params (for GET) or body (for POST)
    """
    expires = int(time.time()) + 5  # 5 seconds in the future
    path = '/api/v1' + endpoint
    query = ''
    if method == 'GET' and params:
        query = '?' + '&'.join(f"{k}={v}" for k, v in params.items())
        path += query
    url = 'https://www.bitmex.com' + path
    body = '' if method == 'GET' else json.dumps(params) if params else ''
    message = method + path + str(expires) + body
    signature = hmac.new(
        BITMEX_API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    headers = {
        'api-expires': str(expires),
        'api-key': BITMEX_API_KEY,
        'api-signature': signature,
        'Content-Type': 'application/json'
    }
    print(f"DEBUG: BitMEX signature string: {message}")
    print(f"DEBUG: BitMEX signature: {signature}")
    print(f"DEBUG: BitMEX headers: {headers}")
    print(f"DEBUG: BitMEX url: {url}")
    response = requests.request(method, url, headers=headers, data=body if method != 'GET' else None)
    try:
        return response.json()
    except Exception:
        return response.text

def get_bitmex_balances():
    """
    Fetches and processes wallet balances from BitMEX.
    """
    response = bitmex_request('GET', '/user/walletSummary')
    if not isinstance(response, list):
        print("Unexpected BitMEX API response:", response)
        return []

    balances = []
    for wallet in response:
        if wallet.get('transactType') == 'Total':
            balance = wallet.get('walletBalance', 0)
            if balance != 0:
                asset = wallet['currency'].upper()
                if asset == 'XBT':
                    asset = 'BTC'
                    amount = balance / 1e8
                else:
                    amount = balance
                
                balances.append({
                    'asset': asset,
                    'amount': amount
                })
    return balances

if __name__ == '__main__':
    # Fetch wallet summary
    fetched_balances = get_bitmex_balances()
    if fetched_balances:
        print("BitMEX Balances (all assets):")
        print(f"{'Asset':<10} {'Amount':<15} {'Price (USD)':<15} {'Value (USD)':<15}")
        print("-" * 55)
        for b in fetched_balances:
            print(f"{b['asset']:<10} {b['amount']:<15.8f} ${b.get('price', 0):<14.2f} ${b.get('usd_value', 0):<14.2f}")
        print("-" * 55)
        total = sum(b.get('usd_value', 0) for b in fetched_balances)
        print(f"{'TOTAL':<10} {'':<15} {'':<15} ${total:<14.2f}")
    else:
        print("No BitMEX balances found or error fetching them.") 