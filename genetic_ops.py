"""
Genetic operations: crossover and mutation for evolving trading strategies.
"""

import random
from typing import List, Tuple, Any
import config
from genetic_trader import GeneticTrader


def uniform_crossover(
    parent1: GeneticTrader,
    parent2: GeneticTrader
) -> Tuple[GeneticTrader, GeneticTrader]:
    """
    Perform uniform crossover between two parents.
    Each gene has a 50% chance of coming from either parent.

    Args:
        parent1: First parent trader
        parent2: Second parent trader

    Returns:
        Tuple of two child traders
    """
    child1_chromosome = []
    child2_chromosome = []

    for i in range(len(parent1.chromosome)):
        if random.random() < 0.5:
            # Child1 gets gene from parent1, child2 from parent2
            child1_chromosome.append(parent1.chromosome[i])
            child2_chromosome.append(parent2.chromosome[i])
        else:
            # Child1 gets gene from parent2, child2 from parent1
            child1_chromosome.append(parent2.chromosome[i])
            child2_chromosome.append(parent1.chromosome[i])

    child1 = GeneticTrader(child1_chromosome)
    child2 = GeneticTrader(child2_chromosome)

    return child1, child2


def single_point_crossover(
    parent1: GeneticTrader,
    parent2: GeneticTrader
) -> Tuple[GeneticTrader, GeneticTrader]:
    """
    Perform single-point crossover between two parents.
    Swaps genes at a random crossover point.

    Args:
        parent1: First parent trader
        parent2: Second parent trader

    Returns:
        Tuple of two child traders
    """
    crossover_point = random.randint(1, len(parent1.chromosome) - 1)

    child1_chromosome = (
        parent1.chromosome[:crossover_point] +
        parent2.chromosome[crossover_point:]
    )
    child2_chromosome = (
        parent2.chromosome[:crossover_point] +
        parent1.chromosome[crossover_point:]
    )

    child1 = GeneticTrader(child1_chromosome)
    child2 = GeneticTrader(child2_chromosome)

    return child1, child2


def crossover(
    parent1: GeneticTrader,
    parent2: GeneticTrader,
    method: str = 'uniform'
) -> Tuple[GeneticTrader, GeneticTrader]:
    """
    Perform crossover between two parents using specified method.

    Args:
        parent1: First parent trader
        parent2: Second parent trader
        method: Crossover method ('uniform' or 'single_point')

    Returns:
        Tuple of two child traders
    """
    if method == 'uniform':
        return uniform_crossover(parent1, parent2)
    elif method == 'single_point':
        return single_point_crossover(parent1, parent2)
    else:
        raise ValueError(f"Unknown crossover method: {method}")


def mutate(trader: GeneticTrader, mutation_rate: float = None) -> GeneticTrader:
    """
    Mutate a trader's genes with given probability.
    Each gene has a chance of being randomly changed within its bounds.

    Args:
        trader: Trader to mutate
        mutation_rate: Probability of mutating each gene (uses config default if None)

    Returns:
        New mutated trader
    """
    if mutation_rate is None:
        mutation_rate = config.MUTATION_RATE

    mutated_chromosome = trader.chromosome.copy()

    for i, gene_name in enumerate(config.GENE_ORDER):
        if random.random() < mutation_rate:
            # Mutate this gene
            min_val, max_val, dtype = config.GENE_DEFINITIONS[gene_name]

            if dtype == int:
                mutated_chromosome[i] = random.randint(min_val, max_val)
            elif dtype == float:
                mutated_chromosome[i] = random.uniform(min_val, max_val)

    return GeneticTrader(mutated_chromosome)


def mutate_gaussian(
    trader: GeneticTrader,
    mutation_rate: float = None,
    sigma: float = 0.1
) -> GeneticTrader:
    """
    Mutate a trader's genes using Gaussian perturbation.
    More subtle than random replacement - adds noise to existing values.

    Args:
        trader: Trader to mutate
        mutation_rate: Probability of mutating each gene
        sigma: Standard deviation for Gaussian noise (as fraction of range)

    Returns:
        New mutated trader
    """
    if mutation_rate is None:
        mutation_rate = config.MUTATION_RATE

    mutated_chromosome = trader.chromosome.copy()

    for i, gene_name in enumerate(config.GENE_ORDER):
        if random.random() < mutation_rate:
            min_val, max_val, dtype = config.GENE_DEFINITIONS[gene_name]
            current_value = mutated_chromosome[i]

            # Calculate perturbation based on gene range
            gene_range = max_val - min_val
            perturbation = random.gauss(0, sigma * gene_range)

            # Apply perturbation and clamp to bounds
            new_value = current_value + perturbation
            new_value = max(min_val, min(max_val, new_value))

            if dtype == int:
                new_value = int(round(new_value))

            mutated_chromosome[i] = new_value

    return GeneticTrader(mutated_chromosome)


