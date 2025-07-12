from pybit.unified_trading import HTTP
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import hmac
import json
import time
import hashlib

import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_bybit_balances(api_key: str, api_secret: str, testnet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch all balances from Bybit account.
    
    Args:
        api_key (str): Bybit API key
        api_secret (str): Bybit API secret
        testnet (bool): Whether to use testnet or mainnet
        
    Returns:
        List[Dict[str, Any]]: List of balances with asset, amount, and USD value
    """
    try:
        # Initialize Bybit client
        session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )
        
        # Get wallet balance for all coins
        response = session.get_wallet_balance(
            accountType="UNIFIED"
        )
        
        if response['retCode'] != 0:
            logger.error(f"Error getting Bybit balances: {response['retMsg']}")
            return []
            
        balances = []
        for coin in response['result']['list'][0]['coin']:
            total = float(coin['walletBalance'])
            if total > 0:
                balances.append({
                    'asset': coin['coin'],
                    'amount': total
                })
        
        return balances
        
    except Exception as e:
        logger.error(f"Error retrieving Bybit balances: {e}")
        return []

def get_bybit_funding_balances(api_key: str, api_secret: str, testnet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch all balances from Bybit Funding account using the correct endpoint.
    """
    try:
        session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )
        # Use the new endpoint for Funding account balances
        response = session.get_coins_balance(accountType="FUND")
        if response['retCode'] != 0:
            logger.error(f"Error getting Bybit Funding balances: {response['retMsg']}")
            return []
        balances = []
        # The response structure is result > balance (list of coins)
        for coin in response['result']['balance']:
            total = float(coin['walletBalance'])
            if total > 0:
                balances.append({
                    'asset': coin['coin'],
                    'amount': total
                })
        return balances
    except Exception as e:
        logger.error(f"Error retrieving Bybit Funding balances: {e}")
        return []

def get_bybit_earn_balances(api_key: str, api_secret: str, testnet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch all staked balances from Bybit On-Chain Earn using a manual REST API call.
    Note: This endpoint may not be available for all accounts or may require special permissions.
    Returns empty list if the endpoint is not accessible.
    """
    logger.info("Checking Bybit Earn (staked) balances...")
    try:
        # Manually construct the authenticated request
        base_url = "https://api.bybit.com" if not testnet else "https://api-testnet.bybit.com"
        endpoint = "/v5/earn/position"
        url = base_url + endpoint

        # Prepare request parameters
        timestamp = str(int(time.time() * 1000))
        recv_window = "20000"  # Bybit recommendation
        
        # Create the signature using the correct Bybit V5 format
        # For GET requests with no parameters, the signature string is: timestamp + api_key + recv_window
        sign_str = timestamp + api_key + recv_window
        signature = hmac.new(
            api_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            'X-BAPI-API-KEY': api_key,
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-SIGN': signature,
            'X-BAPI-RECV-WINDOW': recv_window,
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        if response_json.get('retCode') != 0:
            ret_msg = response_json.get('retMsg', 'Unknown error')
            
            # Check if it's a permissions or endpoint availability issue
            if 'Invalid parameter' in ret_msg:
                logger.info("Bybit Earn endpoint not available for this account (this is normal)")
            else:
                logger.warning(f"Bybit Earn API returned error: {ret_msg}")
            
            return []
            
        balances = []
        if 'result' in response_json and 'list' in response_json['result']:
            for position in response_json['result']['list']:
                total = float(position['amount'])
                if total > 0:
                    balances.append({
                        'asset': position['coin'],
                        'amount': total
                    })
        
        if balances:
            logger.info(f"Successfully fetched {len(balances)} Earn positions")
        else:
            logger.info("No Earn positions found")
        return balances
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error retrieving Bybit Earn balances: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving Bybit Earn balances: {e}")
        return []

def get_all_bybit_balances(api_key: str, api_secret: str, testnet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetches all balances from Bybit (Unified, Funding, and Earn) and combines them.
    """
    all_balances = []
    all_balances.extend(get_bybit_balances(api_key, api_secret, testnet))
    all_balances.extend(get_bybit_funding_balances(api_key, api_secret, testnet))
    all_balances.extend(get_bybit_earn_balances(api_key, api_secret, testnet))
    return all_balances

if __name__ == '__main__':
    # Bybit API credentials
    api_key = '3hqwkcMjnyhnFUd6XE'
    api_secret = 'OQVX53FdiY4LMztOZAzYxD3UjS93mFpV3XfK'
    
    print("\nFetching Bybit Unified account balances...\n")
    balances = get_bybit_balances(api_key, api_secret)
    if not balances:
        print("No Unified account balances found or error occurred.")
    else:
        print(f"{'Asset':<10} {'Amount':<15}")
        print("-" * 25)
        for balance in balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f}")
        print("-" * 25)
        print(f"Found {len(balances)} assets in Unified account\n")

    print("\nFetching Bybit Funding account balances...\n")
    funding_balances = get_bybit_funding_balances(api_key, api_secret)
    if not funding_balances:
        print("No Funding account balances found or error occurred.")
    else:
        print(f"{'Asset':<10} {'Amount':<15}")
        print("-" * 25)
        for balance in funding_balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f}")
        print("-" * 25)
        print(f"Found {len(funding_balances)} assets in Funding account\n")

    print("\nFetching Bybit Earn (staked) balances...\n")
    earn_balances = get_bybit_earn_balances(api_key, api_secret)
    if not earn_balances:
        print("No Earn (staked) balances found or error occurred.")
    else:
        print(f"{'Asset':<10} {'Amount':<15}")
        print("-" * 25)
        for balance in earn_balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f}")
        print("-" * 25)
        print(f"Found {len(earn_balances)} assets in Earn account\n")

    print("\nFetching ALL Bybit balances (combined)...\n")
    all_balances = get_all_bybit_balances(api_key, api_secret)
    if not all_balances:
        print("No balances found or error occurred.")
    else:
        print(f"{'Asset':<10} {'Amount':<15} {'Source':<15}")
        print("-" * 40)
        
        # Group by source for better display
        unified_count = len(get_bybit_balances(api_key, api_secret))
        funding_count = len(get_bybit_funding_balances(api_key, api_secret))
        earn_count = len(get_bybit_earn_balances(api_key, api_secret))
        
        for i, balance in enumerate(all_balances):
            if i < unified_count:
                source = "Unified"
            elif i < unified_count + funding_count:
                source = "Funding"
            else:
                source = "Earn"
            
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f} {source:<15}")
        
        print("-" * 40)
        print(f"Total: {len(all_balances)} assets across all Bybit accounts\n") 