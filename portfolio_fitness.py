"""
Portfolio-based fitness evaluation for genetic trading algorithm.
Tests strategy across multiple stocks for better generalization.
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import config
from genetic_trader import GeneticTrader
from bt_strategy import create_strategy_from_trader, MacroAwarePandasData
from data_loader import DataLoader


class PortfolioFitnessEvaluator:
    """
    Evaluates fitness of genetic traders using a portfolio of stocks.
    Each trader manages multiple stocks simultaneously with equal capital allocation.
    """

    def __init__(self, symbols: List[str], start_date: str, end_date: str):
        """
        Initialize portfolio fitness evaluator.

        Args:
            symbols: List of stock symbols to trade
            start_date: Start date for training data
            end_date: End date for training data
        """
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = config.INITIAL_CASH
        self.commission = config.COMMISSION

        # Load data for all symbols (cached in memory for reuse)
        print(f"\nLoading portfolio data for {len(symbols)} stocks...")
        loader = DataLoader(config.DATABASE_PATH)
        self.data_feeds = {}

        # Cache data in memory to avoid repeated disk I/O
        for symbol in symbols:
            try:
                df = loader.load_stock_data(
                    symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                # Store as read-only to prevent accidental modification
                df.flags.writeable = False
                self.data_feeds[symbol] = df
                print(f"  ✓ {symbol}: {len(df)} bars")
            except Exception as e:
                print(f"  ✗ {symbol}: Failed to load - {e}")

        self.valid_symbols = list(self.data_feeds.keys())
        print(f"\nSuccessfully loaded {len(self.valid_symbols)}/{len(symbols)} stocks")

        if len(self.valid_symbols) == 0:
            raise ValueError("No valid stock data loaded!")

        # Load macro data if enabled
        self.macro_df = None
        if getattr(config, 'USE_MACRO_DATA', False):
            try:
                macro_df = loader.load_macro_data(
                    start_date=start_date,
                    end_date=end_date
                )
                if macro_df is not None and not macro_df.empty:
                    self.macro_df = macro_df
                    print(f"\n  Macro data loaded: {len(macro_df)} rows")
                else:
                    print("\n  Warning: Macro data table empty or missing")
            except Exception as e:
                print(f"\n  Warning: Could not load macro data: {e}")

    def calculate_fitness(self, trader: GeneticTrader) -> float:
        """
        Calculate fitness score for a trader across the entire portfolio.

        Args:
            trader: GeneticTrader to evaluate

        Returns:
            Fitness score (higher is better)
        """
        try:
            # Run backtest on portfolio
            results = self._run_portfolio_backtest(trader)

            # Calculate metrics
            total_return = results['total_return']
            sharpe_ratio = results['sharpe_ratio']
            max_drawdown = results['max_drawdown']
            win_rate = results['win_rate']
            trade_count = results['trade_count']

            # Check minimum trade requirement
            if trade_count < config.MIN_TRADES_REQUIRED:
                return -100.0

            # Calculate weighted fitness
            fitness = (
                config.FITNESS_WEIGHTS['total_return'] * total_return +
                config.FITNESS_WEIGHTS['sharpe_ratio'] * sharpe_ratio * 10 +
                config.FITNESS_WEIGHTS['max_drawdown'] * max_drawdown +
                config.FITNESS_WEIGHTS['win_rate'] * win_rate
            )

            return fitness

        except Exception as e:
            print(f"Error evaluating trader: {e}")
            return -1000.0

    def _run_portfolio_backtest(self, trader: GeneticTrader) -> Dict[str, Any]:
        """
        Run backtest on entire portfolio using one strategy.

        Args:
            trader: GeneticTrader to backtest

        Returns:
            Dictionary with aggregated performance metrics
        """
        # Create Cerebro instance
        cerebro = bt.Cerebro()

        # Add strategy (will apply to all data feeds)
        # Use portfolio mode with initial allocation from config
        strategy_class = create_strategy_from_trader(
            trader,
            use_portfolio=True,
            initial_allocation_pct=config.INITIAL_ALLOCATION_PCT
        )
        cerebro.addstrategy(strategy_class, printlog=False)

        # Add all stock data feeds (with macro data merged if available)
        use_macro = self.macro_df is not None
        for symbol in self.valid_symbols:
            stock_df = self.data_feeds[symbol]

            if use_macro:
                # Merge macro columns into stock DataFrame
                merged = DataLoader.merge_macro_into_stock(
                    stock_df, self.macro_df
                )
                data_feed = MacroAwarePandasData(
                    dataname=merged,
                    name=symbol
                )
            else:
                data_feed = bt.feeds.PandasData(
                    dataname=stock_df,
                    name=symbol
                )

            cerebro.adddata(data_feed)

        # Set broker parameters
        # Divide cash equally among stocks
        cerebro.broker.setcash(self.initial_cash)
        cerebro.broker.setcommission(commission=self.commission)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        # Run backtest
        starting_value = cerebro.broker.getvalue()
        strategies = cerebro.run()
        ending_value = cerebro.broker.getvalue()

        # Extract strategy and results
        strat = strategies[0]

        # Calculate metrics
        total_return = ((ending_value - starting_value) / starting_value) * 100

        # Sharpe ratio
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe_analysis.get('sharperatio', 0.0)
        if sharpe_ratio is None:
            sharpe_ratio = 0.0

        # Max drawdown
        drawdown_analysis = strat.analyzers.drawdown.get_analysis()
        max_drawdown = -drawdown_analysis.get('max', {}).get('drawdown', 100.0)

        # Trade statistics
        trade_analysis = strat.analyzers.trades.get_analysis()
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0.0

        return {
            'starting_value': starting_value,
            'ending_value': ending_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': total_trades,
            'winning_trades': won_trades,
        }

    def evaluate_population(self, traders: List[GeneticTrader]) -> List[GeneticTrader]:
        """
        Evaluate fitness for all traders in a population.

        Args:
            traders: List of GeneticTrader instances

        Returns:
            List of traders with updated fitness scores
        """
        for i, trader in enumerate(traders):
            fitness = self.calculate_fitness(trader)
            trader.set_fitness(fitness)

            if (i + 1) % 5 == 0:
                print(f"Evaluated {i + 1}/{len(traders)} traders")

        return traders

    def get_detailed_results(self, trader: GeneticTrader) -> Dict[str, Any]:
        """
        Get detailed backtest results for a trader on the portfolio.

        Args:
            trader: GeneticTrader to evaluate

        Returns:
            Dictionary with detailed performance metrics
        """
        results = self._run_portfolio_backtest(trader)
        results['genes'] = trader.get_genes()
        results['fitness'] = self.calculate_fitness(trader)
        results['num_stocks'] = len(self.valid_symbols)
        results['symbols'] = self.valid_symbols

        return results

    def get_per_stock_results(self, trader: GeneticTrader) -> Dict[str, Dict[str, Any]]:
        """
        Get individual backtest results for each stock in portfolio.

        Args:
            trader: GeneticTrader to evaluate

        Returns:
            Dictionary mapping symbols to their individual results
        """
        results = {}

        for symbol in self.valid_symbols:
            cerebro = bt.Cerebro()

            # Add strategy
            strategy_class = create_strategy_from_trader(trader)
            cerebro.addstrategy(strategy_class, printlog=False)

            # Add single stock data
            data_feed = bt.feeds.PandasData(dataname=self.data_feeds[symbol])
            cerebro.adddata(data_feed)

            # Set broker parameters
            cerebro.broker.setcash(self.initial_cash / len(self.valid_symbols))
            cerebro.broker.setcommission(commission=self.commission)

            # Add analyzers
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

            # Run backtest
            starting_value = cerebro.broker.getvalue()
            strategies = cerebro.run()
            ending_value = cerebro.broker.getvalue()

            strat = strategies[0]
            trade_analysis = strat.analyzers.trades.get_analysis()

            results[symbol] = {
                'return_pct': ((ending_value - starting_value) / starting_value) * 100,
                'trades': trade_analysis.get('total', {}).get('total', 0),
                'won': trade_analysis.get('won', {}).get('total', 0),
            }

        return results


def select_random_portfolio(
    size: int = 20,
    min_records: int = 2000,
    seed: int = None
) -> List[str]:
    """
    Randomly select stocks for portfolio from database.

    Args:
        size: Number of stocks to select
        min_records: Minimum number of data records required
        seed: Random seed for reproducibility

    Returns:
        List of stock symbols
    """
    import sqlite3
    import random as rand

    if seed is not None:
        rand.seed(seed)

    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()

    # Get all stocks with sufficient data
    query = """
        SELECT DISTINCT symbol, sector
        FROM daily_indicators
        GROUP BY symbol
        HAVING COUNT(*) >= ?
        ORDER BY symbol
    """

    cursor.execute(query, (min_records,))
    available_stocks = cursor.fetchall()
    conn.close()

    if len(available_stocks) < size:
        raise ValueError(
            f"Not enough stocks with {min_records}+ records. "
            f"Found {len(available_stocks)}, need {size}"
        )

    # Randomly select stocks
    selected = rand.sample(available_stocks, size)
    symbols = [stock[0] for stock in selected]

    print(f"\nRandomly selected {size} stocks:")
    for i, (symbol, sector) in enumerate(selected, 1):
        print(f"  {i}. {symbol} ({sector})")

    return symbols


# Example usage
if __name__ == "__main__":
    import random

    print("Testing Portfolio Fitness Evaluator\n")

    # Set random seed
    if config.RANDOM_SEED is not None:
        random.seed(config.RANDOM_SEED)
        np.random.seed(config.RANDOM_SEED)

    # Use configured portfolio or select random
    if config.AUTO_SELECT_PORTFOLIO:
        symbols = select_random_portfolio(
            size=config.PORTFOLIO_SIZE,
            seed=config.RANDOM_SEED
        )
    else:
        symbols = config.PORTFOLIO_STOCKS[:config.PORTFOLIO_SIZE]

    print(f"\nPortfolio ({len(symbols)} stocks): {', '.join(symbols)}")

    # Create portfolio evaluator
    evaluator = PortfolioFitnessEvaluator(
        symbols=symbols,
        start_date='2019-01-01',
        end_date='2019-12-31'
    )

    # Test with a sample trader
    print("\n" + "=" * 60)
    print("Testing with sample trader")
    print("=" * 60)

    trader = GeneticTrader([14, 70, 30, 3.0, 8.0, 15.0])
    print("\nTrader genes:")
    print(trader.get_genes())

    # Get detailed results
    print("\nRunning portfolio backtest...")
    results = evaluator.get_detailed_results(trader)

    print(f"\nPortfolio Results ({results['num_stocks']} stocks):")
    print(f"  Total Return: {results['total_return']:.2f}%")
    print(f"  Sharpe Ratio: {results['sharpe_ratio']:.4f}")
    print(f"  Max Drawdown: {results['max_drawdown']:.2f}%")
    print(f"  Trade Count: {results['trade_count']}")
    print(f"  Win Rate: {results['win_rate']:.2f}%")
    print(f"  Fitness Score: {results['fitness']:.4f}")

    # Show per-stock breakdown
    print("\n" + "=" * 60)
    print("Per-Stock Performance:")
    print("=" * 60)

    per_stock = evaluator.get_per_stock_results(trader)
    for symbol, stats in sorted(per_stock.items()):
        print(f"\n{symbol}:")
        print(f"  Return: {stats['return_pct']:>8.2f}%")
        print(f"  Trades: {stats['trades']:>8}")
        print(f"  Won:    {stats['won']:>8}")
