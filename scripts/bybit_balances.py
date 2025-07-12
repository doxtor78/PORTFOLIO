from pybit.unified_trading import HTTP
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

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
                # Get current price for the coin
                try:
                    ticker_response = session.get_tickers(
                        category="spot",
                        symbol=f"{coin['coin']}USDT"
                    )
                    if ticker_response['retCode'] == 0 and ticker_response['result']['list']:
                        price = float(ticker_response['result']['list'][0]['lastPrice'])
                    else:
                        # If no USDT pair, try USD
                        ticker_response = session.get_tickers(
                            category="spot",
                            symbol=f"{coin['coin']}USD"
                        )
                        if ticker_response['retCode'] == 0 and ticker_response['result']['list']:
                            price = float(ticker_response['result']['list'][0]['lastPrice'])
                        else:
                            price = 1.0 if coin['coin'] in ['USDT', 'USDC', 'USD'] else 0.0
                except Exception as e:
                    logger.error(f"Error getting price for {coin['coin']}: {e}")
                    price = 1.0 if coin['coin'] in ['USDT', 'USDC', 'USD'] else 0.0
                
                usd_value = total * price
                if usd_value > 0:
                    balances.append({
                        'exchange': 'Bybit',
                        'asset': coin['coin'],
                        'amount': total,
                        'price': price,
                        'usd_value': usd_value
                    })
        
        # Sort balances by USD value
        balances.sort(key=lambda x: x['usd_value'], reverse=True)
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
                try:
                    ticker_response = session.get_tickers(
                        category="spot",
                        symbol=f"{coin['coin']}USDT"
                    )
                    if ticker_response['retCode'] == 0 and ticker_response['result']['list']:
                        price = float(ticker_response['result']['list'][0]['lastPrice'])
                    else:
                        ticker_response = session.get_tickers(
                            category="spot",
                            symbol=f"{coin['coin']}USD"
                        )
                        if ticker_response['retCode'] == 0 and ticker_response['result']['list']:
                            price = float(ticker_response['result']['list'][0]['lastPrice'])
                        else:
                            price = 1.0 if coin['coin'] in ['USDT', 'USDC', 'USD'] else 0.0
                except Exception as e:
                    logger.error(f"Error getting price for {coin['coin']} (Funding): {e}")
                    price = 1.0 if coin['coin'] in ['USDT', 'USDC', 'USD'] else 0.0
                usd_value = total * price
                if usd_value > 0:
                    balances.append({
                        'exchange': 'Bybit',
                        'asset': coin['coin'],
                        'amount': total,
                        'price': price,
                        'usd_value': usd_value
                    })
        balances.sort(key=lambda x: x['usd_value'], reverse=True)
        return balances
    except Exception as e:
        logger.error(f"Error retrieving Bybit Funding balances: {e}")
        return []

if __name__ == '__main__':
    # Bybit API credentials
    api_key = '3hqwkcMjnyhnFUd6XE'
    api_secret = 'OQVX53FdiY4LMztOZAzYxD3UjS93mFpV3XfK'
    
    print("\nFetching Bybit Unified account balances...\n")
    balances = get_bybit_balances(api_key, api_secret)
    if not balances:
        print("No Unified account balances found or error occurred.")
    else:
        total_value = sum(balance['usd_value'] for balance in balances)
        print(f"{'Asset':<10} {'Amount':<15} {'Price (USD)':<15} {'Value (USD)':<15}")
        print("-" * 55)
        for balance in balances:
            print(f"{balance['asset']:<10} "
                  f"{balance['amount']:<15.8f} "
                  f"${balance['price']:<14.2f} "
                  f"${balance['usd_value']:<14.2f}")
        print("-" * 55)
        print(f"{'TOTAL':<10} {'':<15} {'':<15} ${total_value:<14.2f}\n")
        # --- Pandas visualization ---
        df = pd.DataFrame(balances)
        if not df.empty:
            df_sorted = df.sort_values(by='usd_value', ascending=False)
            print("\nUnified Account Balances (pandas DataFrame):")
            print(df_sorted.to_string(index=False, float_format='%.8f'))
            print(f"\nTOTAL (pandas): ${df_sorted['usd_value'].sum():.2f}\n")

    print("\nFetching Bybit Funding account balances...\n")
    funding_balances = get_bybit_funding_balances(api_key, api_secret)
    if not funding_balances:
        print("No Funding account balances found or error occurred.")
    else:
        total_funding_value = sum(balance['usd_value'] for balance in funding_balances)
        print(f"{'Asset':<10} {'Amount':<15} {'Price (USD)':<15} {'Value (USD)':<15}")
        print("-" * 55)
        for balance in funding_balances:
            print(f"{balance['asset']:<10} "
                  f"{balance['amount']:<15.8f} "
                  f"${balance['price']:<14.2f} "
                  f"${balance['usd_value']:<14.2f}")
        print("-" * 55)
        print(f"{'TOTAL':<10} {'':<15} {'':<15} ${total_funding_value:<14.2f}\n") 
        # --- Pandas visualization ---
        df_fund = pd.DataFrame(funding_balances)
        if not df_fund.empty:
            df_fund_sorted = df_fund.sort_values(by='usd_value', ascending=False)
            print("\nFunding Account Balances (pandas DataFrame):")
            print(df_fund_sorted.to_string(index=False, float_format='%.8f'))
            print(f"\nTOTAL (pandas): ${df_fund_sorted['usd_value'].sum():.2f}\n") 