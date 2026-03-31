"""
Portfolio-based fitness evaluation for genetic trading algorithm.
Tests strategy across multiple stocks for better generalization.
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
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

        # Select data source based on config
        data_source = getattr(config, 'DATA_SOURCE', 'sqlite')
        if data_source == 'yahoo':
            from yahoo_data_loader import YahooDataLoader
            loader = YahooDataLoader()
            print(f"\nLoading portfolio data from Yahoo Finance for {len(symbols)} stocks...")
        else:
            loader = DataLoader(config.DATABASE_PATH)
            print(f"\nLoading portfolio data from SQLite for {len(symbols)} stocks...")

        self.data_feeds = {}

        # Cache data in memory to avoid repeated disk I/O
        for symbol in symbols:
            try:
                df = loader.load_stock_data(
                    symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                self.data_feeds[symbol] = df
                print(f"  + {symbol}: {len(df)} bars")
            except Exception as e:
                print(f"  - {symbol}: Failed to load - {e}")

        self.valid_symbols = list(self.data_feeds.keys())
        print(f"\nLoaded {len(self.valid_symbols)}/{len(symbols)} stocks")

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
                    available = [c for c in macro_df.columns if macro_df[c].notna().any()]
                    missing = [c for c in macro_df.columns if macro_df[c].isna().all()]
                    print(f"\n  Macro data loaded: {len(macro_df)} rows")
                    if available:
                        print(f"    Available: {', '.join(available)}")
                    if missing:
                        print(f"    Missing (neutral defaults): {', '.join(missing)}")
                else:
                    print("\n  Macro data: not available — macro genes will use neutral defaults")
            except Exception as e:
                print(f"\n  Macro data: not available ({e}) — macro genes will use neutral defaults")

        # Pre-compute fold boundaries
        self.folds = self._compute_folds()

    def _compute_folds(self) -> List[Tuple[str, str]]:
        """
        Compute fold date boundaries from config.

        Supports both non-overlapping and overlapping (sliding window)
        folds. When overlapping, fold starts are evenly spaced so that
        the first fold begins at the data start and the last fold ends
        at (or near) the data end.

        Returns:
            List of (start_date, end_date) tuples.
            Returns a single fold covering the full range when
            K-fold is disabled.
        """
        if not getattr(config, 'USE_KFOLD_VALIDATION', False):
            return [(self.start_date, self.end_date)]

        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        total_days = (end - start).days

        fold_years = getattr(config, 'KFOLD_FOLD_YEARS', 3)
        fold_days = int(fold_years * 365.25)
        num_folds = getattr(config, 'KFOLD_NUM_FOLDS', 2)
        allow_overlap = getattr(config, 'KFOLD_ALLOW_OVERLAP', False)

        # Clamp fold length to not exceed total span
        fold_days = min(fold_days, total_days)

        if num_folds <= 1:
            return [(self.start_date, self.end_date)]

        if allow_overlap:
            # Sliding window: evenly space fold starts across the span
            stride = (total_days - fold_days) / (num_folds - 1)
        else:
            # Non-overlapping: stride = fold_days, cap num_folds
            stride = fold_days
            num_folds = min(num_folds, max(1, total_days // fold_days))

        folds = []
        for i in range(num_folds):
            fold_start = start + timedelta(days=int(i * stride))
            fold_end = fold_start + timedelta(days=fold_days - 1)
            fold_end = min(fold_end, end)
            folds.append((
                fold_start.strftime('%Y-%m-%d'),
                fold_end.strftime('%Y-%m-%d'),
            ))

        return folds

    def _score_results(self, results: Dict[str, Any]) -> float:
        """
        Compute a fitness score from backtest results.

        Args:
            results: Dict with total_return, sharpe_ratio,
                     max_drawdown, win_rate, trade_count

        Returns:
            Fitness score, or -100.0 if minimum trade
            requirement not met.
        """
        total_return = results['total_return']
        sharpe_ratio = results['sharpe_ratio']
        max_drawdown = results['max_drawdown']
        win_rate = results['win_rate']
        trade_count = results['trade_count']

        if trade_count < config.MIN_TRADES_REQUIRED:
            return -100.0

        fitness = (
            config.FITNESS_WEIGHTS['total_return'] * total_return +
            config.FITNESS_WEIGHTS['sharpe_ratio'] * sharpe_ratio * 10 +
            config.FITNESS_WEIGHTS['max_drawdown'] * max_drawdown +
            config.FITNESS_WEIGHTS['win_rate'] * win_rate
        )
        return fitness

    def _aggregate_fold_scores(
        self,
        fold_scores: List[Tuple[int, float]],
    ) -> float:
        """
        Aggregate per-fold fitness scores into a single value.

        Args:
            fold_scores: List of (fold_index, score) tuples.

        Returns:
            Aggregated fitness score.
        """
        use_weighting = getattr(
            config, 'KFOLD_WEIGHT_RECENT', False
        )
        weight_factor = getattr(
            config, 'KFOLD_RECENT_WEIGHT_FACTOR', 1.5
        )

        if not use_weighting:
            scores = [score for _, score in fold_scores]
            return sum(scores) / len(scores)

        # Linearly increasing weights: first fold = 1.0,
        # last fold = weight_factor
        num_folds = len(fold_scores)
        weights = []
        for i in range(num_folds):
            w = 1.0 + (weight_factor - 1.0) * (
                i / max(1, num_folds - 1)
            )
            weights.append(w)

        weighted_sum = sum(
            w * score
            for w, (_, score) in zip(weights, fold_scores)
        )
        total_weight = sum(weights)
        return weighted_sum / total_weight

    def calculate_fitness(self, trader: GeneticTrader) -> float:
        """
        Calculate fitness score for a trader across the portfolio.

        When K-fold is enabled, runs independent backtests on each
        time fold and averages the scores.

        Args:
            trader: GeneticTrader to evaluate

        Returns:
            Fitness score (higher is better)
        """
        try:
            if len(self.folds) == 1:
                # Single fold — existing behavior
                results = self._run_portfolio_backtest(trader)
                return self._score_results(results)

            # K-fold: run backtest per fold, aggregate
            fold_scores = []
            min_bars = getattr(
                config, 'KFOLD_MIN_BARS_PER_FOLD', 200
            )

            for fold_idx, (fold_start, fold_end) in enumerate(
                self.folds
            ):
                # Slice data_feeds to this fold's date range
                fold_data = {}
                for symbol, df in self.data_feeds.items():
                    sliced = df.loc[fold_start:fold_end]
                    if len(sliced) >= min_bars:
                        fold_data[symbol] = sliced.copy()

                if not fold_data:
                    continue

                # Slice macro data for this fold
                fold_macro = None
                if self.macro_df is not None:
                    fm = self.macro_df.loc[fold_start:fold_end]
                    if not fm.empty:
                        fold_macro = fm

                results = self._run_portfolio_backtest(
                    trader,
                    fold_data_feeds=fold_data,
                    fold_macro_df=fold_macro,
                )
                score = self._score_results(results)
                fold_scores.append((fold_idx, score))

            if not fold_scores:
                return -100.0

            return self._aggregate_fold_scores(fold_scores)

        except Exception as e:
            print(f"Error evaluating trader: {e}")
            return -1000.0

    def _run_portfolio_backtest(
        self,
        trader: GeneticTrader,
        fold_data_feeds: Dict[str, pd.DataFrame] = None,
        fold_macro_df: pd.DataFrame = None,
    ) -> Dict[str, Any]:
        """
        Run backtest on portfolio using one strategy.

        Args:
            trader: GeneticTrader to backtest
            fold_data_feeds: Optional date-filtered data feeds
                (uses self.data_feeds when None)
            fold_macro_df: Optional date-filtered macro data
                (uses self.macro_df when None)

        Returns:
            Dictionary with aggregated performance metrics
        """
        # Use fold-specific or full data
        data_feeds = (
            fold_data_feeds
            if fold_data_feeds is not None
            else self.data_feeds
        )
        symbols = list(data_feeds.keys())
        macro_df = (
            fold_macro_df
            if fold_macro_df is not None
            else self.macro_df
        )

        # Create Cerebro instance
        cerebro = bt.Cerebro()

        # Add strategy (will apply to all data feeds)
        strategy_class = create_strategy_from_trader(
            trader,
            use_portfolio=True,
            initial_allocation_pct=config.INITIAL_ALLOCATION_PCT
        )
        cerebro.addstrategy(strategy_class, printlog=False)

        # Add all stock data feeds
        use_macro = macro_df is not None
        for symbol in symbols:
            stock_df = data_feeds[symbol]

            # Always use MacroAwarePandasData so ensemble and TI
            # data lines are available (missing columns return NaN
            # which _get_line() handles safely)
            if use_macro:
                merged = DataLoader.merge_macro_into_stock(
                    stock_df, macro_df
                )
                data_feed = MacroAwarePandasData(
                    dataname=merged,
                    name=symbol
                )
            else:
                data_feed = MacroAwarePandasData(
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

        # Sharpe ratio (clamped to realistic range;
        # Backtrader can return extreme values on short periods)
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe_analysis.get('sharperatio', 0.0)
        if sharpe_ratio is None:
            sharpe_ratio = 0.0
        sharpe_ratio = max(-5.0, min(5.0, float(sharpe_ratio)))

        # Max drawdown
        drawdown_analysis = strat.analyzers.drawdown.get_analysis()
        max_drawdown = -drawdown_analysis.get('max', {}).get('drawdown', 100.0)

        # Trade statistics
        trade_analysis = strat.analyzers.trades.get_analysis()
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0.0

        # Extract per-stock trade data from strategy
        per_stock_performance = {}
        for symbol in symbols:
            stock_data = strat.trades_by_symbol.get(symbol, {
                'trades': 0, 'won': 0, 'lost': 0, 'pnl': 0.0,
            })
            trades_count = stock_data['trades']
            per_stock_performance[symbol] = {
                'trades': trades_count,
                'won': stock_data['won'],
                'lost': stock_data['lost'],
                'pnl': round(stock_data['pnl'], 2),
                'win_rate': (
                    (stock_data['won'] / trades_count * 100)
                    if trades_count > 0
                    else 0.0
                ),
            }

        return {
            'starting_value': starting_value,
            'ending_value': ending_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': total_trades,
            'winning_trades': won_trades,
            'per_stock_performance': per_stock_performance,
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
        Includes per-fold breakdowns when K-fold is enabled.

        Args:
            trader: GeneticTrader to evaluate

        Returns:
            Dictionary with detailed performance metrics
        """
        if len(self.folds) == 1:
            results = self._run_portfolio_backtest(trader)
            results['genes'] = trader.get_genes()
            results['fitness'] = self.calculate_fitness(trader)
            results['num_stocks'] = len(self.valid_symbols)
            results['symbols'] = self.valid_symbols
            return results

        # K-fold: collect per-fold results
        fold_results = []
        min_bars = getattr(
            config, 'KFOLD_MIN_BARS_PER_FOLD', 200
        )

        for fold_idx, (fold_start, fold_end) in enumerate(
            self.folds
        ):
            fold_data = {}
            for symbol, df in self.data_feeds.items():
                sliced = df.loc[fold_start:fold_end]
                if len(sliced) >= min_bars:
                    fold_data[symbol] = sliced.copy()

            if not fold_data:
                fold_results.append({
                    'fold': fold_idx + 1,
                    'period': f"{fold_start} to {fold_end}",
                    'skipped': True,
                })
                continue

            fold_macro = None
            if self.macro_df is not None:
                fm = self.macro_df.loc[fold_start:fold_end]
                if not fm.empty:
                    fold_macro = fm

            results = self._run_portfolio_backtest(
                trader,
                fold_data_feeds=fold_data,
                fold_macro_df=fold_macro,
            )
            results['fold'] = fold_idx + 1
            results['period'] = f"{fold_start} to {fold_end}"
            results['num_stocks_in_fold'] = len(fold_data)
            results['skipped'] = False
            fold_results.append(results)

        # Aggregate for summary
        valid = [r for r in fold_results if not r.get('skipped')]
        aggregate = {
            'total_return': np.mean(
                [r['total_return'] for r in valid]
            ),
            'sharpe_ratio': np.mean(
                [r['sharpe_ratio'] for r in valid]
            ),
            'max_drawdown': np.mean(
                [r['max_drawdown'] for r in valid]
            ),
            'win_rate': np.mean(
                [r['win_rate'] for r in valid]
            ),
            'trade_count': sum(
                r['trade_count'] for r in valid
            ),
            'winning_trades': sum(
                r['winning_trades'] for r in valid
            ),
        }

        # Aggregate per-stock data across folds
        combined_per_stock = {}
        for r in valid:
            for sym, data in r.get('per_stock_performance', {}).items():
                if sym not in combined_per_stock:
                    combined_per_stock[sym] = {
                        'trades': 0, 'won': 0, 'lost': 0, 'pnl': 0.0,
                    }
                combined_per_stock[sym]['trades'] += data['trades']
                combined_per_stock[sym]['won'] += data['won']
                combined_per_stock[sym]['lost'] += data['lost']
                combined_per_stock[sym]['pnl'] += data['pnl']
        for sym, data in combined_per_stock.items():
            data['win_rate'] = (
                (data['won'] / data['trades'] * 100)
                if data['trades'] > 0 else 0.0
            )
            data['pnl'] = round(data['pnl'], 2)
        aggregate['per_stock_performance'] = combined_per_stock

        aggregate['genes'] = trader.get_genes()
        aggregate['fitness'] = self.calculate_fitness(trader)
        aggregate['num_stocks'] = len(self.valid_symbols)
        aggregate['symbols'] = self.valid_symbols
        aggregate['kfold_results'] = fold_results

        return aggregate

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
    seed: int = None,
    sectors: List[str] = None
) -> List[str]:
    """
    Randomly select stocks for portfolio.

    When DATA_SOURCE is 'yahoo', selects from a built-in list of liquid
    US large-cap stocks (no local database required). Otherwise queries
    the SQLite database.

    Args:
        size: Number of stocks to select
        min_records: Minimum number of data records required
        seed: Random seed for reproducibility
        sectors: Optional list of sectors to filter by (e.g. ['Technology', 'Healthcare'])

    Returns:
        List of stock symbols
    """
    import random as rand

    if seed is not None:
        rand.seed(seed)

    data_source = getattr(config, 'DATA_SOURCE', 'sqlite')

    if data_source == 'yahoo':
        return _select_portfolio_yahoo(size, seed, sectors, rand)

    return _select_portfolio_sqlite(size, min_records, sectors, rand)


