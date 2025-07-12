import os
import json
import time
import hmac
import hashlib
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

# Bitfinex API credentials
BITFINEX_API_KEY = 'cbb2e86f32e6b4256478f1d38bd8e88d725e6312940'
BITFINEX_API_SECRET = '171522474c91db9e7b144528d6cd82ffc10a4603114'
COINMARKETCAP_API_KEY = '2a83a14e-7f99-4dce-ab96-3a0d1f8ddf8b'


def get_prices(symbols):
    filtered_symbols = [s for s in symbols if s.isalpha() and s.isupper() and len(s) <= 10]
    if not filtered_symbols:
        return {}
    headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
    params = {'symbol': ','.join(set(s.upper() for s in filtered_symbols))}
    try:
        response = requests.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest', headers=headers, params=params)
        response.raise_for_status()
        response_json = response.json()
        prices = {}
        if response_json.get('status', {}).get('error_code') == 0 and 'data' in response_json:
            data = response_json['data']
            for symbol_upper in data:
                item = data[symbol_upper][0] if isinstance(data[symbol_upper], list) else data[symbol_upper]
                price = item['quote']['USD']['price']
                for original_symbol in symbols:
                    if original_symbol.upper() == symbol_upper:
                        prices[original_symbol] = price
        return prices
    except Exception as e:
        print(f"Error fetching prices from CoinMarketCap: {e}")
        return {}

def bitfinex_private_request(endpoint, api_key, api_secret, params={}):
    """Make a request to a private Bitfinex endpoint."""
    url = f'https://api.bitfinex.com/v1/{endpoint}'
    
    payload = {
        'request': f'/v1/{endpoint}',
        'nonce': str(int(time.time() * 1000))
    }
    payload.update(params)
    
    payload_base64 = base64.b64encode(json.dumps(payload).encode('utf-8'))
    
    signature = hmac.new(
        api_secret.encode('utf-8'),
        payload_base64,
        hashlib.sha384
    ).hexdigest()
    
    headers = {
        'X-BFX-APIKEY': api_key,
        'X-BFX-PAYLOAD': payload_base64,
        'X-BFX-SIGNATURE': signature
    }
    
    response = requests.post(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error calling Bitfinex API: {response.status_code} - {response.text}")
        return None

def get_bitfinex_balances(api_key, api_secret):
    """Fetch Bitfinex balances."""
    response = bitfinex_private_request('balances', api_key, api_secret)
    
    balances = []
    if response and isinstance(response, list):
        for balance in response:
            if balance.get('type') == 'exchange' and float(balance.get('amount', 0)) > 0:
                balances.append({
                    'exchange': 'Bitfinex',
                    'asset': balance['currency'].upper(),
                    'amount': float(balance['amount'])
                })
    return balances

if __name__ == '__main__':
    balances = get_bitfinex_balances(BITFINEX_API_KEY, BITFINEX_API_SECRET)
    if not balances:
        print("No Bitfinex balances found.")
    else:
        symbols = [b['asset'] for b in balances]
        prices = get_prices(symbols)
        
        print("Bitfinex Balances:")
        print(f"{'Asset':<10} {'Amount':<15} {'Price (USD)':<15} {'Value (USD)':<15}")
        print("-" * 55)
        total_value = 0
        for b in balances:
            price = prices.get(b['asset'], 0.0)
            if price is None:  # Add a check for None
                price = 0.0
            value = b['amount'] * price
            total_value += value
            print(f"{b['asset']:<10} {b['amount']:<15.8f} ${price:<14.2f} ${value:<14.2f}")
        print("-" * 55)
        print(f"{'TOTAL':<10} {'':<15} {'':<15} ${total_value:<14.2f}") 