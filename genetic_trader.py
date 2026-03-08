"""
GeneticTrader class - represents an individual trading bot with a chromosome.
The chromosome encodes trading strategy parameters.
"""

import random
from typing import List, Dict, Any
import config


class GeneticTrader:
    """
    Represents an individual trading bot with genetic encoding.
    Each trader has a chromosome (list of genes) that defines its behavior.
    """

    def __init__(self, chromosome: List[Any] = None):
        """
        Initialize a genetic trader.

        Args:
            chromosome: List of gene values. If None, creates random chromosome.
        """
        if chromosome is None:
            self.chromosome = self._create_random_chromosome()
        else:
            self.chromosome = chromosome
            self._validate_chromosome()

        self.fitness = None
        self.generation = 0

    def _create_random_chromosome(self) -> List[Any]:
        """
        Create a random chromosome within gene bounds.

        Returns:
            List of random gene values
        """
        chromosome = []
        for gene_name in config.GENE_ORDER:
            min_val, max_val, dtype = config.GENE_DEFINITIONS[gene_name]

            if dtype == int:
                value = random.randint(min_val, max_val)
            elif dtype == float:
                value = random.uniform(min_val, max_val)
            else:
                raise ValueError(f"Unsupported gene type: {dtype}")

            chromosome.append(value)

        return chromosome

    def _validate_chromosome(self):
        """Validate that chromosome values are within defined bounds."""
        if len(self.chromosome) != len(config.GENE_ORDER):
            raise ValueError(
                f"Chromosome length {len(self.chromosome)} doesn't match "
                f"expected length {len(config.GENE_ORDER)}"
            )

        for i, gene_name in enumerate(config.GENE_ORDER):
            min_val, max_val, dtype = config.GENE_DEFINITIONS[gene_name]
            value = self.chromosome[i]

            # Type check
            if dtype == int and not isinstance(value, int):
                self.chromosome[i] = int(value)
                value = self.chromosome[i]
            elif dtype == float and not isinstance(value, (int, float)):
                raise ValueError(
                    f"Gene {gene_name} has invalid type: {type(value)}"
                )

            # Bounds check
            if not min_val <= value <= max_val:
                raise ValueError(
                    f"Gene {gene_name} value {value} outside bounds "
                    f"[{min_val}, {max_val}]"
                )

    def get_genes(self) -> Dict[str, Any]:
        """
        Get genes as a dictionary for easy access.

        Returns:
            Dictionary mapping gene names to values
        """
        return {
            gene_name: self.chromosome[i]
            for i, gene_name in enumerate(config.GENE_ORDER)
        }

    def get_gene(self, gene_name: str) -> Any:
        """
        Get value of a specific gene.

        Args:
            gene_name: Name of the gene

        Returns:
            Gene value
        """
        if gene_name not in config.GENE_ORDER:
            raise ValueError(f"Unknown gene: {gene_name}")

        index = config.GENE_ORDER.index(gene_name)
        return self.chromosome[index]

    @classmethod
    def from_dict(cls, data: dict) -> 'GeneticTrader':
        """
        Reconstruct a trader from saved dictionary data.

        Args:
            data: Dictionary with 'chromosome' and optionally
                  'fitness' and 'generation' keys

        Returns:
            Reconstructed GeneticTrader instance
        """
        trader = cls(chromosome=data['chromosome'])
        trader.fitness = data.get('fitness')
        trader.generation = data.get('generation', 0)
        return trader

    def set_fitness(self, fitness: float):
        """Set the fitness score for this trader."""
        self.fitness = fitness

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert trader to dictionary for logging/serialization.

        Returns:
            Dictionary with trader information
        """
        genes_dict = self.get_genes()
        genes_dict['fitness'] = self.fitness
        genes_dict['generation'] = self.generation
        return genes_dict

    def __repr__(self) -> str:
        """String representation of the trader."""
        genes = self.get_genes()
        fitness_str = f"{self.fitness:.4f}" if self.fitness else "None"
        return (
            f"GeneticTrader(gen={self.generation}, fitness={fitness_str}, "
            f"genes={genes})"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        genes = self.get_genes()
        fitness_str = f"{self.fitness:.4f}" if self.fitness else "Not evaluated"
        lines = [
            f"Genetic Trader - Generation {self.generation}",
            f"Fitness: {fitness_str}",
            "Genes:",
        ]
        for name, value in genes.items():
            if isinstance(value, float):
                lines.append(f"  {name}: {value:.2f}")
            else:
                lines.append(f"  {name}: {value}")
        return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    print("Creating random genetic traders:\n")

    for i in range(3):
        trader = GeneticTrader()
        print(trader)
        print()

    print("\nCreating trader with specific chromosome:")
    chromosome = [14, 70, 30, 2.5, 5.0, 10.0]
    trader = GeneticTrader(chromosome)
    print(trader)

    print("\nAccessing specific genes:")
    print(f"RSI Period: {trader.get_gene('rsi_period')}")
    print(f"Position Size: {trader.get_gene('position_size_pct')}%")

    print("\nTrader as dictionary:")
    print(trader.to_dict())
