"""
Main evolution loop for genetic trading algorithm.
Orchestrates the evolutionary process to find optimal trading strategies.
"""

import random
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import json
import config
from data_loader import DataLoader
from population import Population
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
        num_generations: int = None
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
                self.portfolio_symbols = select_random_portfolio(
                    size=config.PORTFOLIO_SIZE,
                    seed=config.RANDOM_SEED
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

        # Initialize components
        self.population = Population(size=self.population_size)

        # Track evolution history
        self.history = {
            'generation': [],
            'best_fitness': [],
            'avg_fitness': [],
            'worst_fitness': [],
            'std_fitness': [],
        }

        # Execution timestamp
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _create_directories(self):
        """Create output directories if they don't exist."""
        for dir_name in [config.RESULTS_DIR, config.LOGS_DIR, config.CHECKPOINT_DIR]:
            Path(dir_name).mkdir(exist_ok=True)

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
        print("=" * 60)

        for generation in range(self.num_generations):
            print(f"\n{'=' * 60}")
            print(f"Generation {generation + 1}/{self.num_generations}")
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
            if generation < self.num_generations - 1:
                print("\nEvolving to next generation...")
                self.population.evolve_generation()

        # Final results
        self._display_final_results()
        self._save_final_results()

    def _display_statistics(self, stats: dict):
        """Display generation statistics."""
        print(f"\nGeneration {stats['generation']} Statistics:")
        print(f"  Evaluated: {stats['evaluated']}/{stats['size']}")
        print(f"  Best Fitness: {stats['best_fitness']:.4f}")
        print(f"  Average Fitness: {stats['avg_fitness']:.4f}")
        print(f"  Worst Fitness: {stats['worst_fitness']:.4f}")
        print(f"  Std Dev: {stats['std_fitness']:.4f}")

        # Display best trader
        best = self.population.get_best_trader()
        if best:
            print(f"\nBest Trader Genes:")
            for name, value in best.get_genes().items():
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

            # Calculate and display buy-and-hold benchmark
            print("\nBenchmark Comparison:")
            try:
                if self.use_portfolio:
                    # Portfolio buy-and-hold with same allocation as strategy
                    # Access data_feeds from underlying evaluator
                    data_feeds = getattr(self.evaluator, 'data_feeds', None)
                    if data_feeds:
                        benchmark = calculate_portfolio_buy_and_hold(
                            data_feeds,
                            initial_capital=config.INITIAL_CASH,
                            allocation_pct=config.INITIAL_ALLOCATION_PCT
                        )
                        print(f"  Buy-and-Hold Return (Portfolio, {config.INITIAL_ALLOCATION_PCT}% allocated): {benchmark['total_return']:.2f}%")
                    else:
                        print("  Buy-and-Hold: Unable to calculate (no data feeds)")
                        benchmark = {'total_return': 0.0}
                else:
                    # Single stock buy-and-hold
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
        if self.use_portfolio:
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

        summary = {
            'run_id': self.run_id,
            'mode': 'portfolio' if self.use_portfolio else 'single_stock',
            'symbol': self.symbol if not self.use_portfolio else None,
            'portfolio_symbols': self.portfolio_symbols if self.use_portfolio else None,
            'portfolio_size': len(self.portfolio_symbols) if self.use_portfolio else 1,
            'initial_allocation_pct': config.INITIAL_ALLOCATION_PCT if self.use_portfolio else None,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'population_size': self.population_size,
            'num_generations': self.num_generations,
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
                }
            },
            'benchmark': {
                'buy_and_hold_return': benchmark.get('total_return'),
                'allocation_pct': benchmark.get('allocation_pct', 100.0),
                'strategy_outperformance': comparison.get('outperformance'),
                'beats_benchmark': comparison.get('beats_benchmark'),
            }
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
    # Create and run genetic algorithm
    ga = GeneticAlgorithm(
        symbol=config.TEST_SYMBOL,
        start_date=config.TRAIN_START_DATE,
        end_date=config.TRAIN_END_DATE,
        population_size=config.POPULATION_SIZE,
        num_generations=config.NUM_GENERATIONS
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
