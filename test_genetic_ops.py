"""
Test script for genetic operations.
Verifies that crossover and mutation produce valid offspring.
"""

import random
import config
from genetic_trader import GeneticTrader
from genetic_ops import (
    uniform_crossover,
    single_point_crossover,
    mutate,
    mutate_gaussian
)


def test_crossover_validity():
    """Test that crossover produces valid offspring."""
    print("=" * 60)
    print("Testing Crossover Operations")
    print("=" * 60)

    # Set seed for reproducibility
    if config.RANDOM_SEED:
        random.seed(config.RANDOM_SEED)

    # Create two parent traders
    parent1 = GeneticTrader([14, 70, 30, 2.5, 5.0, 10.0])
    parent2 = GeneticTrader([10, 80, 20, 5.0, 10.0, 20.0])

    print("\nParent 1 Genes:")
    for name, value in parent1.get_genes().items():
        print(f"  {name}: {value}")

    print("\nParent 2 Genes:")
    for name, value in parent2.get_genes().items():
        print(f"  {name}: {value}")

    # Test uniform crossover
    print("\n" + "-" * 60)
    print("Uniform Crossover Test")
    print("-" * 60)

    children_valid = []
    for i in range(5):
        child1, child2 = uniform_crossover(parent1, parent2)

        print(f"\nIteration {i + 1}:")
        print(f"Child 1: {child1.chromosome}")
        print(f"Child 2: {child2.chromosome}")

        # Verify validity
        try:
            child1._validate_chromosome()
            child2._validate_chromosome()
            children_valid.append(True)
            print("✓ Both children are VALID")
        except Exception as e:
            children_valid.append(False)
            print(f"✗ Validation FAILED: {e}")

        # Verify inheritance
        for j, gene_name in enumerate(config.GENE_ORDER):
            c1_gene = child1.chromosome[j]
            c2_gene = child2.chromosome[j]
            p1_gene = parent1.chromosome[j]
            p2_gene = parent2.chromosome[j]

            # Each child's gene should come from one of the parents
            assert c1_gene in [p1_gene, p2_gene], \
                f"Child 1 gene {gene_name} = {c1_gene} not from parents"
            assert c2_gene in [p1_gene, p2_gene], \
                f"Child 2 gene {gene_name} = {c2_gene} not from parents"

    print(f"\nUniform Crossover: {sum(children_valid)}/{len(children_valid)} iterations produced valid children")

    # Test single-point crossover
    print("\n" + "-" * 60)
    print("Single-Point Crossover Test")
    print("-" * 60)

    children_valid = []
    for i in range(5):
        child1, child2 = single_point_crossover(parent1, parent2)

        print(f"\nIteration {i + 1}:")
        print(f"Child 1: {child1.chromosome}")
        print(f"Child 2: {child2.chromosome}")

        # Verify validity
        try:
            child1._validate_chromosome()
            child2._validate_chromosome()
            children_valid.append(True)
            print("✓ Both children are VALID")
        except Exception as e:
            children_valid.append(False)
            print(f"✗ Validation FAILED: {e}")

    print(f"\nSingle-Point Crossover: {sum(children_valid)}/{len(children_valid)} iterations produced valid children")

    return all(children_valid)


