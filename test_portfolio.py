"""
Test script for portfolio-based evolution.
Quick test with 3 generations, 5 traders, 5 stocks.
"""

import random
import numpy as np
from evolve import GeneticAlgorithm
import config

if __name__ == "__main__":
    print("=" * 60)
    print("PORTFOLIO EVOLUTION TEST")
    print("Running 3 generations with 5 traders on 5-stock portfolio")
    print("=" * 60)

    # Set random seed
    if config.RANDOM_SEED:
        random.seed(config.RANDOM_SEED)
        np.random.seed(config.RANDOM_SEED)

    # Test portfolio with 5 stocks (small for speed)
    test_portfolio = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'WMT']

    # Temporarily override config
    original_use_portfolio = config.USE_PORTFOLIO
    original_portfolio = config.PORTFOLIO_STOCKS
    original_auto_select = config.AUTO_SELECT_PORTFOLIO

    config.USE_PORTFOLIO = True
    config.PORTFOLIO_STOCKS = test_portfolio
    config.AUTO_SELECT_PORTFOLIO = False

    try:
        # Create a minimal genetic algorithm
        ga = GeneticAlgorithm(
            start_date="2019-01-01",
            end_date="2019-12-31",
            population_size=5,
            num_generations=3
        )

        # Run evolution
        ga.evolve()

        print("\n" + "=" * 60)
        print("✓ PORTFOLIO TEST PASSED")
        print("=" * 60)
        print("\nThe portfolio evolution system works correctly!")
        print("\nKey benefits of portfolio mode:")
        print("  ✓ Tests strategy across multiple stocks")
        print("  ✓ Reduces overfitting to single stock")
        print("  ✓ More robust fitness evaluation")
        print("  ✓ Better generalization")
        print("\nYou can now run full evolution with:")
        print("  python evolve.py")

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ PORTFOLIO TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

    finally:
        # Restore config
        config.USE_PORTFOLIO = original_use_portfolio
        config.PORTFOLIO_STOCKS = original_portfolio
        config.AUTO_SELECT_PORTFOLIO = original_auto_select