def tournament_selection(
    population: List[GeneticTrader],
    tournament_size: int = None
) -> GeneticTrader:
    """
    Select a parent using tournament selection.
    Randomly picks tournament_size individuals and returns the best one.

    Args:
        population: List of traders to select from
        tournament_size: Number of individuals in tournament

    Returns:
        Selected trader
    """
    if tournament_size is None:
        tournament_size = config.TOURNAMENT_SIZE

    tournament = random.sample(population, min(tournament_size, len(population)))
    return max(tournament, key=lambda t: t.fitness if t.fitness else float('-inf'))


def roulette_selection(population: List[GeneticTrader]) -> GeneticTrader:
    """
    Select a parent using roulette wheel selection.
    Probability of selection is proportional to fitness.

    Args:
        population: List of traders to select from

    Returns:
        Selected trader
    """
    # Ensure all fitness values are positive
    min_fitness = min(t.fitness for t in population if t.fitness is not None)
    if min_fitness < 0:
        offset = abs(min_fitness) + 1
        adjusted_fitness = [
            (t.fitness + offset if t.fitness else 0) for t in population
        ]
    else:
        adjusted_fitness = [t.fitness if t.fitness else 0 for t in population]

    total_fitness = sum(adjusted_fitness)

    if total_fitness == 0:
        # All traders have zero fitness, select randomly
        return random.choice(population)

    # Spin the wheel
    spin = random.uniform(0, total_fitness)
    cumulative = 0

    for trader, fitness in zip(population, adjusted_fitness):
        cumulative += fitness
        if cumulative >= spin:
            return trader

    # Fallback (shouldn't reach here)
    return population[-1]


# Testing and examples
if __name__ == "__main__":
    print("Testing Genetic Operations\n")
    print("=" * 60)

    # Create two parent traders
    parent1 = GeneticTrader([14, 70, 30, 2.5, 5.0, 10.0])
    parent2 = GeneticTrader([10, 80, 20, 5.0, 10.0, 20.0])

    print("Parent 1:")
    print(parent1.get_genes())
    print("\nParent 2:")
    print(parent2.get_genes())

    # Test uniform crossover
    print("\n" + "=" * 60)
    print("Uniform Crossover:")
    child1, child2 = uniform_crossover(parent1, parent2)
    print("\nChild 1:")
    print(child1.get_genes())
    print("\nChild 2:")
    print(child2.get_genes())

    # Test single-point crossover
    print("\n" + "=" * 60)
    print("Single-Point Crossover:")
    child1, child2 = single_point_crossover(parent1, parent2)
    print("\nChild 1:")
    print(child1.get_genes())
    print("\nChild 2:")
    print(child2.get_genes())

    # Test mutation
    print("\n" + "=" * 60)
    print("Mutation (high rate for demonstration):")
    trader = GeneticTrader([14, 70, 30, 2.5, 5.0, 10.0])
    print("\nOriginal:")
    print(trader.get_genes())

    mutated = mutate(trader, mutation_rate=0.5)
    print("\nMutated (random replacement):")
    print(mutated.get_genes())

    mutated_gaussian = mutate_gaussian(trader, mutation_rate=0.5, sigma=0.2)
    print("\nMutated (Gaussian):")
    print(mutated_gaussian.get_genes())

    # Test selection
    print("\n" + "=" * 60)
    print("Selection Methods:")

    # Create population with varying fitness
    population = []
    for i in range(5):
        trader = GeneticTrader()
        trader.set_fitness(random.uniform(0, 100))
        population.append(trader)

    print("\nPopulation fitness scores:")
    for i, trader in enumerate(population):
        print(f"  Trader {i}: {trader.fitness:.2f}")

    print("\nTournament selection (5 samples):")
    for _ in range(5):
        selected = tournament_selection(population)
        idx = population.index(selected)
        print(f"  Selected Trader {idx} (fitness: {selected.fitness:.2f})")

    print("\nRoulette selection (5 samples):")
    for _ in range(5):
        selected = roulette_selection(population)
        idx = population.index(selected)
        print(f"  Selected Trader {idx} (fitness: {selected.fitness:.2f})")
