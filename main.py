import asyncio
import yaml
import logging
import os
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.live import Live
from exchanges.okx import OKXExchange
from exchanges.xt import XTExchange
from strategies.spread import SpreadStrategy
from strategies.multi_asset_strategy import MultiAssetStrategy
from bidirectional_arbitrage_strategy import BidirectionalArbitrageStrategy
from engine.trading_engine import SimulatedTradingEngine


class ArbitrageBot:
    """Main arbitrage bot class"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        # Set up Rich console
        self.console = Console()
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Set up logging
        logging.basicConfig(
            level=getattr(logging, self.config['logging']['level']),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Error counters for monitoring
        self.error_counters = {
            'market_data_errors': 0,
            'strategy_errors': 0,
            'trade_execution_errors': 0,
            'position_closing_errors': 0,
            'general_errors': 0
        }
        
        # Last dashboard content for comparison
        self.last_dashboard_content = None
        
        # Update counter for periodic refresh
        self.update_counter = 0
        
        # Initialize exchanges
        self.okx_exchange = OKXExchange(self.config['exchanges']['okx'])
        self.xt_exchange = XTExchange(self.config['exchanges']['xt'])
        
        # Initialize strategies
        self.spread_strategy = SpreadStrategy(self.config['trading'])
        self.multi_asset_strategy = MultiAssetStrategy(self.config['trading'])
        self.bidirectional_strategy = BidirectionalArbitrageStrategy(self.config['trading'])
        
        # Initialize trading engine
        self.trading_engine = SimulatedTradingEngine(self.config['simulation'])
        
        # Control flags
        self.running = False
        
    async def initialize_supported_pairs(self):
        """Initialize supported trading pairs by getting intersection of both exchanges"""
        # Get supported pairs from both exchanges
        okx_pairs = await self.okx_exchange.get_supported_pairs()
        xt_pairs = await self.xt_exchange.get_supported_pairs()
        
        # Find intersection of supported pairs
        common_pairs = list(set(okx_pairs) & set(xt_pairs))
        
        # If no common pairs found, use default pairs from config
        if not common_pairs:
            common_pairs = self.config['trading'].get('supported_pairs', 
                                                     ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT'])
        
        self.supported_pairs = common_pairs
        self.logger.info(f"Supported trading pairs: {self.supported_pairs}")
        
    async def fetch_market_data(self) -> Dict[str, Any]:
        """Fetch market data from both exchanges for all supported pairs"""
        # Fetch data for all supported pairs
        okx_data = await self.okx_exchange.fetch_multi_order_book(self.supported_pairs)
        xt_data = await self.xt_exchange.fetch_multi_order_book(self.supported_pairs)
        
        # Combine data by symbol
        market_data = {}
        for symbol in self.supported_pairs:
            if symbol in okx_data and symbol in xt_data:
                market_data[symbol] = {
                    'okx': okx_data[symbol],
                    'xt': xt_data[symbol]
                }
        
        return market_data
    
    def create_opportunities_table(self, opportunities_summary):
        """Create opportunities table with Rich"""
        table = Table(title="套利机会概览", box=box.ROUNDED)
        table.add_column("状态", style="bold", width=4)
        table.add_column("币种", style="cyan")
        table.add_column("价差%", style="green")
        table.add_column("绝对价差", style="yellow")
        
        for opp in opportunities_summary[:10]:  # Show top 10 opportunities
            status = "🟢" if opp['profitable'] else "🔴"
            spread_pct = f"{opp['spread_percentage']*100:.4f}%"
            spread_abs = f"${opp['spread']:.2f}"
            table.add_row(status, opp['symbol'], spread_pct, spread_abs)
        
        return table
    
    def create_positions_table(self, open_positions):
        """Create positions table with Rich"""
        if not open_positions:
            return Panel("📊 [bold green]当前无持仓[/bold green]", expand=False)
        
        table = Table(title=f"持仓信息 (共{len(open_positions)}个)", box=box.ROUNDED)
        table.add_column("币种", style="cyan")
        table.add_column("买入交易所", style="green")
        table.add_column("卖空交易所", style="red")
        table.add_column("数量", style="yellow")
        table.add_column("买入价格", style="green")
        table.add_column("卖空价格", style="red")
        table.add_column("入场价差", style="blue")
        
        for position in open_positions:
            table.add_row(
                position['symbol'],
                position['buy_exchange'],
                position['short_exchange'],
                f"{position['position_size']:.6f}",
                f"${position['buy_price']:.2f}",
                f"${position['short_price']:.2f}",
                f"${position['entry_spread']:.2f}"
            )
        
        return table
    
    def create_balances_table(self, balances):
        """Create balances table with Rich"""
        table = Table(title="账户余额", box=box.ROUNDED)
        table.add_column("交易所", style="bold")
        table.add_column("USDT余额", style="green")
        table.add_column("合约仓位", style="magenta")
        table.add_column("持仓资产", style="cyan")
        
        # OKX balances
        okx_usdt = f"${balances['OKX']['USDT']:.2f}"
        okx_contracts = f"{balances['OKX']['contracts']:.6f}"
        okx_assets = []
        for asset in ['BTC', 'ETH', 'BNB', 'ADA', 'DOT', 'SOL']:
            if balances['OKX'].get(asset, 0) > 0:
                if asset in ['BTC', 'SOL']:
                    okx_assets.append(f"{asset}: {balances['OKX'][asset]:.4f}")
                else:
                    okx_assets.append(f"{asset}: {balances['OKX'][asset]:.2f}")
        okx_assets_str = " | ".join(okx_assets) if okx_assets else "无"
        table.add_row("OKX", okx_usdt, okx_contracts, okx_assets_str)
        
        # XT balances
        xt_usdt = f"${balances['XT']['USDT']:.2f}"
        xt_contracts = f"{balances['XT']['contracts']:.6f}"
        xt_assets = []
        for asset in ['BTC', 'ETH', 'BNB', 'ADA', 'DOT', 'SOL']:
            if balances['XT'].get(asset, 0) > 0:
                if asset in ['BTC', 'SOL']:
                    xt_assets.append(f"{asset}: {balances['XT'][asset]:.4f}")
                else:
                    xt_assets.append(f"{asset}: {balances['XT'][asset]:.2f}")
        xt_assets_str = " | ".join(xt_assets) if xt_assets else "无"
        table.add_row("XT", xt_usdt, xt_contracts, xt_assets_str)
        
        return table
    
    def create_stats_panel(self, stats):
        """Create statistics panel with Rich"""
        content = f"""
