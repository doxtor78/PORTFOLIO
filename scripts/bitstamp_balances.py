import requests
import hmac
import hashlib
import time
import base64
import json
from pycoingecko import CoinGeckoAPI

# Bitstamp API credentials
BITSTAMP_API_KEY = 'jihKE0CWGln3A1mczdKTUoazcfqPnQSb'
BITSTAMP_API_SECRET = 'FNxEXCRiJaEOC6BXmJ7KIvK7imZ6GRKP'
BITSTAMP_CUSTOMER_ID = 'jklv7730'

def bitstamp_request(endpoint, params=None):
    """Make a request to the Bitstamp API."""
    url = f'https://www.bitstamp.net/api/v2/{endpoint}/'
    nonce = str(int(time.time() * 1000))
    message = nonce + BITSTAMP_CUSTOMER_ID + BITSTAMP_API_KEY
    signature = hmac.new(
        BITSTAMP_API_SECRET.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest().upper()
    data = {
        'key': BITSTAMP_API_KEY,
        'signature': signature,
        'nonce': nonce,
    }
    if params:
        data.update(params)
    response = requests.post(url, data=data)
    return response.json()

def get_fallback_price(asset):
    cg = CoinGeckoAPI()
    try:
        asset_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'USDT': 'tether',
            'SOL': 'solana',
            'FLR': 'flare-networks',
            'STRK': 'starknet',
        }
        asset_id = asset_map.get(asset.upper(), asset.lower())
        price = cg.get_price(ids=asset_id, vs_currencies='usd')
        return float(price[asset_id]['usd']) if asset_id in price and 'usd' in price[asset_id] else 0.0
    except Exception as e:
        print(f"[WARN] CoinGecko price fetch failed for {asset}: {e}")
        return 0.0

def get_bitstamp_balances():
    response = bitstamp_request('balance')
    if 'error' in response:
        print("Bitstamp API error:", response['error'])
        return []
    asset_totals = {}
    # Only use *_balance fields for asset amounts, skip fee/withdrawal_fee
    for field, amount in response.items():
        if not field.endswith('_balance'):
            continue
        if field.endswith('_fee') or field.endswith('_withdrawal_fee'):
            continue
        asset = field[:-8]  # Remove '_balance'
        try:
            amount_f = float(amount)
        except Exception:
            continue
        # Treat ETH2 as ETH
        if asset.lower() == 'eth2':
            asset = 'eth'
        asset = asset.upper()
        if asset not in asset_totals:
            asset_totals[asset] = 0.0
        asset_totals[asset] += amount_f
    balances = []
    fiat_assets = {'USD', 'EUR', 'GBP', 'EURT', 'GUSD', 'USDC', 'ZUSD', 'EURC', 'EURCV', 'PYUSD', 'VCHF', 'VEUR', 'XSGD', 'RLUSD'}
    for asset, total in asset_totals.items():
        if total > 0:
            if asset.lower() in {x.lower() for x in fiat_assets} or not asset.isalpha() or len(asset) > 8:
                price = 1.0 if asset.lower() == 'usd' else 0.0
            else:
                # Try to fetch USD price from Bitstamp
                try:
                    ticker = bitstamp_request(f'ticker/{asset.lower()}usd')
                    price = float(ticker['last']) if 'last' in ticker else 0.0
                except Exception:
                    price = 0.0
                if price == 0.0:
                    price = get_fallback_price(asset)
                    if price == 0.0:
                        print(f"[WARN] No USD price found for {asset} (amount: {total})")
            usd_value = total * price
            balances.append({'exchange': 'Bitstamp', 'asset': asset, 'amount': total, 'price': price, 'usd_value': usd_value})
    return balances

if __name__ == '__main__':
    balances = get_bitstamp_balances()
    # Print all assets, even if price is 0
    if balances:
        print("Bitstamp Balances (all assets):")
        print("Asset      Amount          Price (USD)     Value (USD)")
        print("-------------------------------------------------------")
        for balance in balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f} ${balance.get('price', 0):<15.2f} ${balance.get('usd_value', 0):<15.2f}")
        total = sum(balance.get('usd_value', 0) for balance in balances)
        print("-------------------------------------------------------")
        print(f"TOTAL                                      ${total:<15.2f}")
    else:
        print("No Bitstamp balances found.") 