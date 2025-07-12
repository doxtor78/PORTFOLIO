import nest_asyncio
nest_asyncio.apply()

import requests
from binance.client import Client
import asyncio
import time
import hmac
import hashlib

BINANCE_API_KEY = '8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7'
BINANCE_API_SECRET = 'jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO'

BASE_URL = 'https://api.binance.com'

def sign_params(params, secret):
    query_string = '&'.join([f"{k}={v}" for k, v in params.items() if v is not None])
    signature = hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature
    return params

def binance_signed_request(method, endpoint, api_key, api_secret, params=None):
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    params = sign_params(params, api_secret)
    headers = {'X-MBX-APIKEY': api_key}
    url = BASE_URL + endpoint
    if method == 'GET':
        resp = requests.get(url, headers=headers, params=params)
    else:
        resp = requests.post(url, headers=headers, params=params)
    return resp.json()

def get_binance_balances(api_key, api_secret):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    try:
        client = Client(api_key, api_secret)
        # Spot
        account = client.get_account()
        spot_balances = {}
        for asset in account['balances']:
            free = float(asset['free'])
            locked = float(asset['locked'])
            total = free + locked
            if total > 0:
                symbol = asset['asset']
                spot_balances[symbol] = spot_balances.get(symbol, 0.0) + total
        # Earn (Flexible Savings) - direct REST
        earn_flexible = {}
        try:
            data = binance_signed_request('GET', '/sapi/v1/lending/union/account', api_key, api_secret)
            for pos in data.get('positionAmountVos', []):
                asset = pos['asset']
                amount = float(pos['amount'])
                if amount > 0:
                    earn_flexible[asset] = earn_flexible.get(asset, 0.0) + amount
            print('[DEBUG] Flexible Savings:', earn_flexible)
        except Exception as e:
            print('[DEBUG] Flexible Savings error:', e)
        # Earn (Locked Savings) - direct REST
        earn_locked = {}
        try:
            data = binance_signed_request('GET', '/sapi/v1/lending/project/position/list', api_key, api_secret, {'status': 'HOLDING'})
            for pos in data:
                asset = pos['asset']
                amount = float(pos['amount'])
                if amount > 0:
                    earn_locked[asset] = earn_locked.get(asset, 0.0) + amount
            print('[DEBUG] Locked Savings:', earn_locked)
        except Exception as e:
            print('[DEBUG] Locked Savings error:', e)
        # Earn (Staking) - direct REST
        earn_staking = {}
        try:
            data = binance_signed_request('GET', '/sapi/v1/staking/position', api_key, api_secret, {'product': 'STAKING'})
            for pos in data:
                asset = pos['asset']
                amount = float(pos['amount'])
                if amount > 0:
                    earn_staking[asset] = earn_staking.get(asset, 0.0) + amount
            print('[DEBUG] Staking:', earn_staking)
        except Exception as e:
            print('[DEBUG] Staking error:', e)
        # Earn (Simple Earn Flexible) - new endpoint
        earn_simple_flexible = {}
        try:
            data = binance_signed_request('GET', '/sapi/v1/simple-earn/flexible/position', api_key, api_secret)
            for pos in data.get('data', []):
                asset = pos['asset']
                amount = float(pos['totalAmount'])
                if amount > 0:
                    earn_simple_flexible[asset] = earn_simple_flexible.get(asset, 0.0) + amount
            print('[DEBUG] Simple Earn Flexible:', earn_simple_flexible)
        except Exception as e:
            print('[DEBUG] Simple Earn Flexible error:', e)
        # Earn (Simple Earn Locked) - new endpoint
        earn_simple_locked = {}
        try:
            data = binance_signed_request('GET', '/sapi/v1/simple-earn/locked/position', api_key, api_secret)
            for pos in data.get('data', []):
                asset = pos['asset']
                amount = float(pos['amount'])
                if amount > 0:
                    earn_simple_locked[asset] = earn_simple_locked.get(asset, 0.0) + amount
            print('[DEBUG] Simple Earn Locked:', earn_simple_locked)
        except Exception as e:
            print('[DEBUG] Simple Earn Locked error:', e)
        # Isolated Margin (via python-binance)
        margin_balances = {}
        try:
            margin = client.get_isolated_margin_account()
            for asset_info in margin['assets']:
                base = asset_info['baseAsset']
                base_total = float(asset_info['baseAsset']['totalAsset'])
                if base_total > 0:
                    margin_balances[base['asset']] = margin_balances.get(base['asset'], 0.0) + base_total
                quote = asset_info['quoteAsset']
                quote_total = float(asset_info['quoteAsset']['totalAsset'])
                if quote_total > 0:
                    margin_balances[quote['asset']] = margin_balances.get(quote['asset'], 0.0) + quote_total
            print('[DEBUG] Isolated Margin:', margin_balances)
        except Exception as e:
            print('[DEBUG] Isolated Margin error:', e)
        # Merge all balances (add new Earn sources)
        all_assets = set(spot_balances) | set(earn_flexible) | set(earn_locked) | set(earn_staking) | set(margin_balances) | set(earn_simple_flexible) | set(earn_simple_locked)
        balances = []
        for symbol in all_assets:
            total_amount = (
                spot_balances.get(symbol, 0.0)
                + earn_flexible.get(symbol, 0.0)
                + earn_locked.get(symbol, 0.0)
                + earn_staking.get(symbol, 0.0)
                + margin_balances.get(symbol, 0.0)
                + earn_simple_flexible.get(symbol, 0.0)
                + earn_simple_locked.get(symbol, 0.0)
            )
            if symbol != 'USDT':
                try:
                    ticker = client.get_symbol_ticker(symbol=f"{symbol}USDT")
                    price = float(ticker['price'])
                except Exception:
                    price = 0.0
            else:
                price = 1.0
            usd_value = total_amount * price
            balances.append({
                'exchange': 'Binance',
                'asset': symbol,
                'amount': total_amount,
                'price': price,
                'usd_value': usd_value
            })
        return balances
    except Exception as e:
        print('[DEBUG] Top-level error:', e)
        return []

if __name__ == '__main__':
    api_key = BINANCE_API_KEY
    api_secret = BINANCE_API_SECRET
    balances = get_binance_balances(api_key, api_secret)
    if balances:
        print("Binance Balances (all assets):")
        print("Asset      Amount          Price (USD)     Value (USD)")
        print("-------------------------------------------------------")
        for b in balances:
            print(f"{b['asset']:<10} {b['amount']:<15.8f} ${b['price']:<15.2f} ${b['usd_value']:<15.2f}")
        total = sum(b['usd_value'] for b in balances)
        print("-------------------------------------------------------")
        print(f"TOTAL                                      ${total:<15.2f}")
    else:
        print("No Binance balances found.") 