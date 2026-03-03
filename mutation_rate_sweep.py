"""
Mutation Rate Sweep Experiment.

Runs 10 evolutions with identical settings except mutation rate,
which varies from 20% to 80%. This isolates the effect of mutation
rate on trading strategy quality.

Usage:
    python mutation_rate_sweep.py
"""

import random
import numpy as np
import json
from datetime import datetime
from pathlib import Path

import config
from evolve import GeneticAlgorithm, convert_to_serializable
from portfolio_fitness import select_random_portfolio


def run_sweep():
    """Run the mutation rate sweep experiment."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Experiment parameters ---
    num_runs = 10
    mutation_rates = np.linspace(0.20, 0.80, num_runs).tolist()
    num_generations = 30
    population_size = 100
    portfolio_size = 20
    seed = 42

    print("=" * 60)
    print("MUTATION RATE SWEEP EXPERIMENT")
    print("=" * 60)
    print(f"Runs: {num_runs}")
    print(f"Mutation rates: {[f'{r:.3f}' for r in mutation_rates]}")
    print(f"Generations per run: {num_generations}")
    print(f"Population size: {population_size}")
    print(f"Portfolio size: {portfolio_size}")
    print(f"K-Folds: 5 (overlapping)")
    print(f"Features: Macro + TI + Ensemble")
    print(f"Seed: {seed}")

    # --- Select stocks once ---
    stocks = select_random_portfolio(size=portfolio_size, seed=seed)
    print(f"\nPortfolio ({len(stocks)} stocks):")
    print(f"  {', '.join(stocks)}")

    # --- Save original config values ---
    original = {}
    config_keys = [
        'AUTO_SELECT_PORTFOLIO', 'PORTFOLIO_STOCKS', 'PORTFOLIO_SIZE',
        'NUM_GENERATIONS', 'POPULATION_SIZE', 'MUTATION_RATE',
        'USE_KFOLD_VALIDATION', 'KFOLD_NUM_FOLDS', 'KFOLD_ALLOW_OVERLAP',
        'USE_MACRO_DATA', 'USE_TECHNICAL_INDICATORS', 'USE_ENSEMBLE_SIGNALS',
        'RANDOM_SEED',
    ]
    for key in config_keys:
        original[key] = getattr(config, key)

    # --- Override config with experiment values ---
    config.AUTO_SELECT_PORTFOLIO = False
    config.PORTFOLIO_STOCKS = stocks
    config.PORTFOLIO_SIZE = portfolio_size
    config.NUM_GENERATIONS = num_generations
    config.POPULATION_SIZE = population_size
    config.USE_KFOLD_VALIDATION = True
    config.KFOLD_NUM_FOLDS = 5
    config.KFOLD_ALLOW_OVERLAP = True
    config.USE_MACRO_DATA = True
    config.USE_TECHNICAL_INDICATORS = True
    config.USE_ENSEMBLE_SIGNALS = True
    config.RANDOM_SEED = seed

    # Ensure elitism is valid
    elitism = getattr(config, 'ELITISM_COUNT', 2)
    if elitism >= population_size:
        config.ELITISM_COUNT = max(1, population_size // 5)

    # --- Run sweep ---
    results = []

    try:
        for i, rate in enumerate(mutation_rates):
            print(f"\n{'=' * 60}")
            print(f"RUN {i + 1}/{num_runs} — Mutation Rate: {rate:.3f}")
            print(f"{'=' * 60}")

            # Reset seeds so each run starts with the same initial population
            random.seed(seed)
            np.random.seed(seed)

            config.MUTATION_RATE = rate

            try:
                ga = GeneticAlgorithm(
                    start_date=config.TRAIN_START_DATE,
                    end_date=config.TRAIN_END_DATE,
                    population_size=population_size,
                    num_generations=num_generations,
                )
                ga.evolve()
                ga.plot_evolution()

                # Collect results
                best = ga.population.best_trader
                detailed = ga.evaluator.get_detailed_results(best) if best else {}

                run_result = {
                    'mutation_rate': rate,
                    'run_id': ga.run_id,
                    'best_fitness': best.fitness if best else None,
                    'total_return': detailed.get('total_return'),
                    'sharpe_ratio': detailed.get('sharpe_ratio'),
                    'max_drawdown': detailed.get('max_drawdown'),
                    'trade_count': detailed.get('trade_count'),
                    'win_rate': detailed.get('win_rate'),
                    'best_generation': best.generation if best else None,
                    'fitness_history': ga.history.copy(),
                }
                results.append(run_result)

                print(f"\n--- Run {i + 1} Summary ---")
                print(f"  Mutation Rate: {rate:.3f}")
                print(f"  Best Fitness:  {run_result['best_fitness']:.4f}")
                print(f"  Total Return:  {run_result['total_return']:.2f}%")
                print(f"  Sharpe Ratio:  {run_result['sharpe_ratio']:.4f}")
                print(f"  Max Drawdown:  {run_result['max_drawdown']:.2f}%")
                print(f"  Trade Count:   {run_result['trade_count']}")
                print(f"  Win Rate:      {run_result['win_rate']:.2f}%")

            except Exception as e:
                print(f"\n  Run {i + 1} FAILED: {e}")
                results.append({
                    'mutation_rate': rate,
                    'run_id': None,
                    'best_fitness': None,
                    'error': str(e),
                })

    finally:
        # --- Restore original config ---
        for key, value in original.items():
            setattr(config, key, value)

    # --- Summary table ---
    print("\n" + "=" * 60)
    print("SWEEP RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Rate':>8} {'Fitness':>10} {'Return%':>10} {'Sharpe':>10} "
          f"{'MaxDD%':>10} {'Trades':>8} {'WinRate%':>10}")
    print("-" * 68)

    for r in results:
        if r.get('best_fitness') is not None:
            print(f"{r['mutation_rate']:8.3f} "
                  f"{r['best_fitness']:10.4f} "
                  f"{r['total_return']:10.2f} "
                  f"{r['sharpe_ratio']:10.4f} "
                  f"{r['max_drawdown']:10.2f} "
                  f"{r['trade_count']:8d} "
                  f"{r['win_rate']:10.2f}")
        else:
            print(f"{r['mutation_rate']:8.3f}    FAILED")

    # --- Save sweep results JSON ---
    Path(config.RESULTS_DIR).mkdir(exist_ok=True)
    sweep_file = f"{config.RESULTS_DIR}/mutation_sweep_{timestamp}.json"
    sweep_data = {
        'timestamp': timestamp,
        'experiment': 'mutation_rate_sweep',
        'portfolio_stocks': stocks,
        'portfolio_size': portfolio_size,
        'num_generations': num_generations,
        'population_size': population_size,
        'kfold_num_folds': 5,
        'kfold_allow_overlap': True,
        'macro_enabled': True,
        'ti_enabled': True,
        'ensemble_enabled': True,
        'seed': seed,
        'mutation_rates': mutation_rates,
        'results': results,
    }
    sweep_data = convert_to_serializable(sweep_data)

    with open(sweep_file, 'w') as f:
        json.dump(sweep_data, f, indent=2)
    print(f"\nSweep results saved to {sweep_file}")

    # --- Generate comparison chart ---
    _plot_sweep(results, timestamp)

    print("\n" + "=" * 60)
    print("SWEEP COMPLETE")
    print("=" * 60)


def _plot_sweep(results, timestamp):
    """Generate a multi-panel chart comparing mutation rates."""
    try:
        import matplotlib.pyplot as plt

        # Filter successful runs
        valid = [r for r in results if r.get('best_fitness') is not None]
        if not valid:
            print("No successful runs to plot.")
            return

        rates = [r['mutation_rate'] for r in valid]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Mutation Rate Sweep Experiment', fontsize=16,
                     fontweight='bold')

        # Panel 1: Best Fitness
        ax = axes[0, 0]
        fitness_vals = [r['best_fitness'] for r in valid]
        ax.plot(rates, fitness_vals, 'o-', color='#2196F3', linewidth=2,
                markersize=8)
        ax.set_xlabel('Mutation Rate')
        ax.set_ylabel('Best Fitness')
        ax.set_title('Best Fitness vs Mutation Rate')
        ax.grid(True, alpha=0.3)
        best_idx = np.argmax(fitness_vals)
        ax.annotate(f'{fitness_vals[best_idx]:.3f}',
                    xy=(rates[best_idx], fitness_vals[best_idx]),
                    textcoords="offset points", xytext=(0, 12),
                    ha='center', fontweight='bold', color='green')

        # Panel 2: Total Return
        ax = axes[0, 1]
        returns = [r['total_return'] for r in valid]
        colors = ['green' if v >= 0 else 'red' for v in returns]
        ax.bar(rates, returns, width=0.05, color=colors, alpha=0.7,
               edgecolor='black', linewidth=0.5)
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
        ax.set_xlabel('Mutation Rate')
        ax.set_ylabel('Total Return (%)')
        ax.set_title('Total Return vs Mutation Rate')
        ax.grid(True, alpha=0.3, axis='y')

        # Panel 3: Sharpe Ratio
        ax = axes[1, 0]
        sharpes = [r['sharpe_ratio'] for r in valid]
        ax.plot(rates, sharpes, 's-', color='#FF9800', linewidth=2,
                markersize=8)
        ax.set_xlabel('Mutation Rate')
        ax.set_ylabel('Sharpe Ratio')
        ax.set_title('Sharpe Ratio vs Mutation Rate')
        ax.grid(True, alpha=0.3)

        # Panel 4: Max Drawdown
        ax = axes[1, 1]
        drawdowns = [r['max_drawdown'] for r in valid]
        ax.plot(rates, drawdowns, 'D-', color='#F44336', linewidth=2,
                markersize=8)
        ax.set_xlabel('Mutation Rate')
        ax.set_ylabel('Max Drawdown (%)')
        ax.set_title('Max Drawdown vs Mutation Rate')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_file = f"results/mutation_sweep_{timestamp}.png"
        plt.savefig(plot_file, dpi=300)
        plt.close()
        print(f"Sweep chart saved to {plot_file}")

    except ImportError:
        print("matplotlib not available, skipping chart generation")


if __name__ == "__main__":
    run_sweep()
