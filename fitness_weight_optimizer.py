"""
Optimizes fitness weights using various strategies.
Faster than full hyperparameter optimization - focuses only on fitness weights.
"""

import numpy as np
import random
from typing import Dict, List, Tuple
import json
from datetime import datetime
import config
from evolve import GeneticAlgorithm


class FitnessWeightOptimizer:
    """
    Optimizes fitness function weights to maximize performance.
    Uses grid search, random search, or Bayesian optimization.
    """

    def __init__(
        self,
        symbol: str = None,
        start_date: str = None,
        end_date: str = None
    ):
        """
        Initialize fitness weight optimizer.

        Args:
            symbol: Stock symbol (or None for portfolio)
            start_date: Training start date
            end_date: Training end date
        """
        self.symbol = symbol or config.TEST_SYMBOL
        self.start_date = start_date or config.TRAIN_START_DATE
        self.end_date = end_date or config.TRAIN_END_DATE

        self.results = []
        self.best_weights = None
        self.best_fitness = float('-inf')

    def generate_weight_combinations(
        self,
        n_samples: int = 20,
        method: str = 'random'
    ) -> List[Dict[str, float]]:
        """
        Generate combinations of fitness weights.

        Args:
            n_samples: Number of combinations to generate
            method: 'grid', 'random', or 'simplex'

        Returns:
            List of weight dictionaries
        """
        if method == 'random':
            return self._random_weights(n_samples)
        elif method == 'grid':
            return self._grid_weights()
        elif method == 'simplex':
            return self._simplex_samples(n_samples)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _random_weights(self, n: int) -> List[Dict[str, float]]:
        """
        Generate random weight combinations using Dirichlet distribution.
        Ensures weights sum to 1.0.

        Args:
            n: Number of combinations

        Returns:
            List of weight dictionaries
        """
        combinations = []

        for _ in range(n):
            # Dirichlet distribution (random simplex point)
            weights = np.random.dirichlet([1, 1, 1, 1])

            combinations.append({
                'total_return': weights[0],
                'sharpe_ratio': weights[1],
                'max_drawdown': weights[2],
                'win_rate': weights[3],
            })

        return combinations

    def _grid_weights(self, step: float = 0.1) -> List[Dict[str, float]]:
        """
        Generate grid of weight combinations.

        Args:
            step: Grid step size

        Returns:
            List of weight dictionaries
        """
        combinations = []

        # Generate all combinations that sum to 1.0
        for w1 in np.arange(0.1, 0.8, step):
            for w2 in np.arange(0.1, 0.8, step):
                for w3 in np.arange(0.1, 0.8, step):
                    w4 = 1.0 - w1 - w2 - w3
                    if 0.0 <= w4 <= 1.0:
                        combinations.append({
                            'total_return': w1,
                            'sharpe_ratio': w2,
                            'max_drawdown': w3,
                            'win_rate': w4,
                        })

        return combinations

    def _simplex_samples(self, n: int) -> List[Dict[str, float]]:
        """
        Sample uniformly from weight simplex (sum to 1).

        Args:
            n: Number of samples

        Returns:
            List of weight dictionaries
        """
        combinations = []

        for _ in range(n):
            # Uniform simplex sampling
            values = np.sort(np.random.random(3))
            w1 = values[0]
            w2 = values[1] - values[0]
            w3 = values[2] - values[1]
            w4 = 1.0 - values[2]

            combinations.append({
                'total_return': w1,
                'sharpe_ratio': w2,
                'max_drawdown': w3,
                'win_rate': w4,
            })

        return combinations

    def optimize(
        self,
        n_trials: int = 20,
        generations: int = 20,
        method: str = 'random'
    ) -> Dict[str, float]:
        """
        Optimize fitness weights.

        Args:
            n_trials: Number of weight combinations to test
            generations: Generations per trial
            method: Sampling method ('random', 'grid', 'simplex')

        Returns:
            Best fitness weights
        """
        print(f"\n{'=' * 60}")
        print(f"FITNESS WEIGHT OPTIMIZATION")
        print(f"Method: {method}, Trials: {n_trials}")
        print(f"{'=' * 60}")

        # Generate weight combinations
        weight_combinations = self.generate_weight_combinations(n_trials, method)

        print(f"\nGenerated {len(weight_combinations)} weight combinations")

        # Test each combination
        for i, weights in enumerate(weight_combinations):
            print(f"\n[{i + 1}/{len(weight_combinations)}] Testing weights:")
            self._print_weights(weights)

            # Evaluate
            fitness = self._evaluate_weights(weights, generations)

            self.results.append({
                'weights': weights,
                'best_fitness': fitness,
                'trial': i + 1
            })

            if fitness > self.best_fitness:
                self.best_fitness = fitness
                self.best_weights = weights
                print(f"  🎯 New best! Fitness: {fitness:.4f}")

        return self.best_weights

    def _evaluate_weights(
        self,
        weights: Dict[str, float],
        generations: int
    ) -> float:
        """
        Evaluate fitness weights by running evolution.

        Args:
            weights: Fitness weights to test
            generations: Number of generations

        Returns:
            Best fitness achieved
        """
        # Temporarily override fitness weights
        original_weights = config.FITNESS_WEIGHTS.copy()
        config.FITNESS_WEIGHTS = weights

        try:
            # Run evolution
            ga = GeneticAlgorithm(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                num_generations=generations
            )

            ga.evolve()

            # Return best fitness
            return ga.population.best_trader.fitness

        except Exception as e:
            print(f"  ✗ Evaluation failed: {e}")
            return float('-inf')

        finally:
            # Restore original weights
            config.FITNESS_WEIGHTS = original_weights

    def _print_weights(self, weights: Dict[str, float]):
        """Print weights in readable format."""
        total = sum(weights.values())
        print(f"    Total Return:  {weights['total_return']:.2f} ({weights['total_return']/total*100:.1f}%)")
        print(f"    Sharpe Ratio:  {weights['sharpe_ratio']:.2f} ({weights['sharpe_ratio']/total*100:.1f}%)")
        print(f"    Max Drawdown:  {weights['max_drawdown']:.2f} ({weights['max_drawdown']/total*100:.1f}%)")
        print(f"    Win Rate:      {weights['win_rate']:.2f} ({weights['win_rate']/total*100:.1f}%)")
        print(f"    Sum:           {total:.2f}")

    def print_best_weights(self):
        """Print the best weights found."""
        if self.best_weights is None:
            print("No optimization run yet!")
            return

        print("\n" + "=" * 60)
        print("BEST FITNESS WEIGHTS")
        print("=" * 60)
        print(f"Best Fitness Achieved: {self.best_fitness:.4f}\n")
        self._print_weights(self.best_weights)

        print("\n" + "=" * 60)
        print("COPY TO config.py:")
        print("=" * 60)
        print()
        print("FITNESS_WEIGHTS = {")
        print(f"    'total_return': {self.best_weights['total_return']:.3f},")
        print(f"    'sharpe_ratio': {self.best_weights['sharpe_ratio']:.3f},")
        print(f"    'max_drawdown': {self.best_weights['max_drawdown']:.3f},")
        print(f"    'win_rate': {self.best_weights['win_rate']:.3f},")
        print("}")

    def save_results(self, filepath: str = None):
        """Save optimization results."""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"results/fitness_weight_optimization_{timestamp}.json"

        output = {
            'best_weights': self.best_weights,
            'best_fitness': self.best_fitness,
            'n_trials': len(self.results),
            'all_results': self.results
        }

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\nResults saved to {filepath}")

    def analyze_sensitivity(self):
        """Analyze sensitivity of each weight."""
        if not self.results:
            print("No results to analyze!")
            return

        print("\n" + "=" * 60)
        print("WEIGHT SENSITIVITY ANALYSIS")
        print("=" * 60)

        # Calculate correlation between each weight and fitness
        weights_array = np.array([
            [r['weights']['total_return'],
             r['weights']['sharpe_ratio'],
             r['weights']['max_drawdown'],
             r['weights']['win_rate']]
            for r in self.results
        ])

        fitness_array = np.array([r['best_fitness'] for r in self.results])

        weight_names = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']

        print("\nCorrelation with fitness:")
        for i, name in enumerate(weight_names):
            corr = np.corrcoef(weights_array[:, i], fitness_array)[0, 1]
            print(f"  {name:20s}: {corr:+.3f}")

        # Best and worst results
        sorted_results = sorted(self.results, key=lambda x: x['best_fitness'], reverse=True)

        print("\n" + "-" * 60)
        print("TOP 3 WEIGHT COMBINATIONS:")
        for i, r in enumerate(sorted_results[:3]):
            print(f"\n#{i+1}: Fitness = {r['best_fitness']:.4f}")
            self._print_weights(r['weights'])

        print("\n" + "-" * 60)
        print("WORST 3 WEIGHT COMBINATIONS:")
        for i, r in enumerate(sorted_results[-3:]):
            print(f"\n#{i+1}: Fitness = {r['best_fitness']:.4f}")
            self._print_weights(r['weights'])


