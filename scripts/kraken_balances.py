import time
import requests
import base64
import hashlib
import hmac
import os

KRAKEN_API_KEY = 'lnlMNYd+mD3zRHw0IcBRkBAycn+SOFjhrbSj9yvHXwn3yPiys8BYST47'
KRAKEN_API_SECRET = 'NmvhB+59u58ZDke+nqKD6RU8FxmqWk2VLDpKZCqttIdQ6PrI0ukY86KqHpbLn62jndenrLggVB36q1+ZsCvXMQ=='

KRAKEN_ASSET_MAP = {
    'XBT': 'BTC',
    'XETH': 'ETH',
    'ZEUR': 'EUR',
    'ZUSD': 'USD',
    'USDT': 'USDT',
    'DOT': 'DOT',
    'ADA': 'ADA',
    'SOL': 'SOL',
    'MATIC': 'MATIC',
    'LINK': 'LINK',
    'UNI': 'UNI',
    'AAVE': 'AAVE',
    'ALGO': 'ALGO',
    'ATOM': 'ATOM',
    'AVAX': 'AVAX',
    'BCH': 'BCH',
    'DASH': 'DASH',
    'EOS': 'EOS',
    'LTC': 'LTC',
    'XRP': 'XRP',
    'XTZ': 'XTZ',
    'YFI': 'YFI',
    'ZEC': 'ZEC'
}

def get_kraken_nonce():
    return str(int(time.time() * 1000))

def kraken_request(url, data, api_key, api_secret):
    nonce = get_kraken_nonce()
    data['nonce'] = nonce
    post_data = '&'.join([f'{k}={v}' for k, v in data.items()])
    path = url.split('kraken.com')[1]
    secret = base64.b64decode(api_secret)
    hash_digest = hashlib.sha256((nonce + post_data).encode()).digest()
    hmac_digest = hmac.new(secret, (path.encode() + hash_digest), hashlib.sha512).digest()
    signature = base64.b64encode(hmac_digest)
    headers = {
        'API-Key': api_key,
        'API-Sign': signature.decode(),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    response = requests.post(url, data=data, headers=headers)
    return response.json()

def get_kraken_asset_pairs():
    """Fetch Kraken asset pairs and build a mapping from (base, quote) to Kraken pair code."""
    url = 'https://api.kraken.com/0/public/AssetPairs'
    response = requests.get(url)
    data = response.json()
    mapping = {}
    if 'result' in data:
        for pair_code, info in data['result'].items():
            base = info['base']
            quote = info['quote']
            mapping[(base, quote)] = pair_code
    return mapping

def get_kraken_balances():
    url = 'https://api.kraken.com/0/private/Balance'
    data = {}
    response = kraken_request(url, data, KRAKEN_API_KEY, KRAKEN_API_SECRET)
    print("Kraken Balance API Response:", response)
    if 'error' in response and response['error']:
        print("Kraken API error:", response['error'])
        return []
    if 'result' not in response:
        print("Unexpected Kraken response:", response)
        return []
    balances = []
    btc_reserve = 0.0
    btc_codes = ['XBT.F', 'XBT.M', 'XBT.B']  # Include Earn BTC (XBT.B)
    btc_amounts = {}
    for asset, amount in response['result'].items():
        if float(amount) > 0:
            symbol = KRAKEN_ASSET_MAP.get(asset, asset)
            if asset in btc_codes:
                btc_reserve += float(amount)
                btc_amounts[asset] = float(amount)
            else:
                balances.append({'exchange': 'Kraken', 'asset': symbol, 'kraken_code': asset, 'amount': float(amount)})
    # Add combined BTC reserve
    if btc_reserve > 0:
        balances.insert(0, {'exchange': 'Kraken', 'asset': 'BTC', 'kraken_code': 'XBT.F', 'amount': btc_reserve, 'btc_breakdown': btc_amounts})
    # Get current prices for all assets from Kraken public API
    if balances:
        asset_pairs = get_kraken_asset_pairs()
        pairs = []
        pair_map = {}
        for b in balances:
            base = b['kraken_code']
            quote = 'ZUSD'  # Kraken's code for USD
            pair_code = asset_pairs.get((base, quote))
            # For combined BTC, try XBT.FZUSD, then XBT.MZUSD
            if b['asset'] == 'BTC':
                pair_code = asset_pairs.get(('XBT.F', 'ZUSD')) or asset_pairs.get(('XBT.M', 'ZUSD'))
            if pair_code:
                pairs.append(pair_code)
                pair_map[pair_code] = b
        if pairs:
            price_url = 'https://api.kraken.com/0/public/Ticker'
            price_data = {'pair': ','.join(pairs)}
            price_response = requests.get(price_url, params=price_data)
            price_data = price_response.json()
            print("Kraken Price API Response:", price_data)
            if 'result' in price_data:
                for pair_code in pairs:
                    balance = pair_map[pair_code]
                    if pair_code in price_data['result']:
                        price = float(price_data['result'][pair_code]['c'][0])
                        balance['price'] = price
                        balance['value'] = balance['amount'] * price
                    else:
                        print(f"No price found for pair {pair_code}")
            else:
                print("No price data found in response.")
        else:
            print("No valid asset pairs found for price lookup.")
    return balances

def get_kraken_staking_balances():
    """Fetch balances held in Kraken Earn (staking/yield) via the private Staking/Assets endpoint."""
    url = 'https://api.kraken.com/0/private/Staking/Assets'
    data = {}
    response = kraken_request(url, data, KRAKEN_API_KEY, KRAKEN_API_SECRET)
    print("Kraken Staking API Response:", response)
    return response

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

if __name__ == '__main__':
    balances_from_kraken = get_kraken_balances()
    if not balances_from_kraken:
        print("No assets found on Kraken.")
    else:
        # Create a unified list with a symbol for CMC lookup
        processed_balances = []
        for b in balances_from_kraken:
            # Handle cases where price/value might be missing
            if 'amount' not in b:
                continue
            
            asset = b['asset']
            # Use the part before the dot for a cleaner symbol, default to asset name
            cmc_symbol = asset.split('.')[0]
            if cmc_symbol == 'XBT':
                cmc_symbol = 'BTC'
            
            processed_balances.append({
                'asset': asset,
                'amount': b['amount'],
                'cmc_symbol': cmc_symbol
            })

        # Fetch prices from CoinMarketCap
        symbols_to_fetch = [b['cmc_symbol'] for b in processed_balances]
        prices = get_prices(symbols_to_fetch)

        print(f"{'Asset':<10} {'Amount':<15} {'Price (USD)':<15} {'Value (USD)':<15}")
        print("-" * 55)
        total_value = 0
        for b in processed_balances:
            price = prices.get(b['cmc_symbol'], 0.0)
            value = b['amount'] * price
            total_value += value
            print(f"{b['asset']:<10} {b['amount']:<15.8f} ${price:<14.2f} ${value:<14.2f}")
        print("-" * 55)
        print(f"{'TOTAL':<10} {'':<15} {'':<15} ${total_value:<14.2f}")

    # --- Print Kraken Earn (staking) balances ---
    get_kraken_staking_balances() 