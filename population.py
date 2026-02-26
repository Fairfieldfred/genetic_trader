"""
Population manager for genetic algorithm.
Handles population initialization, statistics, and generational transitions.
"""

import random
from typing import List, Dict, Any
import config
from genetic_trader import GeneticTrader
from genetic_ops import crossover, mutate, tournament_selection


class Population:
    """Manages a population of genetic traders across generations."""

    def __init__(self, size: int = None):
        """
        Initialize a population.

        Args:
            size: Population size (uses config default if None)
        """
        self.size = size or config.POPULATION_SIZE
        self.generation = 0
        self.traders: List[GeneticTrader] = []
        self.best_trader: GeneticTrader = None
        self.history = []  # Track best fitness per generation

        # Initialize random population
        self._initialize_population()

    def _initialize_population(self):
        """Create initial random population."""
        self.traders = [GeneticTrader() for _ in range(self.size)]
        for trader in self.traders:
            trader.generation = self.generation

    def get_statistics(self) -> Dict[str, Any]:
        """
        Calculate population statistics.

        Returns:
            Dictionary with population statistics
        """
        fitness_scores = [
            t.fitness for t in self.traders if t.fitness is not None
        ]

        if not fitness_scores:
            return {
                'generation': self.generation,
                'size': self.size,
                'evaluated': 0,
                'best_fitness': None,
                'avg_fitness': None,
                'worst_fitness': None,
                'std_fitness': None,
            }

        import statistics

        stats = {
            'generation': self.generation,
            'size': self.size,
            'evaluated': len(fitness_scores),
            'best_fitness': max(fitness_scores),
            'avg_fitness': statistics.mean(fitness_scores),
            'worst_fitness': min(fitness_scores),
        }

        if len(fitness_scores) > 1:
            stats['std_fitness'] = statistics.stdev(fitness_scores)
        else:
            stats['std_fitness'] = 0.0

        return stats

    def get_best_trader(self) -> GeneticTrader:
        """
        Get the best trader in current population.

        Returns:
            Trader with highest fitness
        """
        evaluated_traders = [t for t in self.traders if t.fitness is not None]
        if not evaluated_traders:
            return None
        return max(evaluated_traders, key=lambda t: t.fitness)

    def get_top_traders(self, n: int) -> List[GeneticTrader]:
        """
        Get top n traders by fitness.

        Args:
            n: Number of top traders to return

        Returns:
            List of top traders
        """
        evaluated_traders = [t for t in self.traders if t.fitness is not None]
        return sorted(evaluated_traders, key=lambda t: t.fitness, reverse=True)[:n]

    def evolve_generation(
        self,
        elitism_count: int = None,
        crossover_rate: float = None,
        mutation_rate: float = None
    ):
        """
        Evolve to next generation using genetic operations.

        Args:
            elitism_count: Number of top performers to preserve
            crossover_rate: Probability of crossover
            mutation_rate: Probability of mutation
        """
        if elitism_count is None:
            elitism_count = config.ELITISM_COUNT
        if crossover_rate is None:
            crossover_rate = config.CROSSOVER_RATE
        if mutation_rate is None:
            mutation_rate = config.MUTATION_RATE

        # Track best trader
        current_best = self.get_best_trader()
        if current_best:
            if self.best_trader is None or current_best.fitness > self.best_trader.fitness:
                self.best_trader = current_best
            self.history.append(current_best.fitness)

        # Create new generation
        new_generation = []

        # Elitism: preserve top performers
        if elitism_count > 0:
            elite = self.get_top_traders(elitism_count)
            new_generation.extend(elite)

        # Fill rest of population with offspring
        while len(new_generation) < self.size:
            # Select parents
            parent1 = tournament_selection(self.traders)
            parent2 = tournament_selection(self.traders)

            # Crossover
            if random.random() < crossover_rate:
                child1, child2 = crossover(parent1, parent2)
            else:
                # No crossover, children are copies of parents
                child1 = GeneticTrader(parent1.chromosome.copy())
                child2 = GeneticTrader(parent2.chromosome.copy())

            # Mutation
            child1 = mutate(child1, mutation_rate)
            if len(new_generation) + 1 < self.size:
                child2 = mutate(child2, mutation_rate)
                new_generation.extend([child1, child2])
            else:
                new_generation.append(child1)

        # Update generation
        self.generation += 1
        self.traders = new_generation[:self.size]

        # Set generation number on all traders
        for trader in self.traders:
            trader.generation = self.generation
            trader.fitness = None  # Reset fitness for new generation

    def print_statistics(self):
        """Print current population statistics."""
        stats = self.get_statistics()

        print(f"\n{'=' * 60}")
        print(f"Generation {stats['generation']}")
        print(f"{'=' * 60}")
        print(f"Population Size: {stats['size']}")
        print(f"Evaluated: {stats['evaluated']}")

        if stats['best_fitness'] is not None:
            print(f"Best Fitness: {stats['best_fitness']:.4f}")
            print(f"Average Fitness: {stats['avg_fitness']:.4f}")
            print(f"Worst Fitness: {stats['worst_fitness']:.4f}")
            print(f"Std Dev: {stats['std_fitness']:.4f}")

            if self.best_trader:
                print(f"\nBest Trader Ever (Gen {self.best_trader.generation}):")
                print(f"Fitness: {self.best_trader.fitness:.4f}")
                print(f"Genes: {self.best_trader.get_genes()}")
        else:
            print("No fitness evaluations yet")

    def save_best_trader(self, filepath: str):
        """
        Save the best trader to a file.

        Args:
            filepath: Path to save file
        """
        if self.best_trader is None:
            print("No best trader to save")
            return

        import json

        data = {
            'generation': self.best_trader.generation,
            'fitness': self.best_trader.fitness,
            'chromosome': self.best_trader.chromosome,
            'genes': self.best_trader.get_genes(),
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Best trader saved to {filepath}")

    def load_trader(self, filepath: str) -> GeneticTrader:
        """
        Load a trader from a file.

        Args:
            filepath: Path to saved trader file

        Returns:
            Loaded trader
        """
        import json

        with open(filepath, 'r') as f:
            data = json.load(f)

        trader = GeneticTrader(data['chromosome'])
        trader.fitness = data['fitness']
        trader.generation = data['generation']

        return trader


# Example usage
if __name__ == "__main__":
    print("Testing Population Manager\n")

    # Set random seed for reproducibility
    if config.RANDOM_SEED is not None:
        random.seed(config.RANDOM_SEED)

    # Create population
    pop = Population(size=10)

    print(f"Initialized population of {pop.size} traders")
    print("\nFirst 3 traders:")
    for i, trader in enumerate(pop.traders[:3]):
        print(f"\nTrader {i}:")
        print(trader.get_genes())

    # Simulate fitness evaluation
    print("\n" + "=" * 60)
    print("Simulating fitness evaluation...")
    for trader in pop.traders:
        # Random fitness for demonstration
        trader.set_fitness(random.uniform(-10, 100))

    pop.print_statistics()

    # Evolve a few generations
    print("\n" + "=" * 60)
    print("Evolving 3 generations...")

    for gen in range(3):
        pop.evolve_generation()

        # Simulate evaluation
        for trader in pop.traders:
            trader.set_fitness(random.uniform(-10, 100 + gen * 10))

        pop.print_statistics()

    # Show fitness history
    print("\n" + "=" * 60)
    print("Fitness History (best per generation):")
    for i, fitness in enumerate(pop.history):
        print(f"Generation {i}: {fitness:.4f}")
