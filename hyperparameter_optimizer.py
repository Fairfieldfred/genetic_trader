"""
Hyperparameter optimization for genetic algorithm.
Optimizes both GA parameters and fitness weights to find best configuration.
"""

import random
import numpy as np
import pandas as pd
from itertools import product
from typing import Dict, List, Tuple, Any
import json
from pathlib import Path
from datetime import datetime
import config
from evolve import GeneticAlgorithm


class HyperparameterOptimizer:
    """
    Optimizes genetic algorithm hyperparameters and fitness weights.
    Uses grid search or random search to find optimal configuration.
    """

    def __init__(
        self,
        symbol: str = None,
        start_date: str = None,
        end_date: str = None,
        search_type: str = 'grid',
        n_trials: int = None
    ):
        """
        Initialize hyperparameter optimizer.

        Args:
            symbol: Stock symbol (or None for portfolio mode)
            start_date: Training start date
            end_date: Training end date
            search_type: 'grid' or 'random'
            n_trials: Number of random trials (for random search)
        """
        self.symbol = symbol or config.TEST_SYMBOL
        self.start_date = start_date or config.TRAIN_START_DATE
        self.end_date = end_date or config.TRAIN_END_DATE
        self.search_type = search_type
        self.n_trials = n_trials or 20

        self.results = []
        self.best_config = None
        self.best_fitness = float('-inf')

    def define_search_space(self) -> Dict[str, List]:
        """
        Define hyperparameter search space.

        Returns:
            Dictionary of hyperparameters and their possible values
        """
        search_space = {
            # Genetic algorithm parameters
            'POPULATION_SIZE': [10, 15, 20, 30],
            'MUTATION_RATE': [0.05, 0.10, 0.15, 0.20, 0.25],
            'CROSSOVER_RATE': [0.6, 0.7, 0.8, 0.9],
            'ELITISM_COUNT': [1, 2, 3, 4],
            'TOURNAMENT_SIZE': [2, 3, 4, 5],

            # Fitness weights (must sum to 1.0)
            'FITNESS_WEIGHT_RETURN': [0.2, 0.3, 0.4, 0.5],
            'FITNESS_WEIGHT_SHARPE': [0.1, 0.2, 0.3, 0.4],
            'FITNESS_WEIGHT_DRAWDOWN': [0.1, 0.2, 0.3],
            'FITNESS_WEIGHT_WINRATE': [0.05, 0.10, 0.15, 0.20],
        }

        return search_space

    def normalize_fitness_weights(
        self,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Normalize fitness weights to sum to 1.0.

        Args:
            weights: Dictionary of weight values

        Returns:
            Normalized weights
        """
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}

    def grid_search(self, generations: int = 20) -> Dict[str, Any]:
        """
        Perform grid search over hyperparameter space.

        Args:
            generations: Number of generations per trial

        Returns:
            Best configuration found
        """
        search_space = self.define_search_space()

        # Create grid of all combinations
        keys = list(search_space.keys())
        values = list(search_space.values())
        combinations = list(product(*values))

        print(f"\n{'=' * 60}")
        print(f"GRID SEARCH: {len(combinations)} configurations")
        print(f"{'=' * 60}")

        for i, combination in enumerate(combinations):
            config_dict = dict(zip(keys, combination))

            # Normalize fitness weights
            weight_keys = [k for k in config_dict if k.startswith('FITNESS_WEIGHT_')]
            weights = {k: config_dict[k] for k in weight_keys}
            normalized_weights = self.normalize_fitness_weights(weights)

            # Update config dict
            for k, v in normalized_weights.items():
                config_dict[k] = v

            print(f"\n[{i + 1}/{len(combinations)}] Testing configuration:")
            self._print_config(config_dict)

            # Run evolution with this configuration
            fitness = self._evaluate_config(config_dict, generations)

            self.results.append({
                'config': config_dict,
                'best_fitness': fitness,
                'trial': i + 1
            })

            if fitness > self.best_fitness:
                self.best_fitness = fitness
                self.best_config = config_dict
                print(f"  🎯 New best! Fitness: {fitness:.4f}")

        return self.best_config

    def random_search(self, generations: int = 20) -> Dict[str, Any]:
        """
        Perform random search over hyperparameter space.

        Args:
            generations: Number of generations per trial

        Returns:
            Best configuration found
        """
        search_space = self.define_search_space()

        print(f"\n{'=' * 60}")
        print(f"RANDOM SEARCH: {self.n_trials} trials")
        print(f"{'=' * 60}")

        for i in range(self.n_trials):
            # Random sample from search space
            config_dict = {
                k: random.choice(v) for k, v in search_space.items()
            }

            # Normalize fitness weights
            weight_keys = [k for k in config_dict if k.startswith('FITNESS_WEIGHT_')]
            weights = {k: config_dict[k] for k in weight_keys}
            normalized_weights = self.normalize_fitness_weights(weights)

            for k, v in normalized_weights.items():
                config_dict[k] = v

            print(f"\n[{i + 1}/{self.n_trials}] Testing configuration:")
            self._print_config(config_dict)

            # Run evolution
            fitness = self._evaluate_config(config_dict, generations)

            self.results.append({
                'config': config_dict,
                'best_fitness': fitness,
                'trial': i + 1
            })

            if fitness > self.best_fitness:
                self.best_fitness = fitness
                self.best_config = config_dict
                print(f"  🎯 New best! Fitness: {fitness:.4f}")

        return self.best_config

    def _evaluate_config(
        self,
        config_dict: Dict[str, Any],
        generations: int
    ) -> float:
        """
        Evaluate a hyperparameter configuration.

        Args:
            config_dict: Configuration to test
            generations: Number of generations to run

        Returns:
            Best fitness achieved
        """
        # Temporarily override config
        original_values = {}

        # GA parameters
        for param in ['POPULATION_SIZE', 'MUTATION_RATE', 'CROSSOVER_RATE',
                      'ELITISM_COUNT', 'TOURNAMENT_SIZE']:
            if param in config_dict:
                original_values[param] = getattr(config, param)
                setattr(config, param, config_dict[param])

        # Fitness weights
        original_weights = config.FITNESS_WEIGHTS.copy()
        config.FITNESS_WEIGHTS = {
            'total_return': config_dict.get('FITNESS_WEIGHT_RETURN', 0.4),
            'sharpe_ratio': config_dict.get('FITNESS_WEIGHT_SHARPE', 0.3),
            'max_drawdown': config_dict.get('FITNESS_WEIGHT_DRAWDOWN', 0.2),
            'win_rate': config_dict.get('FITNESS_WEIGHT_WINRATE', 0.1),
        }

        try:
            # Run evolution
            ga = GeneticAlgorithm(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                population_size=config_dict['POPULATION_SIZE'],
                num_generations=generations
            )

            ga.evolve()

            # Get best fitness
            best_fitness = ga.population.best_trader.fitness

            return best_fitness

        except Exception as e:
            print(f"  ✗ Configuration failed: {e}")
            return float('-inf')

        finally:
            # Restore original config
            for param, value in original_values.items():
                setattr(config, param, value)
            config.FITNESS_WEIGHTS = original_weights

    def _print_config(self, config_dict: Dict[str, Any]):
        """Print configuration in readable format."""
        print("  GA Parameters:")
        print(f"    Population: {config_dict.get('POPULATION_SIZE', 'N/A')}")
        print(f"    Mutation Rate: {config_dict.get('MUTATION_RATE', 'N/A')}")
        print(f"    Crossover Rate: {config_dict.get('CROSSOVER_RATE', 'N/A')}")
        print(f"    Elitism: {config_dict.get('ELITISM_COUNT', 'N/A')}")
        print(f"    Tournament: {config_dict.get('TOURNAMENT_SIZE', 'N/A')}")

        print("  Fitness Weights:")
        print(f"    Return: {config_dict.get('FITNESS_WEIGHT_RETURN', 'N/A'):.2f}")
        print(f"    Sharpe: {config_dict.get('FITNESS_WEIGHT_SHARPE', 'N/A'):.2f}")
        print(f"    Drawdown: {config_dict.get('FITNESS_WEIGHT_DRAWDOWN', 'N/A'):.2f}")
        print(f"    Win Rate: {config_dict.get('FITNESS_WEIGHT_WINRATE', 'N/A'):.2f}")

    def optimize(self, generations: int = 20) -> Dict[str, Any]:
        """
        Run optimization using selected search method.

        Args:
            generations: Number of generations per trial

        Returns:
            Best configuration found
        """
        if self.search_type == 'grid':
            return self.grid_search(generations)
        elif self.search_type == 'random':
            return self.random_search(generations)
        else:
            raise ValueError(f"Unknown search type: {self.search_type}")

    def save_results(self, filepath: str = None):
        """
        Save optimization results to file.

        Args:
            filepath: Path to save results (auto-generated if None)
        """
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"results/hyperparameter_optimization_{timestamp}.json"

        Path(filepath).parent.mkdir(exist_ok=True, parents=True)

        output = {
            'best_config': self.best_config,
            'best_fitness': self.best_fitness,
            'search_type': self.search_type,
            'n_trials': len(self.results),
            'all_results': self.results
        }

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\nResults saved to {filepath}")

    def print_best_config(self):
        """Print the best configuration found."""
        if self.best_config is None:
            print("No optimization run yet!")
            return

        print("\n" + "=" * 60)
        print("BEST CONFIGURATION")
        print("=" * 60)
        print(f"Best Fitness: {self.best_fitness:.4f}")
        print()
        self._print_config(self.best_config)

        # Generate config.py code
        print("\n" + "=" * 60)
        print("COPY TO config.py:")
        print("=" * 60)
        print()
        print("# Optimized genetic algorithm parameters")
        print(f"POPULATION_SIZE = {self.best_config['POPULATION_SIZE']}")
        print(f"MUTATION_RATE = {self.best_config['MUTATION_RATE']}")
        print(f"CROSSOVER_RATE = {self.best_config['CROSSOVER_RATE']}")
        print(f"ELITISM_COUNT = {self.best_config['ELITISM_COUNT']}")
        print(f"TOURNAMENT_SIZE = {self.best_config['TOURNAMENT_SIZE']}")
        print()
        print("# Optimized fitness weights")
        print("FITNESS_WEIGHTS = {")
        print(f"    'total_return': {self.best_config['FITNESS_WEIGHT_RETURN']:.2f},")
        print(f"    'sharpe_ratio': {self.best_config['FITNESS_WEIGHT_SHARPE']:.2f},")
        print(f"    'max_drawdown': {self.best_config['FITNESS_WEIGHT_DRAWDOWN']:.2f},")
        print(f"    'win_rate': {self.best_config['FITNESS_WEIGHT_WINRATE']:.2f},")
        print("}")

    def analyze_results(self) -> pd.DataFrame:
        """
        Analyze optimization results.

        Returns:
            DataFrame with results analysis
        """
        if not self.results:
            print("No results to analyze!")
            return None

        # Convert to DataFrame
        rows = []
        for r in self.results:
            row = {
                'trial': r['trial'],
                'fitness': r['best_fitness'],
                **r['config']
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        # Sort by fitness
        df = df.sort_values('fitness', ascending=False)

        print("\n" + "=" * 60)
        print("TOP 5 CONFIGURATIONS")
        print("=" * 60)
        print(df.head().to_string())

        # Parameter importance analysis
        print("\n" + "=" * 60)
        print("PARAMETER IMPORTANCE (correlation with fitness)")
        print("=" * 60)

        numeric_cols = [c for c in df.columns if c not in ['trial']]
        correlations = df[numeric_cols].corr()['fitness'].drop('fitness')
        correlations = correlations.abs().sort_values(ascending=False)

        for param, corr in correlations.items():
            print(f"  {param:30s}: {corr:.3f}")

        return df


# Convenience function
def optimize_hyperparameters(
    search_type: str = 'random',
    n_trials: int = 20,
    generations: int = 20
):
    """
    Quick hyperparameter optimization.

    Args:
        search_type: 'grid' or 'random'
        n_trials: Number of trials (random search)
        generations: Generations per trial

    Returns:
        Best configuration
    """
    optimizer = HyperparameterOptimizer(
        search_type=search_type,
        n_trials=n_trials
    )

    best_config = optimizer.optimize(generations=generations)
    optimizer.print_best_config()
    optimizer.save_results()
    optimizer.analyze_results()

    return best_config


# Example usage
if __name__ == "__main__":
    print("Hyperparameter Optimization for Genetic Trading Algorithm")
    print("=" * 60)

    # Random search (faster, good for exploration)
    print("\nRunning random search with 10 trials...")
    print("Each trial: 10 generations on 2019 data")

    optimizer = HyperparameterOptimizer(
        start_date="2019-01-01",
        end_date="2019-12-31",
        search_type='random',
        n_trials=10
    )

    # Run optimization
    best_config = optimizer.optimize(generations=10)

    # Results
    optimizer.print_best_config()
    optimizer.save_results()
    optimizer.analyze_results()

    print("\n" + "=" * 60)
    print("Optimization complete!")
    print("=" * 60)