# Liquid US large-caps grouped by sector for Yahoo-based portfolio selection
_YAHOO_STOCK_UNIVERSE = {
    'Technology': [
        'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AVGO', 'ADBE', 'CRM',
        'CSCO', 'INTC', 'AMD', 'ORCL', 'TXN', 'QCOM', 'IBM', 'NOW',
        'AMAT', 'MU', 'LRCX', 'KLAC',
    ],
    'Healthcare': [
        'JNJ', 'UNH', 'PFE', 'ABT', 'TMO', 'MRK', 'LLY', 'ABBV',
        'DHR', 'BMY', 'AMGN', 'MDT', 'GILD', 'ISRG', 'SYK', 'CVS',
        'CI', 'ZTS', 'VRTX', 'REGN',
    ],
    'Financials': [
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'SCHW', 'AXP',
        'C', 'USB', 'PNC', 'TFC', 'COF', 'BK', 'CME', 'ICE',
        'MMC', 'AON', 'MET', 'PRU',
    ],
    'Consumer Discretionary': [
        'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'SBUX', 'TJX',
        'BKNG', 'CMG', 'MAR', 'ORLY', 'ROST', 'DHI', 'LEN', 'GM',
        'F', 'YUM', 'DG', 'DLTR',
    ],
    'Consumer Staples': [
        'PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'CL',
        'EL', 'MDLZ', 'GIS', 'KMB', 'SYY', 'HSY', 'KHC', 'STZ',
        'ADM', 'CAG', 'CPB', 'SJM',
    ],
    'Energy': [
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO',
        'PXD', 'OXY', 'HAL', 'DVN', 'HES', 'WMB', 'KMI', 'OKE',
    ],
    'Industrials': [
        'CAT', 'GE', 'HON', 'UNP', 'UPS', 'BA', 'RTX', 'DE',
        'LMT', 'MMM', 'GD', 'NOC', 'WM', 'EMR', 'ITW', 'ETN',
        'FDX', 'CSX', 'NSC', 'PCAR',
    ],
    'Utilities': [
        'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'EXC', 'XEL',
        'WEC', 'ES', 'ED', 'AWK', 'PEG', 'DTE', 'EIX', 'FE',
    ],
    'Real Estate': [
        'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'WELL',
        'DLR', 'AVB', 'EQR', 'VTR', 'ARE', 'MAA', 'UDR', 'ESS',
    ],
    'Materials': [
        'LIN', 'APD', 'SHW', 'ECL', 'FCX', 'NEM', 'NUE', 'DOW',
        'DD', 'PPG', 'VMC', 'MLM', 'ALB', 'CE', 'EMN', 'IP',
    ],
    'Communication Services': [
        'GOOG', 'DIS', 'CMCSA', 'NFLX', 'T', 'VZ', 'TMUS', 'CHTR',
        'EA', 'ATVI', 'TTWO', 'WBD', 'PARA', 'FOX', 'OMC', 'IPG',
    ],
}


