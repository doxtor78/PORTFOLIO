import sys
import os
from dotenv import load_dotenv
from tabulate import tabulate
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the 'scripts' directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

# Import balance fetching functions from scripts
from binance_balances import get_all_binance_balances
from bybit_balances import get_all_bybit_balances
from kraken_balances import get_kraken_balances, get_prices as get_cmc_prices
from bitmex_balances import get_bitmex_balances
from bitfinex_balances import get_bitfinex_balances
from bitstamp_balances import get_bitstamp_balances

# --- API Credentials ---
load_dotenv()
BINANCE_API_KEY = '8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7'
BINANCE_API_SECRET = 'jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO'
BYBIT_API_KEY = '3hqwkcMjnyhnFUd6XE'
BYBIT_API_SECRET = 'OQVX53FdiY4LMztOZAzYxD3UjS93mFpV3XfK'
BITFINEX_API_KEY = 'cbb2e86f32e6b4256478f1d38bd8e88d725e6312940'
BITFINEX_API_SECRET = '171522474c91db9e7b144528d6cd82ffc10a4603114'

# --- Asset Groups (Consolidated) ---
BTC_GROUP = ['BTC', 'XBT']
STABLECOIN_GROUP = ['USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDP', 'FDUSD', 'USD', 'UST']
MAJOR_ASSETS = ['BTC', 'ETH', 'BNB']

# The get_all_balances function is removed as its logic is now in main.

def display_portfolio(all_assets):
    """
    Displays the consolidated portfolio in a single formatted table,
    sorted by BTC, then stablecoins, then other altcoins.
    """
    headers = ["Asset", "Amount", "Price", "Value (USD)", "Exchange"]

    # Filter out assets with a value of less than $0.01
    valuable_assets = [asset for asset in all_assets if asset.get('value', 0.0) >= 0.01]

    if not valuable_assets:
        print("No assets with a value greater than $0.01 found.")
        return

    def get_sort_key(asset):
        asset_name = asset.get('asset')
        value = asset.get('value', 0.0)

        if asset_name in BTC_GROUP:
            return (0, -value)  # Group 0: BTC, sorted by value descending
        if asset_name in STABLECOIN_GROUP:
            return (1, -value)  # Group 1: Stablecoins, sorted by value descending
        if asset_name == 'ETH':
            return (2, -value)  # Group 2: ETH
        return (3, -value)      # Group 3: Other altcoins, sorted by value descending

    # Sort all assets using the custom sort key
    valuable_assets.sort(key=get_sort_key)

    # Calculate total portfolio value from the original list to ensure accuracy
    total_value = sum(
        asset.get('value', 0.0) 
        for asset in all_assets 
        if isinstance(asset.get('value'), (int, float))
    )

    print("\n" + "="*80)
    print("--- Consolidated Portfolio ---".center(80))
    print("="*80)

    # Convert list of dicts to list of lists for tabulate
    table_data = [
        [
            d.get('asset', 'N/A'),
            d.get('amount', 0.0),
            d.get('price', 0.0),
            d.get('value', 0.0),
            d.get('exchange', 'N/A')
        ] for d in valuable_assets
    ]

    print(tabulate(table_data, headers=headers, floatfmt=(".8f", ",.2f", ",.2f", ",.2f"), numalign="right"))
    
    print("\n" + "-"*80)
    print(f"Total Portfolio Value: ${total_value:,.2f}".center(80))
    print("-" * 80)

    # --- Asset Sums Section ---
    asset_sums = {}
    stablecoin_sum = 0.0
    # Calculate BTC sum for all exchanges except BitMEX
    btc_other_sum = 0.0
    for asset in all_assets:
        symbol = asset.get('asset')
        amount = asset.get('amount', 0.0)
        exchange = asset.get('exchange', '')
        if symbol == 'BTC' and exchange != 'BitMEX':
            btc_other_sum += amount
        if symbol in MAJOR_ASSETS:
            asset_sums[symbol] = asset_sums.get(symbol, 0.0) + amount
        elif symbol in STABLECOIN_GROUP:
            stablecoin_sum += amount
    print("\n" + "="*80)
    print("--- Asset Sums Across All Exchanges ---".center(80))
    print("="*80)
    for symbol in MAJOR_ASSETS:
        if symbol in asset_sums:
            print(f"Total {symbol}: {asset_sums[symbol]:,.8f}")
            if symbol == 'BTC':
                print(f"Total other BTC (excluding BitMEX): {btc_other_sum:,.8f}")
    print(f"Total Stablecoins (USD, USDT, USDC, etc.): {stablecoin_sum:,.8f}")
    print("="*80)


def main():
    """
    Main function to fetch all balances and display the portfolio.
    """
    # Define a lambda to wrap functions that need API keys
    def with_keys(func, key, secret):
        return lambda: func(key, secret)

    exchange_functions = {
        "Binance": with_keys(get_all_binance_balances, BINANCE_API_KEY, BINANCE_API_SECRET),
        "Bybit": with_keys(get_all_bybit_balances, BYBIT_API_KEY, BYBIT_API_SECRET),
        "Bitstamp": get_bitstamp_balances,
        "Kraken": get_kraken_balances,
        "Bitfinex": with_keys(get_bitfinex_balances, BITFINEX_API_KEY, BITFINEX_API_SECRET),
        "BitMEX": get_bitmex_balances,
    }

    raw_assets = []
    with ThreadPoolExecutor(max_workers=len(exchange_functions)) as executor:
        future_to_exchange = {executor.submit(func): name for name, func in exchange_functions.items()}
        print("Fetching balances from all exchanges...")
        for future in as_completed(future_to_exchange):
            exchange_name = future_to_exchange[future]
            try:
                balances = future.result()
                if balances:
                    for balance in balances:
                        # Only collect asset and amount initially
                        raw_assets.append({
                            'asset': balance.get('asset'),
                            'amount': balance.get('amount', 0.0),
                            'exchange': exchange_name
                        })
                print(f"Successfully fetched balances from {exchange_name}.")
            except Exception as e:
                print(f"Error fetching balances from {exchange_name}: {e}")

    # Centralized price fetching for all collected assets
    symbols_to_fetch = list(set(b['asset'] for b in raw_assets if b.get('asset')))
    
    print(f"\nFetching prices for {len(symbols_to_fetch)} unique assets...")
    prices = get_cmc_prices(symbols_to_fetch)
    print("Price fetching complete.")

    # Calculate values and build the final list of assets
    all_assets = []
    for asset in raw_assets:
        price = prices.get(asset['asset'], 0.0)
        if price is None:
            price = 0.0
        amount = asset.get('amount', 0.0)
        value = amount * price
        asset['price'] = price
        asset['value'] = value
        all_assets.append(asset)

    display_portfolio(all_assets)


if __name__ == '__main__':
    main()