📊 [bold]交易统计[/bold]
总交易数: [bold cyan]{stats['total_trades']}[/bold cyan]
胜率: [bold green]{stats['win_rate']:.2f}%[/bold green]
总利润: [bold yellow]${stats['total_profit']:.2f}[/bold yellow]
今日利润: [bold blue]${stats['daily_profit']:.2f}[/bold blue]
持仓数量: [bold purple]{stats['open_positions']}[/bold purple]
        """.strip()
        
        return Panel(content, title="统计信息", box=box.ROUNDED)
    
    def create_error_stats_panel(self):
        """Create error statistics panel with Rich"""
        content = f"""
⚠️  [bold]错误统计[/bold]
市场数据错误: [bold red]{self.error_counters['market_data_errors']}[/bold red]
策略计算错误: [bold red]{self.error_counters['strategy_errors']}[/bold red]
交易执行错误: [bold red]{self.error_counters['trade_execution_errors']}[/bold red]
平仓错误: [bold red]{self.error_counters['position_closing_errors']}[/bold red]
一般错误: [bold red]{self.error_counters['general_errors']}[/bold red]
        """.strip()
        
        return Panel(content, title="错误监控", box=box.ROUNDED)
    
    def create_dashboard_layout(self, market_data: Dict[str, Any], signal: Dict[str, Any], open_positions: list = None):
        """Create dashboard layout without clearing screen"""
        if open_positions is None:
            open_positions = []
            
        # Create header
        header = Panel("[bold blue]多币种MVP版本[/bold blue]", 
                      box=box.DOUBLE)
        
        # Display signal
        if signal['should_trade']:
            if signal['direction'] == 'xt_short_okx_long':
                buy_price = signal['okx_price']
                short_price = signal['xt_price']
                buy_exchange = "OKX"
                short_exchange = "XT"
            else:
                buy_price = signal['xt_price']
                short_price = signal['okx_price']
                buy_exchange = "XT"
                short_exchange = "OKX"
                
            signal_text = f"""