def _select_portfolio_yahoo(size, seed, sectors, rand):
    """Select portfolio symbols from built-in stock universe."""
    use_sector_filter = sectors and len(sectors) > 0

    if use_sector_filter:
        pool = []
        for sector in sectors:
            matched = _YAHOO_STOCK_UNIVERSE.get(sector, [])
            pool.extend([(sym, sector) for sym in matched])
        if len(pool) < size:
            raise ValueError(
                f"Not enough stocks in sectors {sectors}. "
                f"Found {len(pool)}, need {size}"
            )
        selected = rand.sample(pool, size)
        symbols = [s[0] for s in selected]
        filter_label = f" from sectors: {', '.join(sectors)}"
        print(f"\nRandomly selected {size} stocks{filter_label}:")
        for i, (sym, sec) in enumerate(selected, 1):
            print(f"  {i}. {sym} ({sec})")
    else:
        pool = []
        for sector, syms in _YAHOO_STOCK_UNIVERSE.items():
            pool.extend([(sym, sector) for sym in syms])
        if len(pool) < size:
            raise ValueError(
                f"Not enough stocks in universe. "
                f"Found {len(pool)}, need {size}"
            )
        selected = rand.sample(pool, size)
        symbols = [s[0] for s in selected]
        print(f"\nRandomly selected {size} stocks (Yahoo universe):")
        for i, (sym, sec) in enumerate(selected, 1):
            print(f"  {i}. {sym} ({sec})")

    return symbols


