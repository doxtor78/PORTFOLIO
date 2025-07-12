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
        except (ValueError, TypeError):
            continue
        
        # Treat ETH2 as ETH
        if asset.lower() == 'eth2':
            asset = 'eth'
        asset = asset.upper()

        asset_totals[asset] = asset_totals.get(asset, 0.0) + amount_f

    balances = []
    for asset, total in asset_totals.items():
        if total > 0:
            # Only return the asset and amount. Price and value will be handled centrally.
            balances.append({'asset': asset, 'amount': total})
            
    return balances

if __name__ == '__main__':
    # This part remains for standalone testing, but will now show incomplete data.
    balances = get_bitstamp_balances()
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