[bold green]🟢 最佳机会: {signal['reason']}[/bold green]
币种: [bold cyan]{signal['selected_symbol']}[/bold cyan]
方向: [bold magenta]{'XT做空,OKX做多' if signal['direction'] == 'xt_short_okx_long' else 'OKX做空,XT做多'}[/bold magenta]
在{buy_exchange}买入现货: [bold green]${buy_price:.2f}[/bold green] (现货价格)
在{short_exchange}卖空合约: [bold red]${short_price:.2f}[/bold red] (合约价格)
预期利润: [bold yellow]{signal['profit_potential']*100:.4f}%[/bold yellow]
            """.strip()
        else:
            signal_text = f"[bold red]🔴 无套利机会: {signal['reason']}[/bold red]"
        
        signal_panel = Panel(signal_text, title="交易信号", box=box.ROUNDED)
        
        # Display opportunities summary
        opportunities_summary = self.multi_asset_strategy.get_market_summary(market_data)
        opportunities_table = self.create_opportunities_table(opportunities_summary)
        
        # Display open positions
        positions_table = self.create_positions_table(open_positions)
        
        # Display balances
        balances = self.trading_engine.get_balances()
        balances_table = self.create_balances_table(balances)
        
        # Display statistics
        stats = self.trading_engine.get_statistics()
        stats['open_positions'] = len(open_positions)
        stats_panel = self.create_stats_panel(stats)
        
        # Display error statistics
        error_stats_panel = self.create_error_stats_panel()
        
        # Display footer
        footer = Panel("[bold]按 Ctrl+C 停止机器人[/bold]", 
                      box=box.SIMPLE)
        
        # Combine all elements using Rich's renderable approach
        from rich.console import Group
        dashboard_content = Group(
            header,
            signal_panel,
            opportunities_table,
            positions_table,
            balances_table,
            stats_panel,
            error_stats_panel,
            footer
        )
        return dashboard_content
    
    async def display_dashboard(self, market_data: Dict[str, Any], signal: Dict[str, Any], open_positions: list = None):
        """Display real-time dashboard with Rich"""
        if open_positions is None:
            open_positions = []
            
        # Create dashboard content
        dashboard_content = self.create_dashboard_layout(market_data, signal, open_positions)
        return dashboard_content
        
    async def run_strategy(self):
        """Main strategy loop"""
        self.logger.info("Starting multi-asset arbitrage bot...")
        
        # Initialize supported trading pairs
        await self.initialize_supported_pairs()
        
        # Update strategies with the actual supported pairs
        self.multi_asset_strategy.supported_pairs = self.supported_pairs
        
        # Counter for periodic re-initialization
        reinit_counter = 0
        
        # Use Rich Live for smooth dashboard updates with reduced flicker
        with Live(auto_refresh=False, refresh_per_second=1) as live:
            while self.running:
                try:
                    # Periodically re-initialize supported trading pairs (every 20 iterations)
                    reinit_counter += 1
                    if reinit_counter % 20 == 0:
                        old_pairs = set(self.supported_pairs)
                        await self.initialize_supported_pairs()
                        new_pairs = set(self.supported_pairs)
                        
                        # Check for new pairs
                        added_pairs = new_pairs - old_pairs
                        if added_pairs:
                            self.logger.info(f"NEW TRADING PAIRS DETECTED: {added_pairs}")
                        
                        # Update strategies with the actual supported pairs
                        self.multi_asset_strategy.supported_pairs = self.supported_pairs
                    
                    # Fetch market data for all supported pairs
                    try:
                        market_data = await self.fetch_market_data()
                        self.error_counters['market_data_errors'] = 0  # Reset counter on success
                    except Exception as e:
                        self.error_counters['market_data_errors'] += 1
                        self.logger.error(f"Error fetching market data (attempt {self.error_counters['market_data_errors']}): {e}")
                        self.logger.debug(f"Market data error details: {type(e).__name__}", exc_info=True)
                        
                        # If we have too many consecutive errors, log a warning
                        if self.error_counters['market_data_errors'] >= 5:
                            self.logger.warning(f"Multiple consecutive market data errors ({self.error_counters['market_data_errors']}). Check exchange connectivity.")
                        
                        await asyncio.sleep(5)  # Wait before retrying
                        continue
                    
                    # Get open positions
                    open_positions = self.trading_engine.get_open_positions()
                    
                    # Select best arbitrage opportunity using bidirectional strategy
                    try:
                        signal = self.bidirectional_strategy.select_best_opportunity(market_data)
                        self.error_counters['strategy_errors'] = 0  # Reset counter on success
                    except Exception as e:
                        self.error_counters['strategy_errors'] += 1
                        self.logger.error(f"Error selecting best opportunity (attempt {self.error_counters['strategy_errors']}): {e}")
                        self.logger.debug(f"Strategy error details: {type(e).__name__}", exc_info=True)
                        
                        # If we have too many consecutive errors, log a warning
                        if self.error_counters['strategy_errors'] >= 3:
                            self.logger.warning(f"Multiple consecutive strategy errors ({self.error_counters['strategy_errors']}). Check strategy logic or market data.")
                        
                        await asyncio.sleep(5)  # Wait before retrying
                        continue
                    
                    # Display dashboard using Live update with smart refresh
                    dashboard_content = self.create_dashboard_layout(market_data, signal, open_positions)
                    
                    # Update dashboard every 5 iterations or when content changes significantly
                    self.update_counter += 1
                    should_update = (self.update_counter % 5 == 0)  # Update every 5 iterations
                    
                    # Also update if there are significant changes (new positions, etc.)
                    if not should_update:
                        current_positions = len(open_positions)
                        last_positions = getattr(self, 'last_position_count', 0)
                        if current_positions != last_positions:
                            should_update = True
                    
                    if should_update:
                        live.update(dashboard_content)
                        live.refresh()
                        self.last_position_count = len(open_positions)
                    
                    # Execute trade if signal is positive and no open positions
                    if signal['should_trade'] and len(open_positions) == 0:
                        try:
                            # Determine which exchanges to use based on direction
                            if signal['direction'] == 'xt_short_okx_long':
                                # XT做空，OKX做多
                                buy_exchange = self.okx_exchange
                                short_exchange = self.xt_exchange
                                buy_price = signal['okx_price']
                                short_price = signal['xt_price']
                            else:
                                # OKX做空，XT做多 (默认方向)
                                buy_exchange = self.xt_exchange
                                short_exchange = self.okx_exchange
                                buy_price = signal['xt_price']
                                short_price = signal['okx_price']
                            
                            # Create bidirectional signal
                            bidirectional_signal = {
                                'should_trade': True,
                                'selected_symbol': signal['selected_symbol'],
                                'buy_exchange': buy_exchange.name,
                                'short_exchange': short_exchange.name,
                                'buy_price': buy_price,
                                'short_price': short_price,
                                'direction': signal['direction'],
                                'spread': signal['spread'],
                                'spread_percentage': signal['spread_percentage'],
                                'profit_potential': signal['profit_potential'],
                                'reason': signal['reason']
                            }
                            
                            # Execute arbitrage with bidirectional support
                            result = await self.trading_engine.execute_bidirectional_arbitrage(
                                bidirectional_signal, short_exchange, buy_exchange, signal['selected_symbol'])
                            self.error_counters['trade_execution_errors'] = 0  # Reset counter on success
                            
                            if result['status'] == 'success':
                                self.logger.info(f"Bidirectional arbitrage position opened: {result}")
                            else:
                                self.logger.warning(f"Bidirectional arbitrage execution failed: {result.get('reason', 'Unknown error')}")
                        except Exception as e:
                            self.error_counters['trade_execution_errors'] += 1
                            self.logger.error(f"Error executing bidirectional arbitrage (attempt {self.error_counters['trade_execution_errors']}): {e}")
                            self.logger.debug(f"Trade execution error details: {type(e).__name__}", exc_info=True)
                            
                            # If we have too many consecutive errors, log a warning
                            if self.error_counters['trade_execution_errors'] >= 3:
                                self.logger.warning(f"Multiple consecutive trade execution errors ({self.error_counters['trade_execution_errors']}). Check trading engine or exchange connectivity.")
                            
                            import traceback
                            self.logger.error(f"Traceback: {traceback.format_exc()}")
                            # Continue with the next iteration instead of stopping the bot
                            pass
                    
                    # Check if we should close open positions (spread has converged)
                    elif len(open_positions) > 0:
                        # For each open position, check if we should close it
                        for position in open_positions:
                            symbol = position.get('symbol', 'BTC/USDT')
                            if symbol in market_data:
                                try:
                                    # Determine exchanges based on position direction
                                    if position['short_exchange'] == 'XT' and position['buy_exchange'] == 'OKX':
                                        # XT做空，OKX做多
                                        short_exchange = self.xt_exchange
                                        buy_exchange = self.okx_exchange
                                        current_spread = (market_data[symbol]['xt']['asks'][0][0] - 
                                                        market_data[symbol]['okx']['bids'][0][0])
                                    else:
                                        # OKX做空，XT做多 (默认方向)
                                        short_exchange = self.okx_exchange
                                        buy_exchange = self.xt_exchange
                                        current_spread = (market_data[symbol]['okx']['asks'][0][0] - 
                                                        market_data[symbol]['xt']['bids'][0][0])
                                    
                                    entry_spread = position['entry_spread']
                                    
                                    # Close position if spread has converged significantly (e.g., less than 30% of entry spread)
                                    # or if spread has reversed direction
                                    if abs(current_spread) < abs(entry_spread) * 0.3 or (
                                       current_spread * entry_spread < 0):  # Spread direction changed
                                        
                                        # Get exit prices for closing the position
                                        try:
                                            buy_order_book = await buy_exchange.fetch_order_book(symbol)
                                            short_order_book = await short_exchange.fetch_order_book(symbol)
                                            
                                            exit_prices = {
                                                'buy_price': buy_order_book['bids'][0][0],      # Sell spot
                                                'short_price': short_order_book['bids'][0][0]   # Buy contract (cover short)
                                            }
                                        except Exception as e:
                                            self.error_counters['position_closing_errors'] += 1
                                            self.logger.error(f"Error fetching order book for closing position (attempt {self.error_counters['position_closing_errors']}): {e}")
                                            self.logger.debug(f"Order book fetch error details: {type(e).__name__}", exc_info=True)
                                            
                                            # If we have too many consecutive errors, log a warning
                                            if self.error_counters['position_closing_errors'] >= 3:
                                                self.logger.warning(f"Multiple consecutive position closing errors ({self.error_counters['position_closing_errors']}). Check exchange connectivity.")
                                            
                                            continue
                                        
                                        close_result = await self.trading_engine.close_bidirectional_arbitrage_position(
                                            position, exit_prices, short_exchange, buy_exchange)
                                        
                                        if close_result['status'] == 'success':
                                            self.logger.info(f"Bidirectional arbitrage position closed: {close_result}")
                                            break  # Only close one position per cycle
                                except Exception as e:
                                    self.error_counters['position_closing_errors'] += 1
                                    self.logger.error(f"Error closing position for {symbol} (attempt {self.error_counters['position_closing_errors']}): {e}")
                                    self.logger.debug(f"Position closing error details: {type(e).__name__}", exc_info=True)
                                    
                                    # If we have too many consecutive errors, log a warning
                                    if self.error_counters['position_closing_errors'] >= 3:
                                        self.logger.warning(f"Multiple consecutive position closing errors ({self.error_counters['position_closing_errors']}). Check position management logic.")
                                    
                                    # Continue with the next position instead of stopping the bot
                                    continue
                    
                    # Wait before next iteration
                    await asyncio.sleep(2)  # Update every 2 seconds to reduce flickering
                    
                except KeyboardInterrupt:
                    self.logger.info("Received interrupt signal, stopping bot...")
                    self.running = False
                    break
                except Exception as e:
                    self.error_counters['general_errors'] += 1
                    import traceback
                    self.logger.error(f"Error in strategy loop (attempt {self.error_counters['general_errors']}): {e}")
                    self.logger.debug(f"General error details: {type(e).__name__}", exc_info=True)
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # If we have too many consecutive errors, log a warning
                    if self.error_counters['general_errors'] >= 3:
                        self.logger.warning(f"Multiple consecutive general errors ({self.error_counters['general_errors']}). Check overall system health.")
                    
                    await asyncio.sleep(5)  # Wait before retrying
    
    def start(self):
        """Start the arbitrage bot"""
        self.running = True
        try:
            asyncio.run(self.run_strategy())
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the arbitrage bot"""
        self.running = False
        self.logger.info("Arbitrage bot stopped")


if __name__ == "__main__":
    bot = ArbitrageBot()
    bot.start()