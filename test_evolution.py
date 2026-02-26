"""
Quick test to verify the entire evolution system works end-to-end.
Runs a minimal evolution (2 generations, 5 traders) to test integration.
"""

import random
import numpy as np
from evolve import GeneticAlgorithm
import config

if __name__ == "__main__":
    print("=" * 60)
    print("QUICK EVOLUTION TEST")
    print("Running 2 generations with 5 traders")
    print("=" * 60)

    # Set random seed
    if config.RANDOM_SEED:
        random.seed(config.RANDOM_SEED)
        np.random.seed(config.RANDOM_SEED)

    # Create a minimal genetic algorithm
    ga = GeneticAlgorithm(
        symbol="AAPL",
        start_date="2019-01-01",  # Smaller date range for speed
        end_date="2019-12-31",
        population_size=5,  # Small population
        num_generations=2   # Just 2 generations
    )

    try:
        # Run evolution
        ga.evolve()

        print("\n" + "=" * 60)
        print("✓ INTEGRATION TEST PASSED")
        print("=" * 60)
        print("\nThe complete evolution cycle works correctly!")
        print("You can now run the full evolution with:")
        print("  python evolve.py")
        print("\nOr customize parameters in config.py and run again.")

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ INTEGRATION TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
