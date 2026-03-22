"""
Timing benchmark: backtrader vs vectorbt fitness evaluation.

Compares wall-clock time for evaluating a population of traders
using both engines and reports the speedup ratio.
"""

import time
import random
import numpy as np
import config
from genetic_trader import GeneticTrader


BENCHMARK_SYMBOLS = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META']
BENCHMARK_START = '2020-01-01'
BENCHMARK_END = '2022-12-31'
NUM_TRADERS = 10


def make_random_traders(n: int):
    """Create n random traders."""
    random.seed(42)
    np.random.seed(42)
    return [GeneticTrader() for _ in range(n)]


def benchmark_vectorbt(traders):
    """Time vectorbt evaluator."""
    from vectorbt_fitness import VectorbtFitnessEvaluator

    evaluator = VectorbtFitnessEvaluator(
        symbols=BENCHMARK_SYMBOLS,
        start_date=BENCHMARK_START,
        end_date=BENCHMARK_END,
    )

    start = time.perf_counter()
    evaluator.evaluate_population(traders)
    elapsed = time.perf_counter() - start
    return elapsed


def benchmark_backtrader(traders):
    """Time backtrader evaluator (sequential, no parallel wrapper)."""
    from portfolio_fitness import PortfolioFitnessEvaluator

    evaluator = PortfolioFitnessEvaluator(
        symbols=BENCHMARK_SYMBOLS,
        start_date=BENCHMARK_START,
        end_date=BENCHMARK_END,
    )

    start = time.perf_counter()
    evaluator.evaluate_population(traders)
    elapsed = time.perf_counter() - start
    return elapsed


if __name__ == '__main__':
    print("=" * 60)
    print("Benchmark: backtrader vs vectorbt")
    print(f"Portfolio: {BENCHMARK_SYMBOLS}")
    print(f"Period: {BENCHMARK_START} to {BENCHMARK_END}")
    print(f"Traders: {NUM_TRADERS}")
    print("=" * 60)

    # Create identical traders for both engines
    traders_bt = make_random_traders(NUM_TRADERS)
    traders_vbt = make_random_traders(NUM_TRADERS)

    print("\n--- backtrader ---")
    bt_time = benchmark_backtrader(traders_bt)
    print(f"backtrader: {bt_time:.2f}s")

    print("\n--- vectorbt ---")
    vbt_time = benchmark_vectorbt(traders_vbt)
    print(f"vectorbt: {vbt_time:.2f}s")

    speedup = bt_time / vbt_time if vbt_time > 0 else float('inf')
    print(f"\n{'=' * 60}")
    print(f"Speedup: {speedup:.1f}x")
    print(f"{'=' * 60}")

    if speedup >= 5:
        print("PASS: vectorbt is at least 5x faster")
    else:
        print(f"NOTE: speedup is {speedup:.1f}x (target: 5x+)")
