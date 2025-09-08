import asyncio
import random
import logging
from typing import Dict, Any, List
from .base import BaseExchange


class XTExchange(BaseExchange):
    """XT exchange implementation for simulation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("XT", config)
        self.fee = config.get('fee', 0.001)  # 0.1% default fee
        self.logger = logging.getLogger(__name__)
        
        # Base prices for different assets (slightly different from OKX to create arbitrage opportunities)
        self.base_prices = {
            'BTC/USDT': 59800.0,
            'ETH/USDT': 2990.0,
            'BNB/USDT': 495.0,
            'ADA/USDT': 0.49,
            'DOT/USDT': 6.9
        }
        
        # Volatility levels for different assets
        self.volatilities = {
            'BTC/USDT': 0.0006,
            'ETH/USDT': 0.0012,
            'BNB/USDT': 0.0025,
            'ADA/USDT': 0.006,
            'DOT/USDT': 0.0035
        }
        
        # Counter to simulate new listings
        self.listing_counter = 0
        
    async def fetch_ticker(self, symbol: str = None) -> Dict[str, Any]:
        """Fetch current ticker data (simulated)"""
        symbol = symbol or self.symbol
        
        # Simulate price movement over time with a slight offset from OKX
        self.base_prices[symbol] += random.uniform(-self.base_prices[symbol]*0.01, self.base_prices[symbol]*0.01)  # Random walk
        # Keep price within reasonable bounds
        self.base_prices[symbol] = max(self.base_prices[symbol] * 0.5, min(self.base_prices[symbol] * 1.5, self.base_prices[symbol]))
        
        volatility = self.volatilities.get(symbol, 0.001)
        price_data = self._simulate_price_data(self.base_prices[symbol], volatility)
        
        return {
            'symbol': symbol,
            'bid': price_data['bid'],
            'ask': price_data['ask'],
            'last': price_data['last'],
            'timestamp': asyncio.get_event_loop().time()
        }
    
    async def fetch_order_book(self, symbol: str = None) -> Dict[str, Any]:
        """Fetch order book data (simulated)"""
        symbol = symbol or self.symbol
        ticker = await self.fetch_ticker(symbol)
        
        # Simulate order book with multiple levels
        order_book = {
            'symbol': symbol,
            'bids': [
                [ticker['bid'], random.uniform(0.1, 10.0)],  # [price, amount]
                [ticker['bid'] * 0.999, random.uniform(0.1, 10.0)],
                [ticker['bid'] * 0.998, random.uniform(0.1, 10.0)]
            ],
            'asks': [
                [ticker['ask'], random.uniform(0.1, 10.0)],  # [price, amount]
                [ticker['ask'] * 1.001, random.uniform(0.1, 10.0)],
                [ticker['ask'] * 1.002, random.uniform(0.1, 10.0)]
            ],
            'timestamp': asyncio.get_event_loop().time()
        }
        
        return order_book
    
    async def create_order(self, side: str, amount: float, price: float, symbol: str = None) -> Dict[str, Any]:
        """Create a new order (simulated)"""
        symbol = symbol or self.symbol
        # In simulation mode, all orders are filled immediately
        return {
            'id': f"xt_order_{random.randint(10000, 99999)}",
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'status': 'filled',
            'filled': amount,
            'remaining': 0.0,
            'timestamp': asyncio.get_event_loop().time()
        }
    
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance (simulated)"""
        # For simulation, we'll return a fixed balance
        return {
            'USDT': {
                'free': 10000.0,
                'used': 0.0,
                'total': 10000.0
            },
            'BTC': {
                'free': 1.0,
                'used': 0.0,
                'total': 1.0
            },
            'ETH': {
                'free': 10.0,
                'used': 0.0,
                'total': 10.0
            },
            'BNB': {
                'free': 20.0,
                'used': 0.0,
                'total': 20.0
            },
            'ADA': {
                'free': 1000.0,
                'used': 0.0,
                'total': 1000.0
            },
            'DOT': {
                'free': 100.0,
                'used': 0.0,
                'total': 100.0
            }
        }
    
    async def get_supported_pairs(self) -> list:
        """Get list of supported trading pairs"""
        # In simulation mode, return the list of pairs we have base prices for
        # Simulate new listings periodically
        self.listing_counter += 1
        
        # Every 10 calls, add a new trading pair (simulating a new listing)
        if self.listing_counter % 10 == 0 and 'SOL/USDT' not in self.base_prices:
            self.base_prices['SOL/USDT'] = 95.0
            self.volatilities['SOL/USDT'] = 0.005
            self.logger.info("NEW LISTING: SOL/USDT now available on XT")
        
        return list(self.base_prices.keys())
    
    async def fetch_multi_order_book(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch order book data for multiple symbols"""
        result = {}
        for symbol in symbols:
            result[symbol] = await self.fetch_order_book(symbol)
        return result