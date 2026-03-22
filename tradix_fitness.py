"""
Tradix-based portfolio fitness evaluation for genetic trading algorithm.

Drop-in replacement for portfolio_fitness.py when BACKTESTING_ENGINE = 'tradix'.
Implements the same interface: calculate_fitness(), evaluate_population(),
get_detailed_results().
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

import config
from genetic_trader import GeneticTrader
from tradix_strategy import TradixPortfolioStrategy
from tradix.datafeed.feed import DataFeed as TradixDataFeed


class _DataFrameFeed(TradixDataFeed):
    """
    Tradix DataFeed backed by an in-memory pandas DataFrame.

    Tradix does not provide a built-in feed for pre-loaded DataFrames,
    so this thin subclass wraps one. The DataFrame must have a
    DatetimeIndex and columns: open, high, low, close, volume.
    """

    def __init__(self, df: pd.DataFrame, symbol: str):
        start = str(df.index.min().date()) if len(df) > 0 else '2000-01-01'
        end = str(df.index.max().date()) if len(df) > 0 else '2099-12-31'
        super().__init__(symbol=symbol, startDate=start, endDate=end)
        self._source_df = df

    def load(self) -> pd.DataFrame:
        """Return the pre-loaded DataFrame."""
        if self._loaded and self._data is not None:
            return self._data

        df = self._source_df.copy()

        # Ensure DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # Strip timezone
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Keep only OHLCV
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                raise ValueError(f"DataFrame missing required column: {col}")

        df = df[['open', 'high', 'low', 'close', 'volume']]
        df = df.dropna(subset=['open', 'high', 'low', 'close'])

        self._data = df
        self._buildNumpyArrays()
        self._loaded = True
        return self._data


class TradixPortfolioFitnessEvaluator:
    """
    Evaluates fitness of genetic traders using Tradix MultiAssetEngine.

    Same interface as PortfolioFitnessEvaluator so evolve.py and
    ParallelFitnessEvaluator work without modification.
    """

    def __init__(self, symbols: List[str], start_date: str, end_date: str):
        """
        Initialize Tradix portfolio fitness evaluator.

        Args:
            symbols: List of stock symbols to trade.
            start_date: Start date for training data.
            end_date: End date for training data.
        """
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = config.INITIAL_CASH
        self.commission = config.COMMISSION

        # Load data from configured source
        self._load_data()

        # Pre-compute fold boundaries (same logic as portfolio_fitness.py)
        self.folds = self._compute_folds()

    def _load_data(self):
        """Load stock data from the configured data source."""
        data_source = getattr(config, 'DATA_SOURCE', 'sqlite')

        if data_source == 'yahoo':
            from yahoo_data_loader import YahooDataLoader
            loader = YahooDataLoader()
            print(f"\nLoading portfolio data from Yahoo Finance for {len(self.symbols)} stocks...")
        else:
            from data_loader import DataLoader
            loader = DataLoader(config.DATABASE_PATH)
            print(f"\nLoading portfolio data from SQLite for {len(self.symbols)} stocks...")

        self.data_feeds = {}

        for symbol in self.symbols:
            try:
                df = loader.load_stock_data(
                    symbol,
                    start_date=self.start_date,
                    end_date=self.end_date,
                )
                self.data_feeds[symbol] = df
                print(f"  + {symbol}: {len(df)} bars")
            except Exception as e:
                print(f"  - {symbol}: Failed to load - {e}")

        self.valid_symbols = list(self.data_feeds.keys())
        print(f"\nLoaded {len(self.valid_symbols)}/{len(self.symbols)} stocks")

        if len(self.valid_symbols) == 0:
            raise ValueError("No valid stock data loaded!")

        # Load macro data if enabled
        self.macro_df = None
        if getattr(config, 'USE_MACRO_DATA', False):
            try:
                macro_df = loader.load_macro_data(
                    start_date=self.start_date,
                    end_date=self.end_date,
                )
                if macro_df is not None and not macro_df.empty:
                    self.macro_df = macro_df
                    # Report which columns have data
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

    # ------------------------------------------------------------------
    # K-fold computation (same as portfolio_fitness.py)
    # ------------------------------------------------------------------

    def _compute_folds(self) -> List[Tuple[str, str]]:
        """Compute fold date boundaries from config."""
        if not getattr(config, 'USE_KFOLD_VALIDATION', False):
            return [(self.start_date, self.end_date)]

        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        total_days = (end - start).days

        fold_years = getattr(config, 'KFOLD_FOLD_YEARS', 3)
        fold_days = int(fold_years * 365.25)
        num_folds = getattr(config, 'KFOLD_NUM_FOLDS', 2)
        allow_overlap = getattr(config, 'KFOLD_ALLOW_OVERLAP', False)

        fold_days = min(fold_days, total_days)

        if num_folds <= 1:
            return [(self.start_date, self.end_date)]

        if allow_overlap:
            stride = (total_days - fold_days) / (num_folds - 1)
        else:
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

    # ------------------------------------------------------------------
    # Fitness scoring (same formula as portfolio_fitness.py)
    # ------------------------------------------------------------------

    def _score_results(self, results: Dict[str, Any]) -> float:
        """Compute fitness from backtest results."""
        total_return = results['total_return']
        sharpe_ratio = results['sharpe_ratio']
        max_drawdown = results['max_drawdown']
        win_rate = results['win_rate']
        trade_count = results['trade_count']

        if trade_count < config.MIN_TRADES_REQUIRED:
            return -100.0

        fitness = (
            config.FITNESS_WEIGHTS['total_return'] * total_return
            + config.FITNESS_WEIGHTS['sharpe_ratio'] * sharpe_ratio * 10
            + config.FITNESS_WEIGHTS['max_drawdown'] * max_drawdown
            + config.FITNESS_WEIGHTS['win_rate'] * win_rate
        )
        return fitness

    def _aggregate_fold_scores(
        self, fold_scores: List[Tuple[int, float]]
    ) -> float:
        """Aggregate per-fold fitness scores."""
        use_weighting = getattr(config, 'KFOLD_WEIGHT_RECENT', False)
        weight_factor = getattr(config, 'KFOLD_RECENT_WEIGHT_FACTOR', 1.5)

        if not use_weighting:
            scores = [score for _, score in fold_scores]
            return sum(scores) / len(scores)

        num_folds = len(fold_scores)
        weights = []
        for i in range(num_folds):
            w = 1.0 + (weight_factor - 1.0) * (i / max(1, num_folds - 1))
            weights.append(w)

        weighted_sum = sum(
            w * score for w, (_, score) in zip(weights, fold_scores)
        )
        return weighted_sum / sum(weights)

    # ------------------------------------------------------------------
    # Core fitness calculation
    # ------------------------------------------------------------------

    def calculate_fitness(self, trader: GeneticTrader) -> float:
        """
        Calculate fitness score for a trader across the portfolio.

        When K-fold is enabled, runs independent backtests on each
        time fold and averages the scores.
        """
        try:
            if len(self.folds) == 1:
                results = self._run_portfolio_backtest(trader)
                return self._score_results(results)

            fold_scores = []
            min_bars = getattr(config, 'KFOLD_MIN_BARS_PER_FOLD', 200)

            for fold_idx, (fold_start, fold_end) in enumerate(self.folds):
                fold_data = {}
                for symbol, df in self.data_feeds.items():
                    sliced = df.loc[fold_start:fold_end]
                    if len(sliced) >= min_bars:
                        fold_data[symbol] = sliced.copy()

                if not fold_data:
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
                score = self._score_results(results)
                fold_scores.append((fold_idx, score))

            if not fold_scores:
                return -100.0

            return self._aggregate_fold_scores(fold_scores)

        except Exception as e:
            print(f"Error evaluating trader: {e}")
            import traceback
            traceback.print_exc()
            return -1000.0

    # ------------------------------------------------------------------
    # Tradix backtest runner
    # ------------------------------------------------------------------

    def _run_portfolio_backtest(
        self,
        trader: GeneticTrader,
        fold_data_feeds: Optional[Dict[str, pd.DataFrame]] = None,
        fold_macro_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Run backtest using Tradix MultiAssetEngine.

        Returns the same dict format as PortfolioFitnessEvaluator
        so that scoring and reporting work identically.
        """
        from tradix import MultiAssetEngine
        from tradix.datafeed import MultiDataFeed
        from tradix.engine import SimpleBroker

        data_feeds = fold_data_feeds if fold_data_feeds is not None else self.data_feeds
        macro_df = fold_macro_df if fold_macro_df is not None else self.macro_df
        symbols = list(data_feeds.keys())

        genes = trader.get_genes()

        # Prepare supplementary data (stock DF with TI + macro columns)
        supp_data = {}
        for symbol, df in data_feeds.items():
            if macro_df is not None:
                from data_loader import DataLoader
                merged = DataLoader.merge_macro_into_stock(df, macro_df)
                supp_data[symbol] = merged
            else:
                supp_data[symbol] = df

        # Normalize index to date-only for supplementary data lookups
        for symbol in supp_data:
            sdf = supp_data[symbol]
            if hasattr(sdf.index, 'date') and not isinstance(sdf.index, pd.DatetimeIndex):
                pass
            elif isinstance(sdf.index, pd.DatetimeIndex):
                if sdf.index.tz is not None:
                    sdf = sdf.copy()
                    sdf.index = sdf.index.tz_localize(None)
                sdf = sdf.copy()
                sdf.index = sdf.index.date
                supp_data[symbol] = sdf

        # Build Tradix data feeds from DataFrames
        feeds = {}
        for symbol, df in data_feeds.items():
            # Ensure OHLCV columns are present and properly named
            feed_df = df[['open', 'high', 'low', 'close', 'volume']].copy()
            if isinstance(feed_df.index, pd.DatetimeIndex) and feed_df.index.tz is not None:
                feed_df.index = feed_df.index.tz_localize(None)
            feeds[symbol] = _DataFrameFeed(feed_df, symbol=symbol)

        multi_feed = MultiDataFeed(feeds, alignMethod='inner', fillMethod='ffill')

        # Configure strategy
        strategy = TradixPortfolioStrategy()
        strategy._gene_params = dict(genes)
        strategy._gene_params['initial_allocation_pct'] = config.INITIAL_ALLOCATION_PCT
        strategy._supp_data = supp_data

        # Configure broker
        broker = SimpleBroker(
            commissionRate=self.commission,
            taxRate=0.0,
            slippageRate=0.0,
        )

        # Run backtest
        engine = MultiAssetEngine(
            data=multi_feed,
            strategy=strategy,
            initialCash=self.initial_cash,
            broker=broker,
            fillOnNextBar=True,
        )

        result = engine.run(verbose=False)

        # Extract metrics
        return self._extract_results(result, strategy, symbols)

    def _extract_results(self, result, strategy, symbols) -> Dict[str, Any]:
        """
        Map Tradix MultiAssetResult to the standard results dict
        expected by _score_results() and evolve.py.
        """
        starting_value = self.initial_cash
        final_equity = result.finalEquity

        # Total return as percentage
        total_return = ((final_equity - starting_value) / starting_value) * 100

        # Sharpe ratio (clamped to [-5, 5])
        sharpe_ratio = result.metrics.get('sharpeRatio', 0.0)
        if sharpe_ratio is None:
            sharpe_ratio = 0.0
        sharpe_ratio = max(-5.0, min(5.0, float(sharpe_ratio)))

        # Max drawdown as negative percentage
        max_dd = result.metrics.get('maxDrawdown', 0.0)
        if max_dd is None:
            max_dd = 0.0
        max_drawdown = -abs(float(max_dd))

        # Trade statistics from strategy tracking
        trade_count = strategy.trade_count
        winning_trades = strategy.winning_trades
        win_rate = (
            (winning_trades / trade_count * 100) if trade_count > 0 else 0.0
        )

        # Per-stock performance
        per_stock_performance = {}
        for symbol in symbols:
            stock_data = strategy.trades_by_symbol.get(symbol, {
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
                    if trades_count > 0 else 0.0
                ),
            }

        return {
            'starting_value': starting_value,
            'ending_value': final_equity,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': trade_count,
            'winning_trades': winning_trades,
            'per_stock_performance': per_stock_performance,
        }

    # ------------------------------------------------------------------
    # Population evaluation
    # ------------------------------------------------------------------

    def evaluate_population(
        self, traders: List[GeneticTrader]
    ) -> List[GeneticTrader]:
        """Evaluate fitness for all traders in a population."""
        for i, trader in enumerate(traders):
            fitness = self.calculate_fitness(trader)
            trader.set_fitness(fitness)

            if (i + 1) % 5 == 0:
                print(f"Evaluated {i + 1}/{len(traders)} traders")

        return traders

    # ------------------------------------------------------------------
    # Detailed results
    # ------------------------------------------------------------------

    def get_detailed_results(
        self, trader: GeneticTrader
    ) -> Dict[str, Any]:
        """Get detailed backtest results including K-fold breakdown."""
        if len(self.folds) == 1:
            results = self._run_portfolio_backtest(trader)
            results['genes'] = trader.get_genes()
            results['fitness'] = self.calculate_fitness(trader)
            results['num_stocks'] = len(self.valid_symbols)
            results['symbols'] = self.valid_symbols
            return results

        # K-fold: collect per-fold results
        fold_results = []
        min_bars = getattr(config, 'KFOLD_MIN_BARS_PER_FOLD', 200)

        for fold_idx, (fold_start, fold_end) in enumerate(self.folds):
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

        # Aggregate
        valid = [r for r in fold_results if not r.get('skipped')]
        aggregate = {
            'total_return': np.mean([r['total_return'] for r in valid]),
            'sharpe_ratio': np.mean([r['sharpe_ratio'] for r in valid]),
            'max_drawdown': np.mean([r['max_drawdown'] for r in valid]),
            'win_rate': np.mean([r['win_rate'] for r in valid]),
            'trade_count': sum(r['trade_count'] for r in valid),
            'winning_trades': sum(r['winning_trades'] for r in valid),
        }

        # Aggregate per-stock data
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
