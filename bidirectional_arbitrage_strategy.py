#!/usr/bin/env python3
"""
双向套利策略 - 支持两个方向的跨市场套利
"""
import logging
from typing import Dict, Any, List, Tuple


class BidirectionalArbitrageStrategy:
    """Bidirectional arbitrage strategy supporting both directions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_profit_threshold = config.get('min_profit_threshold', 0.002)  # 0.2% default
        self.okx_fee = config.get('okx_fee', 0.001)
        self.xt_fee = config.get('xt_fee', 0.001)
        
        # Calculate total cost (fees + minimum profit)
        self.total_cost = self.okx_fee + self.xt_fee + self.min_profit_threshold
        
        # List of supported trading pairs
        self.supported_pairs = config.get('supported_pairs', ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT'])
        
    def calculate_spread_direction_1(self, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> float:
        """
        Calculate spread for Direction 1: OKX contract short, XT spot long
        Positive value means OKX price is higher than XT price.
        """
        okx_ask = okx_data['asks'][0][0]  # OKX contract sell price
        xt_bid = xt_data['bids'][0][0]    # XT spot buy price
        spread = okx_ask - xt_bid
        return spread
    
    def calculate_spread_direction_2(self, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> float:
        """
        Calculate spread for Direction 2: XT contract short, OKX spot long
        Positive value means XT price is higher than OKX price.
        """
        xt_ask = xt_data['asks'][0][0]    # XT contract sell price
        okx_bid = okx_data['bids'][0][0]  # OKX spot buy price
        spread = xt_ask - okx_bid
        return spread
    
    def calculate_spread_percentage(self, spread: float, price1: float, price2: float) -> float:
        """
        Calculate the percentage spread relative to the average price.
        """
        avg_price = (price1 + price2) / 2
        percentage_spread = spread / avg_price if avg_price > 0 else 0
        return percentage_spread
    
    def evaluate_opportunity_direction_1(self, symbol: str, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate arbitrage opportunity for Direction 1: OKX contract short, XT spot long
        """
        okx_ask = okx_data['asks'][0][0]  # OKX contract sell price
        xt_bid = xt_data['bids'][0][0]    # XT spot buy price
        absolute_spread = self.calculate_spread_direction_1(okx_data, xt_data)
        percentage_spread = self.calculate_spread_percentage(absolute_spread, okx_ask, xt_bid)
        
        opportunity = {
            'symbol': symbol,
            'direction': 'okx_short_xt_long',  # OKX做空，XT做多
            'okx_price': okx_ask,              # OKX合约卖出价
            'xt_price': xt_bid,                # XT现货买入价
            'spread': absolute_spread,
            'spread_percentage': percentage_spread,
            'profitable': percentage_spread > self.total_cost,
            'profit_potential': percentage_spread - self.total_cost if percentage_spread > self.total_cost else 0
        }
        
        return opportunity
    
    def evaluate_opportunity_direction_2(self, symbol: str, okx_data: Dict[str, Any], xt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate arbitrage opportunity for Direction 2: XT contract short, OKX spot long
        """
        xt_ask = xt_data['asks'][0][0]    # XT合约卖出价
        okx_bid = okx_data['bids'][0][0]  # OKX现货买入价
        absolute_spread = self.calculate_spread_direction_2(okx_data, xt_data)
        percentage_spread = self.calculate_spread_percentage(absolute_spread, xt_ask, okx_bid)
        
        opportunity = {
            'symbol': symbol,
            'direction': 'xt_short_okx_long',  # XT做空，OKX做多
            'xt_price': xt_ask,                # XT合约卖出价
            'okx_price': okx_bid,              # OKX现货买入价
            'spread': absolute_spread,
            'spread_percentage': percentage_spread,
            'profitable': percentage_spread > self.total_cost,
            'profit_potential': percentage_spread - self.total_cost if percentage_spread > self.total_cost else 0
        }
        
        return opportunity
    
    def select_best_opportunity(self, market_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best arbitrage opportunity from multiple assets and directions.
        
        market_data: {
            'BTC/USDT': {'okx': okx_btc_data, 'xt': xt_btc_data},
            'ETH/USDT': {'okx': okx_eth_data, 'xt': xt_eth_data},
            ...
        }
        """
        opportunities = []
        
        # Evaluate all supported pairs in both directions
        for symbol in self.supported_pairs:
            if symbol in market_data and 'okx' in market_data[symbol] and 'xt' in market_data[symbol]:
                # Direction 1: OKX contract short, XT spot long
                opp1 = self.evaluate_opportunity_direction_1(
                    symbol, 
                    market_data[symbol]['okx'], 
                    market_data[symbol]['xt']
                )
                opportunities.append(opp1)
                
                # Direction 2: XT contract short, OKX spot long
                opp2 = self.evaluate_opportunity_direction_2(
                    symbol, 
                    market_data[symbol]['okx'], 
                    market_data[symbol]['xt']
                )
                opportunities.append(opp2)
        
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
            'direction': best_opportunity['direction'],
            'okx_price': best_opportunity['okx_price'],
            'xt_price': best_opportunity['xt_price'],
            'spread': best_opportunity['spread'],
            'spread_percentage': best_opportunity['spread_percentage'],
            'profit_potential': best_opportunity['profit_potential'],
            'reason': f"Best opportunity in {best_opportunity['symbol']} with {best_opportunity['spread_percentage']:.4f} spread, direction: {best_opportunity['direction']}",
            'all_opportunities': opportunities
        }
    
    def get_market_summary(self, market_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get summary of all market opportunities for display.
        """
        summary = []
        
        for symbol in self.supported_pairs:
            if symbol in market_data and 'okx' in market_data[symbol] and 'xt' in market_data[symbol]:
                # Direction 1: OKX contract short, XT spot long
                opp1 = self.evaluate_opportunity_direction_1(
                    symbol, 
                    market_data[symbol]['okx'], 
                    market_data[symbol]['xt']
                )
                summary.append(opp1)
                
                # Direction 2: XT contract short, OKX spot long
                opp2 = self.evaluate_opportunity_direction_2(
                    symbol, 
                    market_data[symbol]['okx'], 
                    market_data[symbol]['xt']
                )
                summary.append(opp2)
        
        # Sort by spread percentage (descending)
        summary.sort(key=lambda x: x['spread_percentage'], reverse=True)
        return summary