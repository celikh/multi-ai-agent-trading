#!/usr/bin/env python3
"""
Exchange API Connection Test
Tests Binance API connectivity with configured credentials
"""

import ccxt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_binance_connection():
    """Test Binance API connection"""

    print("🔌 Testing Binance API Connection...")
    print("=" * 60)

    # Initialize Binance
    binance = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
    })

    try:
        # Load markets
        print("\n📡 Loading markets...")
        markets = binance.load_markets()
        print(f'✅ Binance connection successful!')
        print(f'📊 Total markets available: {len(markets)}')

        # Fetch BTC/USDT ticker
        print("\n📈 Fetching market data...")
        btc_ticker = binance.fetch_ticker('BTC/USDT')
        print(f'BTC/USDT: ${btc_ticker["last"]:,.2f}')

        # Fetch ETH/USDT ticker
        eth_ticker = binance.fetch_ticker('ETH/USDT')
        print(f'ETH/USDT: ${eth_ticker["last"]:,.2f}')

        # Fetch account balance (if available)
        print("\n💰 Fetching account balance...")
        try:
            balance = binance.fetch_balance()
            total_balance = balance.get('total', {})

            # Show non-zero balances
            non_zero = {k: v for k, v in total_balance.items() if v > 0}
            if non_zero:
                print("Account balances:")
                for asset, amount in non_zero.items():
                    print(f"  {asset}: {amount:,.8f}")
            else:
                print("No balances found (possibly testnet or new account)")

        except Exception as e:
            print(f"Balance fetch failed: {str(e)}")
            print("(This is normal for API keys without trading permissions)")

        print("\n" + "=" * 60)
        print("✅ Exchange API test SUCCESSFUL!")
        print("=" * 60)
        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Connection failed: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_binance_connection()
    exit(0 if success else 1)