def optimize_fitness_weights(
    n_trials: int = 20,
    generations: int = 20,
    method: str = 'random'
):
    """
    Quick fitness weight optimization.

    Args:
        n_trials: Number of weight combinations to test
        generations: Generations per trial
        method: 'random', 'grid', or 'simplex'

    Returns:
        Best weights
    """
    optimizer = FitnessWeightOptimizer()

    best_weights = optimizer.optimize(
        n_trials=n_trials,
        generations=generations,
        method=method
    )

    optimizer.print_best_weights()
    optimizer.analyze_sensitivity()
    optimizer.save_results()

    return best_weights


# Example usage
if __name__ == "__main__":
    print("Fitness Weight Optimization")
    print("=" * 60)

    # Quick test with small parameters
    optimizer = FitnessWeightOptimizer(
        start_date="2019-01-01",
        end_date="2019-12-31"
    )

    # Run optimization (random sampling)
    print("\nTesting 15 random weight combinations...")
    print("Each trial: 10 generations")

    best_weights = optimizer.optimize(
        n_trials=15,
        generations=10,
        method='random'
    )

    # Results
    optimizer.print_best_weights()
    optimizer.analyze_sensitivity()
    optimizer.save_results()

    print("\n" + "=" * 60)
    print("Optimization complete!")
    print("=" * 60)
