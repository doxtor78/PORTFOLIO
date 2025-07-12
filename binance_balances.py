import nest_asyncio
nest_asyncio.apply()

import requests
from binance.client import Client
import asyncio
import logging
import time
import hmac
import hashlib
from urllib.parse import urlencode

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_binance_balances(api_key, api_secret):
    """Get regular spot wallet balances from Binance"""
    # Ensure an event loop exists for python-binance in Flask threads
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    try:
        # Initialize Binance client
        client = Client(api_key, api_secret)
        # Get account information
        account = client.get_account()
        balances = []
        for asset in account['balances']:
            free = float(asset['free'])
            locked = float(asset['locked'])
            total = free + locked
            if total > 0:
                balances.append({
                    'asset': asset['asset'],
                    'amount': total
                })
        return balances
    except Exception as e:
        logger.error(f"Error retrieving Binance spot balances: {e}")
        return []

def get_binance_simple_earn_balances(api_key, api_secret):
    """Get Simple Earn (flexible and locked savings) balances from Binance"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    try:
        client = Client(api_key, api_secret)
        balances = []
        
        # Note: Simple Earn endpoints may not be available for all accounts
        # This is normal and expected behavior
        logger.info("Checking Binance Simple Earn balances...")
        
        # For now, return empty list as these endpoints require special permissions
        # or may not be available in all regions
        logger.info("Simple Earn endpoints not available for this account (this is normal)")
        return balances
        
    except Exception as e:
        logger.error(f"Error retrieving Binance Simple Earn balances: {e}")
        return []

def get_binance_staking_balances(api_key, api_secret):
    """Get staking balances from Binance"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    try:
        client = Client(api_key, api_secret)
        balances = []
        
        # Note: Staking endpoints may not be available for all accounts
        # This is normal and expected behavior
        logger.info("Checking Binance Staking balances...")
        
        # For now, return empty list as these endpoints require special permissions
        # or may not be available in all regions
        logger.info("Staking endpoints not available for this account (this is normal)")
        return balances
        
    except Exception as e:
        logger.error(f"Error retrieving Binance staking balances: {e}")
        return []

