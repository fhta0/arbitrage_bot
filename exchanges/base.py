import asyncio
import random
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseExchange(ABC):
    """Base class for all exchange implementations"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.symbol = config.get('symbol', 'BTC/USDT')
        
    @abstractmethod
    async def fetch_ticker(self) -> Dict[str, Any]:
        """Fetch current ticker data"""
        pass
    
    @abstractmethod
    async def fetch_order_book(self) -> Dict[str, Any]:
        """Fetch order book data"""
        pass
    
    @abstractmethod
    async def create_order(self, side: str, amount: float, price: float) -> Dict[str, Any]:
        """Create a new order"""
        pass
    
    @abstractmethod
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance"""
        pass
    
    @abstractmethod
    async def get_supported_pairs(self) -> list:
        """Get list of supported trading pairs"""
        pass
    
    def _simulate_price_data(self, base_price: float, volatility: float = 0.001) -> Dict[str, float]:
        """Simulate realistic price data for testing"""
        # Add some random volatility to make it more realistic
        bid_price = base_price * (1 - random.uniform(0, volatility))
        ask_price = base_price * (1 + random.uniform(0, volatility))
        
        return {
            'bid': bid_price,
            'ask': ask_price,
            'last': base_price
        }