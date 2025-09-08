import logging
from typing import Dict, Any, List, Tuple


class MultiAssetStrategy:
    """Multi-asset arbitrage strategy for selecting best arbitrage opportunities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_profit_threshold = config.get('min_profit_threshold', 0.002)  # 0.2% default
        self.okx_fee = config.get('okx_fee', 0.001)
        self.xt_fee = config.get('xt_fee', 0.001)
        
        # Calculate total cost (fees + minimum profit)
        self.total_cost = self.okx_fee + self.xt_fee + self.min_profit_threshold
        
        # List of supported trading pairs
        self.supported_pairs = config.get('supported_pairs', ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT'])
        
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
    
    def evaluate_opportunity(self, symbol: str, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate arbitrage opportunity for a specific symbol.
        """
        spread_percentage = self.calculate_spread_percentage(okx_data, xt_data)
        
        opportunity = {
            'symbol': symbol,
            'okx_ask': okx_data['asks'][0][0],
            'xt_bid': xt_data['bids'][0][0],
            'spread': self.calculate_spread(okx_data, xt_data),
            'spread_percentage': spread_percentage,
            'profitable': spread_percentage > self.total_cost,
            'profit_potential': spread_percentage - self.total_cost if spread_percentage > self.total_cost else 0
        }
        
        return opportunity
    
    def select_best_opportunity(self, market_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best arbitrage opportunity from multiple assets.
        
        market_data: {
            'BTC/USDT': {'okx': okx_btc_data, 'xt': xt_btc_data},
            'ETH/USDT': {'okx': okx_eth_data, 'xt': xt_eth_data},
            ...
        }
        """
        opportunities = []
        
        # Evaluate all supported pairs
        for symbol in self.supported_pairs:
            if symbol in market_data and 'okx' in market_data[symbol] and 'xt' in market_data[symbol]:
                opportunity = self.evaluate_opportunity(
                    symbol, 
                    market_data[symbol]['okx'], 
                    market_data[symbol]['xt']
                )
                opportunities.append(opportunity)
        
        # Filter profitable opportunities
        profitable_opportunities = [opp for opp in opportunities if opp['profitable']]
        
        if not profitable_opportunities:
            return {
                'should_trade': False,
                'reason': 'No profitable opportunities found',
                'opportunities': opportunities
            }
        
        # Select the opportunity with highest profit potential
        best_opportunity = max(profitable_opportunities, key=lambda x: x['profit_potential'])
        
        return {
            'should_trade': True,
            'selected_symbol': best_opportunity['symbol'],
            'okx_price': best_opportunity['okx_ask'],
            'xt_price': best_opportunity['xt_bid'],
            'spread': best_opportunity['spread'],
            'spread_percentage': best_opportunity['spread_percentage'],
            'profit_potential': best_opportunity['profit_potential'],
            'reason': f"Best opportunity in {best_opportunity['symbol']} with {best_opportunity['spread_percentage']:.4f} spread",
            'all_opportunities': opportunities
        }
    
    def get_market_summary(self, market_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get summary of all market opportunities for display.
        """
        summary = []
        
        for symbol in self.supported_pairs:
            if symbol in market_data and 'okx' in market_data[symbol] and 'xt' in market_data[symbol]:
                opportunity = self.evaluate_opportunity(
                    symbol, 
                    market_data[symbol]['okx'], 
                    market_data[symbol]['xt']
                )
                summary.append(opportunity)
        
        # Sort by spread percentage (descending)
        summary.sort(key=lambda x: x['spread_percentage'], reverse=True)
        return summary