def test_mutation_validity():
    """Test that mutation produces valid offspring."""
    print("\n" + "=" * 60)
    print("Testing Mutation Operations")
    print("=" * 60)

    # Set seed for reproducibility
    if config.RANDOM_SEED:
        random.seed(config.RANDOM_SEED + 1)  # Different seed

    parent = GeneticTrader([14, 70, 30, 2.5, 5.0, 10.0])

    print("\nParent Genes:")
    for name, value in parent.get_genes().items():
        print(f"  {name}: {value}")

    # Test random mutation
    print("\n" + "-" * 60)
    print("Random Mutation Test (high mutation rate)")
    print("-" * 60)

    mutations_valid = []
    for i in range(5):
        mutated = mutate(parent, mutation_rate=0.5)

        print(f"\nIteration {i + 1}:")
        print(f"Mutated: {mutated.chromosome}")

        # Verify validity
        try:
            mutated._validate_chromosome()
            mutations_valid.append(True)
            print("✓ Mutated child is VALID")

            # Show which genes changed
            changes = []
            for j, gene_name in enumerate(config.GENE_ORDER):
                if mutated.chromosome[j] != parent.chromosome[j]:
                    changes.append(gene_name)
            print(f"  Changed genes: {changes if changes else 'None'}")

        except Exception as e:
            mutations_valid.append(False)
            print(f"✗ Validation FAILED: {e}")

    print(f"\nRandom Mutation: {sum(mutations_valid)}/{len(mutations_valid)} iterations produced valid children")

    # Test Gaussian mutation
    print("\n" + "-" * 60)
    print("Gaussian Mutation Test")
    print("-" * 60)

    mutations_valid = []
    for i in range(5):
        mutated = mutate_gaussian(parent, mutation_rate=0.5, sigma=0.1)

        print(f"\nIteration {i + 1}:")
        print(f"Original: {parent.chromosome}")
        print(f"Mutated:  {mutated.chromosome}")

        # Verify validity
        try:
            mutated._validate_chromosome()
            mutations_valid.append(True)
            print("✓ Mutated child is VALID")

            # Show gene changes
            for j, gene_name in enumerate(config.GENE_ORDER):
                if mutated.chromosome[j] != parent.chromosome[j]:
                    orig = parent.chromosome[j]
                    new = mutated.chromosome[j]
                    if isinstance(orig, float):
                        print(f"  {gene_name}: {orig:.2f} → {new:.2f}")
                    else:
                        print(f"  {gene_name}: {orig} → {new}")

        except Exception as e:
            mutations_valid.append(False)
            print(f"✗ Validation FAILED: {e}")

    print(f"\nGaussian Mutation: {sum(mutations_valid)}/{len(mutations_valid)} iterations produced valid children")

    return all(mutations_valid)


def test_gene_bounds():
    """Test that all genes stay within bounds after operations."""
    print("\n" + "=" * 60)
    print("Testing Gene Bounds Preservation")
    print("=" * 60)

    # Set seed
    if config.RANDOM_SEED:
        random.seed(config.RANDOM_SEED + 2)

    # Create random parents
    parent1 = GeneticTrader()
    parent2 = GeneticTrader()

    print("\nTesting 100 crossover + mutation operations...")

    all_valid = True
    for i in range(100):
        # Crossover
        child1, child2 = uniform_crossover(parent1, parent2)

        # Mutate
        child1 = mutate(child1)
        child2 = mutate(child2)

        # Verify bounds
        for child in [child1, child2]:
            for j, gene_name in enumerate(config.GENE_ORDER):
                min_val, max_val, dtype = config.GENE_DEFINITIONS[gene_name]
                value = child.chromosome[j]

                # Check type
                if dtype == int and not isinstance(value, int):
                    print(f"✗ Gene {gene_name} has wrong type: {type(value)}")
                    all_valid = False

                # Check bounds
                if not min_val <= value <= max_val:
                    print(f"✗ Gene {gene_name} = {value} is out of bounds [{min_val}, {max_val}]")
                    all_valid = False

    if all_valid:
        print("✓ All 200 offspring stayed within gene bounds")
    else:
        print("✗ Some offspring violated gene bounds")

    return all_valid


def run_all_tests():
    """Run all genetic operations tests."""
    print("\n" + "=" * 60)
    print("GENETIC OPERATIONS TEST SUITE")
    print("=" * 60)

    results = {
        'Crossover Validity': test_crossover_validity(),
        'Mutation Validity': test_mutation_validity(),
        'Gene Bounds': test_gene_bounds(),
    }

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
