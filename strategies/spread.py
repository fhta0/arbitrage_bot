from typing import Dict, Any, Tuple
import logging


class SpreadStrategy:
    """Spread calculation and signal generation strategy"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_profit_threshold = config.get('min_profit_threshold', 0.002)  # 0.2% default
        self.okx_fee = config.get('okx_fee', 0.001)
        self.xt_fee = config.get('xt_fee', 0.001)
        
        # Calculate total cost (fees + minimum profit)
        self.total_cost = self.okx_fee + self.xt_fee + self.min_profit_threshold
        
    def calculate_spread(self, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> float:
        """
        Calculate the price spread between exchanges.
        Positive value means OKX price is higher than XT price.
        """
        # Calculate spread: OKX sell price - XT buy price
        # This represents the profit opportunity for buying on XT and selling on OKX
        okx_ask = okx_data['asks'][0][0]  # Best ask price on OKX
        xt_bid = xt_data['bids'][0][0]    # Best bid price on XT
        spread = okx_ask - xt_bid
        return spread
    
    def calculate_spread_percentage(self, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> float:
        """
        Calculate the percentage spread relative to the average price.
        """
        # Calculate average price for percentage calculation
        okx_ask = okx_data['asks'][0][0]  # Best ask price on OKX
        xt_bid = xt_data['bids'][0][0]    # Best bid price on XT
        avg_price = (okx_ask + xt_bid) / 2
        absolute_spread = self.calculate_spread(okx_data, xt_data)
        percentage_spread = absolute_spread / avg_price if avg_price > 0 else 0
        return percentage_spread
    
    def should_trade(self, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if a trading opportunity exists.
        
        Returns:
            Tuple[bool, str]: (should_trade, reason)
        """
        spread_percentage = self.calculate_spread_percentage(okx_data, xt_data)
        
        if spread_percentage > self.total_cost:
            return True, f"Spread {spread_percentage:.4f} > Cost {self.total_cost:.4f}"
        else:
            return False, f"Spread {spread_percentage:.4f} <= Cost {self.total_cost:.4f}"
    
    def generate_signal(self, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a trading signal based on the spread analysis.
        """
        should_trade, reason = self.should_trade(okx_data, xt_data)
        spread = self.calculate_spread(okx_data, xt_data)
        spread_percentage = self.calculate_spread_percentage(okx_data, xt_data)
        
        okx_ask = okx_data['asks'][0][0]  # Best ask price on OKX
        xt_bid = xt_data['bids'][0][0]    # Best bid price on XT
        
        signal = {
            'should_trade': should_trade,
            'reason': reason,
            'spread': spread,
            'spread_percentage': spread_percentage,
            'okx_price': okx_ask,  # Price to sell at OKX
            'xt_price': xt_bid,    # Price to buy at XT
            'timestamp': okx_data.get('timestamp', 0)
        }
        
        # Log the signal
        if should_trade:
            logging.info(f"TRADING OPPORTUNITY: {reason}")
        
        return signal