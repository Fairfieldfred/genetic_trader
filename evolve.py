"""
Main evolution loop for genetic trading algorithm.
Orchestrates the evolutionary process to find optimal trading strategies.
"""

import random
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import json
import config
from data_loader import DataLoader
from population import Population
from genetic_trader import GeneticTrader
from portfolio_fitness import PortfolioFitnessEvaluator, select_random_portfolio
from parallel_fitness import enable_parallel_evaluation
from benchmark import calculate_buy_and_hold, calculate_portfolio_buy_and_hold, compare_to_benchmark


def convert_to_serializable(obj):
    """
    Convert numpy/pandas types to JSON-serializable Python native types.

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.ndarray, pd.Series)):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    elif pd.isna(obj):
        return None
    return obj


class GeneticAlgorithm:
    """Main genetic algorithm orchestrator."""

    def __init__(
        self,
        symbol: str = None,
        start_date: str = None,
        end_date: str = None,
        population_size: int = None,
        num_generations: int = None,
        resume_from: str = None
    ):
        """
        Initialize genetic algorithm.

        Args:
            symbol: Stock symbol to trade
            start_date: Start date for training data
            end_date: End date for training data
            population_size: Size of population
            num_generations: Number of generations to evolve
        """
        self.symbol = symbol or config.TEST_SYMBOL
        self.start_date = start_date or config.TRAIN_START_DATE
        self.end_date = end_date or config.TRAIN_END_DATE
        self.population_size = population_size or config.POPULATION_SIZE
        self.num_generations = num_generations or config.NUM_GENERATIONS

        # Set random seeds
        if config.RANDOM_SEED is not None:
            random.seed(config.RANDOM_SEED)
            np.random.seed(config.RANDOM_SEED)

        # Create output directories
        self._create_directories()

        # Determine if using portfolio or single stock
        self.use_portfolio = config.USE_PORTFOLIO

        if self.use_portfolio:
            # Portfolio mode
            print("\n" + "=" * 60)
            print("PORTFOLIO MODE")
            print("=" * 60)

            # Select stocks
            if config.AUTO_SELECT_PORTFOLIO:
                sectors = getattr(config, 'PORTFOLIO_SECTORS', [])
                self.portfolio_symbols = select_random_portfolio(
                    size=config.PORTFOLIO_SIZE,
                    seed=config.RANDOM_SEED,
                    sectors=sectors if sectors else None
                )
            else:
                self.portfolio_symbols = config.PORTFOLIO_STOCKS[:config.PORTFOLIO_SIZE]

            print(f"\nPortfolio size: {len(self.portfolio_symbols)} stocks")
            print(f"Symbols: {', '.join(self.portfolio_symbols)}")

            # Initialize portfolio evaluator
            self.evaluator = PortfolioFitnessEvaluator(
                symbols=self.portfolio_symbols,
                start_date=self.start_date,
                end_date=self.end_date
            )
            self.data = None  # Not used in portfolio mode

        else:
            # Single stock mode is deprecated - use portfolio mode with size=1
            raise ValueError(
                "Single stock mode is not supported. "
                "Please set USE_PORTFOLIO = True in config.py and use PORTFOLIO_SIZE = 1 "
                "for single-stock trading."
            )

        # Wrap evaluator with parallel processing if enabled
        if config.USE_PARALLEL_EVALUATION:
            print(f"\n⚡ Parallel evaluation enabled")
            self.evaluator = enable_parallel_evaluation(
                self.evaluator,
                max_workers=config.MAX_PARALLEL_WORKERS
            )
        else:
            print(f"\n Sequential evaluation (set USE_PARALLEL_EVALUATION=True for speedup)")

        # Display K-fold info
        folds = getattr(self.evaluator, 'folds', None)
        if folds and len(folds) > 1:
            print(f"\nK-Fold CV: {len(folds)} folds of ~{getattr(config, 'KFOLD_FOLD_YEARS', '?')} years each")
            for i, (fs, fe) in enumerate(folds):
                print(f"  Fold {i+1}: {fs} to {fe}")
            if getattr(config, 'KFOLD_WEIGHT_RECENT', False):
                print(f"  Recency weighting: factor {config.KFOLD_RECENT_WEIGHT_FACTOR}")
            print(f"  Note: {len(folds)}x backtests per trader per generation")

        # Initialize components
        self.population = Population(size=self.population_size)

        # Resume from previous run if requested
        self.resumed_from = None
        if resume_from:
            self._apply_resume(resume_from)

        # Track evolution history
        self.history = {
            'generation': [],
            'best_fitness': [],
            'avg_fitness': [],
            'worst_fitness': [],
            'std_fitness': [],
        }

        # Gene change tracking between generations
        self._prev_best_genes = None
        self._prev_best_fitness = None

        # Execution timestamp
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _create_directories(self):
        """Create output directories if they don't exist."""
        for dir_name in [config.RESULTS_DIR, config.LOGS_DIR, config.CHECKPOINT_DIR]:
            Path(dir_name).mkdir(exist_ok=True)

    def _apply_resume(self, run_id: str):
        """
        Load elite traders from a previous run and seed the population.

        Args:
            run_id: The run_id (YYYYMMDD_HHMMSS) of the run to resume from
        """
        summary_file = f"{config.RESULTS_DIR}/summary_{run_id}.json"
        if not Path(summary_file).exists():
            raise FileNotFoundError(
                f"Cannot resume: summary file not found at {summary_file}"
            )

        with open(summary_file, 'r') as f:
            summary = json.load(f)

        print("\n" + "=" * 60)
        print(f"RESUMING from run {run_id}")
        print("=" * 60)

        # Extract elite traders (fallback to single best_trader for old runs)
        elite_data = summary.get('elite_traders', [])
        if not elite_data:
            best_data = summary.get('best_trader', {})
            if best_data and best_data.get('genes'):
                # Reconstruct chromosome from genes for old-format runs
                chromosome = []
                genes = best_data['genes']
                for gene_name in config.GENE_ORDER:
                    if gene_name in genes:
                        chromosome.append(genes[gene_name])
                    else:
                        raise ValueError(
                            f"Gene '{gene_name}' not found in saved run. "
                            f"Config gene set has changed — cannot resume."
                        )
                elite_data = [{
                    'chromosome': chromosome,
                    'fitness': best_data.get('fitness'),
                    'generation': best_data.get('generation', 0),
                }]
            else:
                raise ValueError(
                    f"No elite traders or best trader found in {summary_file}"
                )

        # Validate chromosome length against current config
        expected_len = len(config.GENE_ORDER)
        first_len = len(elite_data[0].get('chromosome', []))
        if first_len != expected_len:
            raise ValueError(
                f"Chromosome length mismatch: saved run has {first_len} genes, "
                f"current config has {expected_len} genes. "
                f"Cannot resume with different gene configuration."
            )

        # Reconstruct traders
        seed_traders = []
        for data in elite_data:
            try:
                trader = GeneticTrader.from_dict(data)
                seed_traders.append(trader)
            except ValueError as e:
                print(f"  Warning: skipping invalid trader: {e}")

        if not seed_traders:
            raise ValueError("No valid traders could be loaded from saved run")

        # Get previous generation count for offset
        prev_generations = summary.get('num_generations', 0)
        # If the previous run was itself resumed, add its start offset
        prev_config = summary.get('config', {})
        prev_start_gen = summary.get('start_generation', 0)
        start_gen = prev_start_gen + prev_generations

        # Seed population
        self.population.seed_population(seed_traders, start_generation=start_gen)
        self.resumed_from = run_id

        print(f"  Loaded {len(seed_traders)} elite traders")
        print(f"  Population: {len(seed_traders)} elites + "
              f"{self.population_size - len(seed_traders)} random")
        print(f"  Continuing from generation {start_gen}")

        # Load previous history for continuity
        history_file = f"{config.RESULTS_DIR}/history_{run_id}.csv"
        if Path(history_file).exists():
            prev_history = pd.read_csv(history_file)
            self.history = {
                'generation': prev_history['generation'].tolist(),
                'best_fitness': prev_history['best_fitness'].tolist(),
                'avg_fitness': prev_history['avg_fitness'].tolist(),
                'worst_fitness': prev_history['worst_fitness'].tolist(),
                'std_fitness': prev_history['std_fitness'].tolist(),
            }
            print(f"  Loaded {len(prev_history)} generations of history")

    def evolve(self):
        """Run the genetic algorithm evolution process."""
        print("\n" + "=" * 60)
        print(f"Starting Genetic Algorithm Evolution")
        if self.use_portfolio:
            print(f"Mode: PORTFOLIO ({len(self.portfolio_symbols)} stocks)")
            print(f"Stocks: {', '.join(self.portfolio_symbols[:5])}{'...' if len(self.portfolio_symbols) > 5 else ''}")
        else:
            print(f"Mode: SINGLE STOCK ({self.symbol})")
        print(f"Population Size: {self.population_size}")
        print(f"Generations: {self.num_generations}")
        folds = getattr(self.evaluator, 'folds', None)
        if folds and len(folds) > 1:
            print(f"K-Fold CV: {len(folds)} folds")
        print("=" * 60)

        start_gen = self.population.generation
        total_display = start_gen + self.num_generations

        for i in range(self.num_generations):
            generation = start_gen + i

            print(f"\n{'=' * 60}")
            print(f"Generation {generation + 1}/{total_display}")
            print(f"{'=' * 60}")

            # Evaluate fitness
            print("Evaluating population fitness...")
            self.evaluator.evaluate_population(self.population.traders)

            # Get and display statistics
            stats = self.population.get_statistics()
            self._display_statistics(stats)

            # Save history
            self._save_generation_history(stats)

            # Save best trader periodically
            if (generation + 1) % config.SAVE_BEST_EVERY_N_GENERATIONS == 0:
                self._save_checkpoint(generation + 1)

            # Evolve to next generation (except on last iteration)
            if i < self.num_generations - 1:
                print("\nEvolving to next generation...")
                self.population.evolve_generation()

        # Final results
        self._display_final_results()

        # Out-of-sample test
        best = self.population.best_trader
        self._oos_results = None
        if best:
            self._oos_results = self._run_out_of_sample_test(best)

        self._save_final_results()

    def _display_statistics(self, stats: dict):
        """Display generation statistics."""
        print(f"\nGeneration {stats['generation']} Statistics:")
        print(f"  Evaluated: {stats['evaluated']}/{stats['size']}")
        print(f"  Best Fitness: {stats['best_fitness']:.4f}")
        print(f"  Average Fitness: {stats['avg_fitness']:.4f}")
        print(f"  Worst Fitness: {stats['worst_fitness']:.4f}")
        print(f"  Std Dev: {stats['std_fitness']:.4f}")

        # Display best trader and track gene changes
        best = self.population.get_best_trader()
        if best:
            current_genes = best.get_genes()
            current_fitness = stats['best_fitness']

            # Print gene changes when best fitness improves
            if self._prev_best_fitness is None:
                print("GENE_CHANGE: initial")
            elif current_fitness > self._prev_best_fitness:
                for name, new_val in current_genes.items():
                    old_val = self._prev_best_genes.get(name)
                    if old_val is None:
                        continue
                    if isinstance(new_val, float):
                        if old_val != 0 and abs(
                            (new_val - old_val) / old_val
                        ) < 0.01:
                            continue
                        print(
                            f"GENE_CHANGE: {name}: "
                            f"{old_val:.2f} -> {new_val:.2f}"
                        )
                    elif new_val != old_val:
                        print(
                            f"GENE_CHANGE: {name}: "
                            f"{old_val} -> {new_val}"
                        )

            self._prev_best_genes = dict(current_genes)
            self._prev_best_fitness = current_fitness

            print(f"\nBest Trader Genes:")
            for name, value in current_genes.items():
                if isinstance(value, float):
                    print(f"  {name}: {value:.2f}")
                else:
                    print(f"  {name}: {value}")

    def _save_generation_history(self, stats: dict):
        """Save generation statistics to history."""
        self.history['generation'].append(stats['generation'])
        self.history['best_fitness'].append(stats['best_fitness'])
        self.history['avg_fitness'].append(stats['avg_fitness'])
        self.history['worst_fitness'].append(stats['worst_fitness'])
        self.history['std_fitness'].append(stats['std_fitness'])

    def _save_checkpoint(self, generation: int):
        """Save checkpoint with best trader."""
        filename = f"{config.CHECKPOINT_DIR}/checkpoint_gen{generation}_{self.run_id}.json"
        self.population.save_best_trader(filename)

    def _display_final_results(self):
        """Display final evolution results."""
        print("\n" + "=" * 60)
        print("EVOLUTION COMPLETE")
        print("=" * 60)

        best = self.population.best_trader
        if best:
            print(f"\nBest Trader Found (Generation {best.generation}):")
            print(f"Fitness: {best.fitness:.4f}")
            print("\nGenes:")
            for name, value in best.get_genes().items():
                if isinstance(value, float):
                    print(f"  {name}: {value:.2f}")
                else:
                    print(f"  {name}: {value}")

            # Get detailed backtest results
            print("\nDetailed Performance Metrics:")
            results = self.evaluator.get_detailed_results(best)
            print(f"  Total Return: {results['total_return']:.2f}%")
            print(f"  Sharpe Ratio: {results['sharpe_ratio']:.4f}")
            print(f"  Max Drawdown: {results['max_drawdown']:.2f}%")
            print(f"  Total Trades: {results['trade_count']}")
            print(f"  Winning Trades: {results['winning_trades']}")
            print(f"  Win Rate: {results['win_rate']:.2f}%")

            # Display K-fold breakdown if available
            if 'kfold_results' in results:
                print("\nPer-Fold Breakdown:")
                for fr in results['kfold_results']:
                    if fr.get('skipped'):
                        print(f"  Fold {fr['fold']} ({fr['period']}): "
                              f"SKIPPED (insufficient data)")
                    else:
                        print(f"  Fold {fr['fold']} ({fr['period']}): "
                              f"Return={fr['total_return']:.2f}%, "
                              f"Sharpe={fr['sharpe_ratio']:.4f}, "
                              f"Trades={fr['trade_count']}")

            # Calculate and display buy-and-hold benchmark
            print("\nBenchmark Comparison:")
            try:
                data_feeds = getattr(self.evaluator, 'data_feeds', None)
                folds = getattr(self.evaluator, 'folds', None)
                use_kfold = folds and len(folds) > 1

                if self.use_portfolio and data_feeds:
                    if use_kfold:
                        # K-fold: average buy-and-hold across same folds
                        min_bars = getattr(config, 'KFOLD_MIN_BARS_PER_FOLD', 200)
                        fold_returns = []
                        for fold_start, fold_end in folds:
                            fold_feeds = {}
                            for sym, df in data_feeds.items():
                                sliced = df.loc[fold_start:fold_end]
                                if len(sliced) >= min_bars:
                                    fold_feeds[sym] = sliced
                            if fold_feeds:
                                bh = calculate_portfolio_buy_and_hold(
                                    fold_feeds,
                                    initial_capital=config.INITIAL_CASH,
                                    allocation_pct=config.INITIAL_ALLOCATION_PCT
                                )
                                fold_returns.append(bh['total_return'])
                        avg_bh_return = sum(fold_returns) / len(fold_returns) if fold_returns else 0.0
                        benchmark = {
                            'total_return': avg_bh_return,
                            'allocation_pct': config.INITIAL_ALLOCATION_PCT,
                        }
                        print(f"  Buy-and-Hold Return (avg across {len(fold_returns)} folds, "
                              f"{config.INITIAL_ALLOCATION_PCT}% allocated): {avg_bh_return:.2f}%")
                    else:
                        benchmark = calculate_portfolio_buy_and_hold(
                            data_feeds,
                            initial_capital=config.INITIAL_CASH,
                            allocation_pct=config.INITIAL_ALLOCATION_PCT
                        )
                        print(f"  Buy-and-Hold Return (Portfolio, {config.INITIAL_ALLOCATION_PCT}% allocated): {benchmark['total_return']:.2f}%")
                elif self.use_portfolio:
                    print("  Buy-and-Hold: Unable to calculate (no data feeds)")
                    benchmark = {'total_return': 0.0}
                else:
                    benchmark = calculate_buy_and_hold(
                        self.data,
                        initial_capital=config.INITIAL_CASH
                    )
                    print(f"  Buy-and-Hold Return ({self.symbol}): {benchmark['total_return']:.2f}%")

                # Compare strategy to benchmark
                comparison = compare_to_benchmark(results, benchmark)
                outperformance = comparison['outperformance']

                print(f"  Strategy Outperformance: {outperformance:+.2f}%")

                if comparison['beats_benchmark']:
                    improvement = (outperformance / abs(benchmark['total_return']) * 100) if benchmark['total_return'] != 0 else 0
                    print(f"  Strategy beats buy-and-hold by {improvement:.1f}%! 🎯")
                else:
                    print(f"  Strategy underperforms buy-and-hold ⚠️")

            except Exception as e:
                print(f"  Unable to calculate benchmark: {e}")
                benchmark = {'total_return': 0.0}

    def _run_out_of_sample_test(self, best):
        """
        Run the best trader on out-of-sample (test) data
        to evaluate generalization.

        Args:
            best: The best GeneticTrader from evolution

        Returns:
            Dictionary with out-of-sample results, or None
        """
        use_oos = getattr(config, 'USE_OUT_OF_SAMPLE_TEST', False)
        test_start = getattr(config, 'TEST_START_DATE', None)
        test_end = getattr(config, 'TEST_END_DATE', None)

        if not use_oos or not test_start or not test_end:
            return None

        print("\n" + "=" * 60)
        print("OUT-OF-SAMPLE TEST")
        print("=" * 60)
        print(f"Test period: {test_start} to {test_end}")

        try:
            # Create a new evaluator for the test period
            test_evaluator = PortfolioFitnessEvaluator(
                symbols=self.portfolio_symbols,
                start_date=test_start,
                end_date=test_end,
            )

            # Get detailed results on unseen data
            test_results = test_evaluator.get_detailed_results(best)

            print(f"\nOut-of-Sample Performance:")
            print(f"  Total Return: {test_results['total_return']:.2f}%")
            print(f"  Sharpe Ratio: {test_results['sharpe_ratio']:.4f}")
            print(f"  Max Drawdown: {test_results['max_drawdown']:.2f}%")
            print(f"  Total Trades: {test_results['trade_count']}")
            print(f"  Win Rate: {test_results['win_rate']:.2f}%")

            # Calculate test benchmark
            test_benchmark = calculate_portfolio_buy_and_hold(
                test_evaluator.data_feeds,
                initial_capital=config.INITIAL_CASH,
                allocation_pct=config.INITIAL_ALLOCATION_PCT,
            )
            test_comparison = compare_to_benchmark(
                test_results, test_benchmark
            )

            print(f"\nTest Benchmark Comparison:")
            print(f"  Buy-and-Hold Return: "
                  f"{test_benchmark['total_return']:.2f}%")
            print(f"  Strategy Outperformance: "
                  f"{test_comparison['outperformance']:+.2f}%")
            if test_comparison['beats_benchmark']:
                print(f"  Strategy beats benchmark on unseen data!")
            else:
                print(f"  Strategy underperforms on unseen data")

            return {
                'enabled': True,
                'test_start_date': test_start,
                'test_end_date': test_end,
                'performance': {
                    'total_return': test_results.get('total_return'),
                    'sharpe_ratio': test_results.get('sharpe_ratio'),
                    'max_drawdown': test_results.get('max_drawdown'),
                    'trade_count': test_results.get('trade_count'),
                    'win_rate': test_results.get('win_rate'),
                },
                'benchmark': {
                    'buy_and_hold_return': test_benchmark.get(
                        'total_return'
                    ),
                    'outperformance': test_comparison.get(
                        'outperformance'
                    ),
                    'beats_benchmark': test_comparison.get(
                        'beats_benchmark'
                    ),
                },
                'per_stock_performance': test_results.get(
                    'per_stock_performance'
                ),
            }

        except Exception as e:
            print(f"\n  Out-of-sample test failed: {e}")
            return {
                'enabled': True,
                'error': str(e),
                'test_start_date': test_start,
                'test_end_date': test_end,
            }

    def _save_final_results(self):
        """Save final results to files."""
        # Save best trader
        best_trader_file = f"{config.RESULTS_DIR}/best_trader_{self.run_id}.json"
        self.population.save_best_trader(best_trader_file)

        # Save evolution history
        history_file = f"{config.RESULTS_DIR}/history_{self.run_id}.csv"
        history_df = pd.DataFrame(self.history)
        history_df.to_csv(history_file, index=False)
        print(f"\nEvolution history saved to {history_file}")

        # Save configuration and summary
        summary_file = f"{config.RESULTS_DIR}/summary_{self.run_id}.json"
        best = self.population.best_trader
        results = self.evaluator.get_detailed_results(best) if best else {}

        # Calculate benchmark with same allocation as strategy
        folds = getattr(self.evaluator, 'folds', None)
        use_kfold = folds and len(folds) > 1
        if self.use_portfolio:
            if use_kfold:
                # K-fold: average buy-and-hold across same folds
                min_bars = getattr(config, 'KFOLD_MIN_BARS_PER_FOLD', 200)
                fold_returns = []
                for fold_start, fold_end in folds:
                    fold_feeds = {}
                    for sym, df in self.evaluator.data_feeds.items():
                        sliced = df.loc[fold_start:fold_end]
                        if len(sliced) >= min_bars:
                            fold_feeds[sym] = sliced
                    if fold_feeds:
                        bh = calculate_portfolio_buy_and_hold(
                            fold_feeds,
                            initial_capital=config.INITIAL_CASH,
                            allocation_pct=config.INITIAL_ALLOCATION_PCT
                        )
                        fold_returns.append(bh['total_return'])
                avg_bh_return = sum(fold_returns) / len(fold_returns) if fold_returns else 0.0
                benchmark = {
                    'total_return': avg_bh_return,
                    'allocation_pct': config.INITIAL_ALLOCATION_PCT,
                }
            else:
                benchmark = calculate_portfolio_buy_and_hold(
                    self.evaluator.data_feeds,
                    initial_capital=config.INITIAL_CASH,
                    allocation_pct=config.INITIAL_ALLOCATION_PCT
                )
        else:
            benchmark = calculate_buy_and_hold(
                self.data,
                initial_capital=config.INITIAL_CASH
            )

        # Compare to benchmark
        comparison = compare_to_benchmark(results, benchmark) if best else {}

        start_gen = self.population.generation - self.num_generations + 1
        if start_gen < 0:
            start_gen = 0

        summary = {
            'run_id': self.run_id,
            'resumed_from': self.resumed_from,
            'start_generation': start_gen,
            'mode': 'portfolio' if self.use_portfolio else 'single_stock',
            'symbol': self.symbol if not self.use_portfolio else None,
            'portfolio_symbols': self.portfolio_symbols if self.use_portfolio else None,
            'portfolio_size': len(self.portfolio_symbols) if self.use_portfolio else 1,
            'initial_allocation_pct': config.INITIAL_ALLOCATION_PCT if self.use_portfolio else None,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'population_size': self.population_size,
            'num_generations': self.num_generations,
            'config': {
                'ga_parameters': {
                    'population_size': self.population_size,
                    'num_generations': self.num_generations,
                    'mutation_rate': config.MUTATION_RATE,
                    'crossover_rate': config.CROSSOVER_RATE,
                    'elitism_count': config.ELITISM_COUNT,
                    'tournament_size': config.TOURNAMENT_SIZE,
                    'random_seed': config.RANDOM_SEED,
                },
                'portfolio': {
                    'use_portfolio': config.USE_PORTFOLIO,
                    'portfolio_size': config.PORTFOLIO_SIZE,
                    'auto_select_portfolio': config.AUTO_SELECT_PORTFOLIO,
                    'portfolio_sectors': getattr(config, 'PORTFOLIO_SECTORS', []),
                    'portfolio_stocks': self.portfolio_symbols if self.use_portfolio else None,
                },
                'dates': {
                    'train_start_date': self.start_date,
                    'train_end_date': self.end_date,
                    'test_start_date': getattr(config, 'TEST_START_DATE', None),
                    'test_end_date': getattr(config, 'TEST_END_DATE', None),
                },
                'kfold': {
                    'use_kfold_validation': getattr(config, 'USE_KFOLD_VALIDATION', False),
                    'kfold_num_folds': getattr(config, 'KFOLD_NUM_FOLDS', 2),
                    'kfold_fold_years': getattr(config, 'KFOLD_FOLD_YEARS', 3),
                    'kfold_allow_overlap': getattr(config, 'KFOLD_ALLOW_OVERLAP', False),
                    'kfold_weight_recent': getattr(config, 'KFOLD_WEIGHT_RECENT', False),
                    'kfold_recent_weight_factor': getattr(config, 'KFOLD_RECENT_WEIGHT_FACTOR', 1.5),
                    'kfold_min_bars_per_fold': getattr(config, 'KFOLD_MIN_BARS_PER_FOLD', 200),
                },
                'features': {
                    'use_macro_data': getattr(config, 'USE_MACRO_DATA', False),
                    'use_technical_indicators': getattr(config, 'USE_TECHNICAL_INDICATORS', False),
                    'use_ensemble_signals': getattr(config, 'USE_ENSEMBLE_SIGNALS', False),
                },
                'backtrader': {
                    'initial_cash': config.INITIAL_CASH,
                    'commission': config.COMMISSION,
                    'initial_allocation_pct': config.INITIAL_ALLOCATION_PCT,
                },
                'fitness': {
                    'fitness_weights': config.FITNESS_WEIGHTS.copy(),
                    'min_trades_required': config.MIN_TRADES_REQUIRED,
                },
                'execution': {
                    'use_parallel_evaluation': config.USE_PARALLEL_EVALUATION,
                    'max_parallel_workers': config.MAX_PARALLEL_WORKERS,
                    'database_path': config.DATABASE_PATH,
                },
            },
            'best_trader': {
                'generation': best.generation if best else None,
                'fitness': best.fitness if best else None,
                'genes': best.get_genes() if best else None,
                'performance': {
                    'total_return': results.get('total_return'),
                    'sharpe_ratio': results.get('sharpe_ratio'),
                    'max_drawdown': results.get('max_drawdown'),
                    'trade_count': results.get('trade_count'),
                    'win_rate': results.get('win_rate'),
                },
                'per_stock_performance': results.get('per_stock_performance'),
            },
            'elite_traders': [
                {
                    'generation': t.generation,
                    'fitness': t.fitness,
                    'chromosome': t.chromosome,
                    'genes': t.get_genes(),
                }
                for t in self.population.get_top_traders(config.ELITISM_COUNT)
            ],
            'benchmark': {
                'buy_and_hold_return': benchmark.get('total_return'),
                'allocation_pct': benchmark.get('allocation_pct', 100.0),
                'strategy_outperformance': comparison.get('outperformance'),
                'beats_benchmark': comparison.get('beats_benchmark'),
            },
            'kfold': {
                'enabled': getattr(config, 'USE_KFOLD_VALIDATION', False),
                'num_folds': len(getattr(self.evaluator, 'folds', [(None, None)])),
                'fold_years': getattr(config, 'KFOLD_FOLD_YEARS', None),
                'allow_overlap': getattr(config, 'KFOLD_ALLOW_OVERLAP', False),
                'weight_recent': getattr(config, 'KFOLD_WEIGHT_RECENT', False),
                'fold_results': results.get('kfold_results'),
            },
            'out_of_sample': self._oos_results,
        }

        # Convert all numpy/pandas types to native Python types for JSON serialization
        summary = convert_to_serializable(summary)

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Summary saved to {summary_file}")

    def plot_evolution(self):
        """Plot evolution progress (optional, requires matplotlib)."""
        try:
            import matplotlib.pyplot as plt

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

            generations = self.history['generation']

            # Plot fitness over time
            ax1.plot(generations, self.history['best_fitness'], label='Best', linewidth=2)
            ax1.plot(generations, self.history['avg_fitness'], label='Average', linewidth=2)
            ax1.fill_between(
                generations,
                np.array(self.history['avg_fitness']) - np.array(self.history['std_fitness']),
                np.array(self.history['avg_fitness']) + np.array(self.history['std_fitness']),
                alpha=0.3
            )
            ax1.set_xlabel('Generation')
            ax1.set_ylabel('Fitness')
            ax1.set_title('Fitness Evolution Over Generations')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # Plot fitness range
            ax2.fill_between(
                generations,
                self.history['worst_fitness'],
                self.history['best_fitness'],
                alpha=0.5,
                label='Fitness Range'
            )
            ax2.plot(generations, self.history['avg_fitness'], 'r-', linewidth=2, label='Average')
            ax2.set_xlabel('Generation')
            ax2.set_ylabel('Fitness')
            ax2.set_title('Fitness Range Over Generations')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            plot_file = f"{config.RESULTS_DIR}/evolution_{self.run_id}.png"
            plt.savefig(plot_file, dpi=300)
            print(f"Evolution plot saved to {plot_file}")
            plt.close()

        except ImportError:
            print("matplotlib not available, skipping plot generation")


# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Run genetic algorithm evolution for trading strategies'
    )
    parser.add_argument(
        '--resume',
        type=str,
        default=None,
        help='Resume from a previous run by specifying its run_id '
             '(e.g., 20260306_074305)'
    )
    args = parser.parse_args()

    # Create and run genetic algorithm
    ga = GeneticAlgorithm(
        symbol=config.TEST_SYMBOL,
        start_date=config.TRAIN_START_DATE,
        end_date=config.TRAIN_END_DATE,
        population_size=config.POPULATION_SIZE,
        num_generations=config.NUM_GENERATIONS,
        resume_from=args.resume
    )

    # Run evolution
    ga.evolve()

    # Optional: plot results
    try:
        ga.plot_evolution()
    except Exception as e:
        print(f"Could not generate plot: {e}")

    print("\n" + "=" * 60)
    print("Evolution complete! Check the results directory for outputs.")
    print("=" * 60)