def _select_portfolio_sqlite(size, min_records, sectors, rand):
    """Select portfolio symbols from SQLite database."""
    import sqlite3

    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()

    use_sector_filter = sectors and len(sectors) > 0

    if use_sector_filter:
        placeholders = ','.join(['?' for _ in sectors])
        query = f"""
            SELECT di.symbol, s.sector
            FROM daily_indicators di
            JOIN stocks s ON di.symbol = s.symbol
            WHERE s.sector IN ({placeholders})
            GROUP BY di.symbol
            HAVING COUNT(*) >= ?
            ORDER BY di.symbol
        """
        params = list(sectors) + [min_records]
    else:
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='stocks'"
        )
        has_stocks_table = cursor.fetchone() is not None

        if has_stocks_table:
            query = """
                SELECT di.symbol, COALESCE(s.sector, 'N/A')
                FROM daily_indicators di
                LEFT JOIN stocks s ON di.symbol = s.symbol
                GROUP BY di.symbol
                HAVING COUNT(*) >= ?
                ORDER BY di.symbol
            """
        else:
            query = """
                SELECT symbol
                FROM daily_indicators
                GROUP BY symbol
                HAVING COUNT(*) >= ?
                ORDER BY symbol
            """
        params = [min_records]

    cursor.execute(query, params)
    available_stocks = cursor.fetchall()
    conn.close()

    if len(available_stocks) < size:
        sector_msg = f" in sectors {sectors}" if use_sector_filter else ""
        raise ValueError(
            f"Not enough stocks with {min_records}+ records{sector_msg}. "
            f"Found {len(available_stocks)}, need {size}"
        )

    selected = rand.sample(available_stocks, size)
    symbols = [stock[0] for stock in selected]

    has_sector_col = len(selected[0]) > 1 if selected else False
    filter_label = f" from sectors: {', '.join(sectors)}" if use_sector_filter else ""
    print(f"\nRandomly selected {size} stocks{filter_label}:")
    for i, stock in enumerate(selected, 1):
        label = f"{stock[0]} ({stock[1]})" if has_sector_col else stock[0]
        print(f"  {i}. {label}")

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
        sectors = getattr(config, 'PORTFOLIO_SECTORS', [])
        symbols = select_random_portfolio(
            size=config.PORTFOLIO_SIZE,
            seed=config.RANDOM_SEED,
            sectors=sectors if sectors else None
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
