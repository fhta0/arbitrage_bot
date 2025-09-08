import asyncio
import logging
from typing import Dict, Any
from datetime import datetime


class SimulatedTradingEngine:
    """Simulated trading engine for executing arbitrage trades"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initial_capital = config.get('initial_capital', 10000.0)
        self.position_size_percent = config.get('position_size_percent', 0.1)  # 10% default
        self.logger = logging.getLogger(__name__)
        
        # Simulated account balances
        # Both exchanges support contract trading
        self.balances = {
            'OKX': {  # Contract exchange
                'USDT': self.initial_capital / 2,
                'BTC': 0.0,
                'ETH': 0.0,
                'BNB': 0.0,
                'ADA': 0.0,
                'DOT': 0.0,
                'SOL': 0.0,
                'contracts': 0.0  # Contract positions
            },
            'XT': {   # Contract exchange
                'USDT': self.initial_capital / 2,
                'BTC': 0.0,
                'ETH': 0.0,
                'BNB': 0.0,
                'ADA': 0.0,
                'DOT': 0.0,
                'SOL': 0.0,
                'contracts': 0.0  # Contract positions
            }
        }
        
        # Open positions tracking
        self.open_positions = []
        
        # Trade history
        self.trade_history = []
        
        # Statistics
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit = 0.0
        self.daily_profit = 0.0
        
    def calculate_position_size(self, price: float) -> float:
        """Calculate position size based on available capital"""
        # Use half of total USDT for each leg of the arbitrage
        available_usdt = min(self.balances['OKX']['USDT'], self.balances['XT']['USDT'])
        position_value = available_usdt * self.position_size_percent
        
        # Add safety checks to prevent extreme values
        if price <= 0:
            self.logger.warning(f"Invalid price {price}, using default price of 1.0")
            price = 1.0
            
        position_size = position_value / price
        
        # Add safety check for extremely small position sizes
        if position_size < 1e-10:
            self.logger.warning(f"Calculated position size too small: {position_size}, setting to 0")
            position_size = 0.0
            
        return position_size
    
    async def execute_bidirectional_arbitrage(self, signal: Dict[str, Any], short_exchange, buy_exchange, symbol: str = None) -> Dict[str, Any]:
        """
        Execute a bidirectional arbitrage trade based on the signal.
        
        Correct strategy:
        1. Short contract on the specified exchange (expecting price to fall)
        2. Buy spot on the specified exchange (expecting price to rise)
        """
        if not signal['should_trade']:
            return {'status': 'no_trade', 'reason': 'No trading signal'}
        
        symbol = symbol or signal.get('selected_symbol', 'BTC/USDT')
        
        # Calculate position size
        buy_price = signal['buy_price']    # Buy spot
        short_price = signal['short_price']  # Sell/Short contract
        position_size = self.calculate_position_size(buy_price)
        
        # Check if we have enough balance
        buy_exchange_name = buy_exchange.name
        short_exchange_name = short_exchange.name
        
        if buy_exchange_name == 'OKX':
            if self.balances['OKX']['USDT'] < (position_size * buy_price):
                return {'status': 'error', 'reason': f'Insufficient USDT balance on OKX for spot purchase'}
        else:  # XT
            if self.balances['XT']['USDT'] < (position_size * buy_price):
                return {'status': 'error', 'reason': f'Insufficient USDT balance on XT for spot purchase'}
        
        # Execute spot buy order (go long)
        spot_buy_order = await buy_exchange.create_order('buy', position_size, buy_price, symbol)
        
        # Execute contract short order (go short)
        contract_short_order = await short_exchange.create_order('sell', position_size, short_price, symbol)
        
        # Update balances
        spot_cost = position_size * buy_price
        contract_value = position_size * short_price
        
        if buy_exchange_name == 'OKX':
            self.balances['OKX']['USDT'] -= spot_cost
            self.balances['OKX'][symbol.split('/')[0]] += position_size
        else:  # XT
            self.balances['XT']['USDT'] -= spot_cost
            self.balances['XT'][symbol.split('/')[0]] += position_size
        
        if short_exchange_name == 'OKX':
            self.balances['OKX']['USDT'] += contract_value
            self.balances['OKX']['contracts'] -= position_size  # Negative for short position
        else:  # XT
            self.balances['XT']['USDT'] += contract_value
            self.balances['XT']['contracts'] -= position_size  # Negative for short position
        
        # Deduct fees
        buy_fee = spot_cost * buy_exchange.fee
        short_fee = contract_value * short_exchange.fee
        total_fees = buy_fee + short_fee
        
        if buy_exchange_name == 'OKX':
            self.balances['OKX']['USDT'] -= buy_fee
        else:  # XT
            self.balances['XT']['USDT'] -= buy_fee
            
        if short_exchange_name == 'OKX':
            self.balances['OKX']['USDT'] -= short_fee
        else:  # XT
            self.balances['XT']['USDT'] -= short_fee
        
        # Record open position
        position_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'buy_exchange': buy_exchange_name,
            'short_exchange': short_exchange_name,
            'buy_price': buy_price,
            'short_price': short_price,
            'position_size': position_size,
            'entry_spread': short_price - buy_price,
            'spot_order_id': spot_buy_order['id'],
            'contract_order_id': contract_short_order['id'],
            'fees': total_fees,
            'status': 'open'
        }
        
        self.open_positions.append(position_record)
        
        # Log the position opening
        logging.info(f"BIDIRECTIONAL ARBITRAGE POSITION OPENED: "
                    f"Buy {position_size} {symbol} spot @ {buy_price} on {buy_exchange_name}, "
                    f"Short {position_size} {symbol} contract @ {short_price} on {short_exchange_name}, "
                    f"Entry Spread: ${short_price - buy_price:.2f}")
        
        return {
            'status': 'success',
            'position_record': position_record
        }
    
    async def close_bidirectional_arbitrage_position(self, position: Dict[str, Any], exit_prices: Dict[str, float], 
                                     short_exchange, buy_exchange) -> Dict[str, Any]:
        """
        Close a bidirectional arbitrage position when spread converges.
        
        position: The open position to close
        exit_prices: {'buy_price': spot_price, 'short_price': contract_price}
        """
        position_size = position['position_size']
        spot_sell_price = exit_prices['buy_price']      # Sell spot
        contract_buy_price = exit_prices['short_price']  # Buy/cover contract
        
        # Execute spot sell order (close long)
        spot_sell_order = await buy_exchange.create_order('sell', position_size, spot_sell_price)
        
        # Execute contract buy order (close short)
        contract_buy_order = await short_exchange.create_order('buy', position_size, contract_buy_price)
        
        # Calculate P&L
        # Spot P&L: (Sell Price - Buy Price) * Quantity
        spot_pl = (spot_sell_price - position['buy_price']) * position_size
        
        # Contract P&L: (Sell Price - Buy Price) * Quantity (but we're short, so it's reversed)
        contract_pl = (position['short_price'] - contract_buy_price) * position_size
        
        gross_profit = spot_pl + contract_pl
        
        # Deduct closing fees
        spot_exit_cost = position_size * spot_sell_price
        contract_exit_cost = position_size * contract_buy_price
        
        buy_exit_fee = spot_exit_cost * buy_exchange.fee
        short_exit_fee = contract_exit_cost * short_exchange.fee
        total_exit_fees = buy_exit_fee + short_exit_fee
        
        net_profit = gross_profit - total_exit_fees - position['fees']  # Include entry fees
        
        # Update balances
        buy_exchange_name = buy_exchange.name
        short_exchange_name = short_exchange.name
        
        if buy_exchange_name == 'OKX':
            self.balances['OKX']['USDT'] += spot_exit_cost
            self.balances['OKX'][position['symbol'].split('/')[0]] -= position_size
        else:  # XT
            self.balances['XT']['USDT'] += spot_exit_cost
            self.balances['XT'][position['symbol'].split('/')[0]] -= position_size
        
        if short_exchange_name == 'OKX':
            self.balances['OKX']['USDT'] -= contract_exit_cost
            self.balances['OKX']['contracts'] += position_size  # Close short position
        else:  # XT
            self.balances['XT']['USDT'] -= contract_exit_cost
            self.balances['XT']['contracts'] += position_size  # Close short position
        
        # Deduct exit fees
        if buy_exchange_name == 'OKX':
            self.balances['OKX']['USDT'] -= buy_exit_fee
        else:  # XT
            self.balances['XT']['USDT'] -= buy_exit_fee
            
        if short_exchange_name == 'OKX':
            self.balances['OKX']['USDT'] -= short_exit_fee
        else:  # XT
            self.balances['XT']['USDT'] -= short_exit_fee
        
        # Update position status
        position['status'] = 'closed'
        position['exit_timestamp'] = datetime.now().isoformat()
        position['spot_exit_price'] = spot_sell_price
        position['contract_exit_price'] = contract_buy_price
        position['spot_exit_order_id'] = spot_sell_order['id']
        position['contract_exit_order_id'] = contract_buy_order['id']
        position['exit_spread'] = spot_sell_price - contract_buy_price
        position['gross_profit'] = gross_profit
        position['exit_fees'] = total_exit_fees
        position['net_profit'] = net_profit
        
        # Move to trade history
        self.open_positions.remove(position)
        self.trade_history.append(position)
        
        # Update statistics
        self.total_trades += 1
        if net_profit > 0:
            self.profitable_trades += 1
        self.total_profit += net_profit
        self.daily_profit += net_profit
        
        # Log the position closing
        logging.info(f"BIDIRECTIONAL ARBITRAGE POSITION CLOSED: "
                    f"Sell {position_size} {position['symbol']} spot @ {spot_sell_price} on {buy_exchange_name}, "
                    f"Buy {position_size} {position['symbol']} contract @ {contract_buy_price} on {short_exchange_name}, "
                    f"Net Profit: {net_profit:.2f} USDT")
        
        return {
            'status': 'success',
            'closed_position': position
        }
    
    def get_open_positions(self) -> list:
        """Get all open positions"""
        return self.open_positions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get trading statistics"""
        win_rate = (self.profitable_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'total_trades': self.total_trades,
            'profitable_trades': self.profitable_trades,
            'win_rate': win_rate,
            'total_profit': self.total_profit,
            'daily_profit': self.daily_profit,
            'open_positions': len(self.open_positions)
        }
    
    def get_balances(self) -> Dict[str, Any]:
        """Get current account balances"""
        return self.balances