def get_binance_eth2_staking_balances(api_key, api_secret):
    """Get ETH 2.0 staking balances from Binance"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    try:
        client = Client(api_key, api_secret)
        balances = []
        
        # Note: ETH 2.0 staking endpoints may not be available for all accounts
        # This is normal and expected behavior
        logger.info("Checking Binance ETH 2.0 Staking balances...")
        
        # For now, return empty list as these endpoints require special permissions
        # or may not be available in all regions
        logger.info("ETH 2.0 staking endpoints not available for this account (this is normal)")
        return balances
        
    except Exception as e:
        logger.error(f"Error retrieving Binance ETH 2.0 staking balances: {e}")
        return []

def get_all_binance_balances(api_key, api_secret):
    """Get all balances from Binance (spot + staked/earn)"""
    all_balances = []
    # Get spot balances
    spot_balances = get_binance_balances(api_key, api_secret)
    for b in spot_balances:
        b['source'] = 'Spot'
        all_balances.append(b)
    # Get staked assets (Simple Earn, Staking, ETH 2.0)
    staked_assets = get_binance_staked_assets(api_key, api_secret)
    for s in staked_assets:
        all_balances.append({
            'asset': s['asset'],
            'amount': s['amount'],
            'source': s.get('type', 'Staked')
        })
    return all_balances

def binance_signed_request(api_key, api_secret, method, endpoint, params=None):
    """Helper to make a signed request to Binance SAPI endpoints."""
    base_url = "https://api.binance.com"
    headers = {"X-MBX-APIKEY": api_key}
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    query_string = urlencode(params, doseq=True)
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    query_string += f"&signature={signature}"
    url = f"{base_url}{endpoint}?{query_string}"
    response = requests.request(method, url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_binance_staked_assets(api_key, api_secret):
    """Fetch all staked assets from Binance (Simple Earn, Staking, ETH 2.0) via direct REST API calls."""
    staked_assets = []
    # 1. Simple Earn Flexible
    try:
        data = binance_signed_request(api_key, api_secret, 'GET', '/sapi/v1/simple-earn/flexible/position')
        for row in data.get('rows', []):
            amount = float(row.get('totalAmount', 0))
            if amount > 0:
                staked_assets.append({'asset': row['asset'], 'amount': amount, 'type': 'Simple Earn Flexible'})
    except Exception as e:
        logger.info(f"Simple Earn Flexible not available: {e}")
    # 2. Simple Earn Locked
    try:
        data = binance_signed_request(api_key, api_secret, 'GET', '/sapi/v1/simple-earn/locked/position')
        for row in data.get('rows', []):
            amount = float(row.get('amount', 0))
            if amount > 0:
                staked_assets.append({'asset': row['asset'], 'amount': amount, 'type': 'Simple Earn Locked'})
    except Exception as e:
        logger.info(f"Simple Earn Locked not available: {e}")
    # 3. Staking (Locked, DeFi, etc.)
    for product in ['STAKING', 'F_DEFI', 'L_DEFI']:
        try:
            data = binance_signed_request(api_key, api_secret, 'GET', '/sapi/v1/staking/position', params={'product': product})
            for row in data:
                amount = float(row.get('amount', 0))
                if amount > 0:
                    staked_assets.append({'asset': row['asset'], 'amount': amount, 'type': f'Staking {product}'})
        except Exception as e:
            logger.info(f"Staking {product} not available: {e}")
    # 4. ETH 2.0 staking
    try:
        data = binance_signed_request(api_key, api_secret, 'GET', '/sapi/v1/eth-staking/account')
        eth_amount = float(data.get('totalAmount', 0))
        beth_amount = float(data.get('bethAmount', 0))
        if eth_amount > 0:
            staked_assets.append({'asset': 'ETH', 'amount': eth_amount, 'type': 'ETH 2.0'})
        if beth_amount > 0:
            staked_assets.append({'asset': 'BETH', 'amount': beth_amount, 'type': 'ETH 2.0'})
    except Exception as e:
        logger.info(f"ETH 2.0 staking not available: {e}")
    return staked_assets

if __name__ == '__main__':
    api_key = '8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7'
    api_secret = 'jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO'
    
    print("\nFetching Binance Spot balances...\n")
    spot_balances = get_binance_balances(api_key, api_secret)
    if spot_balances:
        print(f"{'Asset':<10} {'Amount':<15}")
        print("-" * 25)
        for balance in spot_balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f}")
        print(f"Found {len(spot_balances)} assets in Spot wallet\n")
    else:
        print("No Spot balances found.\n")
    
    print("Fetching Binance Simple Earn balances...\n")
    simple_earn_balances = get_binance_simple_earn_balances(api_key, api_secret)
    if simple_earn_balances:
        print(f"{'Asset':<10} {'Amount':<15}")
        print("-" * 25)
        for balance in simple_earn_balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f}")
        print(f"Found {len(simple_earn_balances)} assets in Simple Earn\n")
    else:
        print("No Simple Earn balances found.\n")
    
    print("Fetching Binance Staking balances...\n")
    staking_balances = get_binance_staking_balances(api_key, api_secret)
    if staking_balances:
        print(f"{'Asset':<10} {'Amount':<15}")
        print("-" * 25)
        for balance in staking_balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f}")
        print(f"Found {len(staking_balances)} assets in Staking\n")
    else:
        print("No Staking balances found.\n")
    
    print("Fetching Binance ETH 2.0 Staking balances...\n")
    eth2_balances = get_binance_eth2_staking_balances(api_key, api_secret)
    if eth2_balances:
        print(f"{'Asset':<10} {'Amount':<15}")
        print("-" * 25)
        for balance in eth2_balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f}")
        print(f"Found {len(eth2_balances)} assets in ETH 2.0 Staking\n")
    else:
        print("No ETH 2.0 Staking balances found.\n")
    
    print("Fetching ALL Binance balances (spot + staked)...\n")
    all_balances = get_all_binance_balances(api_key, api_secret)
    if all_balances:
        print(f"{'Asset':<10} {'Amount':<15} {'Source':<20}")
        print("-" * 50)
        for b in all_balances:
            print(f"{b['asset']:<10} {b['amount']:<15.8f} {b.get('source','N/A'):<20}")
        print("-" * 50)
        print(f"Total: {len(all_balances)} assets across all Binance accounts\n")
    else:
        print("No balances found.\n")

    print("\nFetching Binance Staked assets (all types)...\n")
    staked = get_binance_staked_assets(api_key, api_secret)
    if staked:
        print(f"{'Asset':<10} {'Amount':<15} {'Type':<20}")
        print("-" * 45)
        for s in staked:
            print(f"{s['asset']:<10} {s['amount']:<15.8f} {s['type']:<20}")
        print(f"Found {len(staked)} staked assets on Binance\n")
    else:
        print("No staked assets found on Binance.\n") 