import 'dart:math';
import '../models/chromosome.dart';
import 'gene_definitions.dart';
import 'gene_groups.dart';

/// Genetic algorithm operators.
class GeneticOperators {
  GeneticOperators._();

  /// Initialize a random population with expression weights.
  ///
  /// Each optional group has a 50% chance of starting silenced
  /// or active. Core genes are always active. Individual gene
  /// expressions are uniform random [0.3, 1.0].
  static List<Chromosome> initPopulation(
    int size,
    Map<String, GeneRange> genes, {
    int? seed,
  }) {
    final rng = Random(seed);
    return List.generate(size, (_) {
      final geneMap = <String, double>{};
      for (final entry in genes.entries) {
        final range = entry.value;
        final value =
            range.min + rng.nextDouble() * (range.max - range.min);
        geneMap[entry.key] = range.clamp(value);
      }

      // Build expression map.
      final expr = <String, double>{};

      // Determine which optional groups are present in the
      // gene set (disabled groups won't have genes at all).
      final presentGroups = <String>{};
      for (final gene in geneMap.keys) {
        final group = GeneGroups.geneToGroup[gene];
        if (group != null) presentGroups.add(group);
      }
      final presentOptional = presentGroups
          .where((g) => g != GeneGroups.core)
          .toList();

      // Decide which present optional groups are active (50/50).
      final activeGroups = <String>{GeneGroups.core};
      for (final group in presentOptional) {
        if (rng.nextBool()) {
          activeGroups.add(group);
        }
      }

      // Ensure at least core + min(2, available) optional groups.
      final minOptional =
          presentOptional.length < 2 ? presentOptional.length : 2;
      while (activeGroups.length < 1 + minOptional &&
          presentOptional.isNotEmpty) {
        final pick = presentOptional[
            rng.nextInt(presentOptional.length)];
        activeGroups.add(pick);
      }

      for (final gene in geneMap.keys) {
        final group = GeneGroups.geneToGroup[gene];
        if (group == GeneGroups.core) {
          expr[gene] = 1.0;
        } else if (group != null && activeGroups.contains(group)) {
          // Active group: individual expression [0.3, 1.0].
          expr[gene] = 0.3 + rng.nextDouble() * 0.7;
        } else {
          // Silenced group: expression [0.0, 0.1].
          expr[gene] = rng.nextDouble() * 0.1;
        }
      }

      return Chromosome(genes: geneMap, expression: expr);
    });
  }

  /// Tournament selection: pick k random individuals, return the
  /// fittest.
  static Chromosome tournamentSelect(
    List<Chromosome> population,
    int k, {
    Random? rng,
  }) {
    rng ??= Random();
    Chromosome best = population[rng.nextInt(population.length)];
    for (var i = 1; i < k; i++) {
      final candidate = population[rng.nextInt(population.length)];
      if (candidate.fitness > best.fitness) {
        best = candidate;
      }
    }
    return best;
  }

  /// Uniform crossover: for each gene, randomly pick from parent a
  /// or b. Expression weights are crossed over independently.
  static (Chromosome, Chromosome) uniformCrossover(
    Chromosome a,
    Chromosome b, {
    Random? rng,
  }) {
    rng ??= Random();
    final child1Genes = <String, double>{};
    final child2Genes = <String, double>{};
    final child1Expr = <String, double>{};
    final child2Expr = <String, double>{};

    for (final gene in a.genes.keys) {
      if (rng.nextBool()) {
        child1Genes[gene] = a.genes[gene]!;
        child2Genes[gene] = b.genes[gene] ?? a.genes[gene]!;
      } else {
        child1Genes[gene] = b.genes[gene] ?? a.genes[gene]!;
        child2Genes[gene] = a.genes[gene]!;
      }

      // Crossover expression independently.
      if (rng.nextBool()) {
        child1Expr[gene] = a.expression[gene] ?? 1.0;
        child2Expr[gene] = b.expression[gene] ?? 1.0;
      } else {
        child1Expr[gene] = b.expression[gene] ?? 1.0;
        child2Expr[gene] = a.expression[gene] ?? 1.0;
      }
    }

    return (
      Chromosome(
        genes: child1Genes,
        expression: child1Expr,
      ),
      Chromosome(
        genes: child2Genes,
        expression: child2Expr,
      ),
    );
  }

  /// Gaussian mutation: perturb each gene with probability [rate].
  ///
  /// Perturbation is Gaussian with stddev = 10% of gene range.
  static Chromosome gaussianMutate(
    Chromosome c,
    Map<String, GeneRange> genes,
    double rate, {
    int? seed,
  }) {
    final rng = Random(seed);
    final mutated = Map<String, double>.from(c.genes);

    for (final entry in genes.entries) {
      if (rng.nextDouble() < rate) {
        final range = entry.value;
        final span = range.max - range.min;
        // Box-Muller transform for Gaussian random.
        final u1 = rng.nextDouble();
        final u2 = rng.nextDouble();
        final z = sqrt(-2.0 * log(u1)) * cos(2.0 * pi * u2);
        final perturbation = z * span * 0.1;
        mutated[entry.key] = range.clamp(
          (mutated[entry.key] ?? range.min) + perturbation,
        );
      }
    }

    return Chromosome(
      genes: mutated,
      fitness: c.fitness,
      expression: Map.of(c.expression),
    );
  }

  /// Expression mutation: evolves expression weights alongside
  /// gene values.
  ///
  /// Three mutation types:
  /// - Type A (60%): Perturb individual gene expression by
  ///   Gaussian(0, 0.2), clamped [0, 1].
  /// - Type B (25%): Silence or activate an entire group.
  ///   Cannot silence core group.
  /// - Type C (15%): Boost a random gene to 1.0 ("spotlight").
  static Chromosome expressionMutate(
    Chromosome c,
    double rate, {
    int? seed,
  }) {
    final rng = Random(seed);
    final expr = Map<String, double>.from(c.expression);

    // Choose mutation type.
    final typeRoll = rng.nextDouble();

    if (typeRoll < 0.60) {
      // Type A: per-gene Gaussian perturbation.
      for (final gene in c.genes.keys) {
        if (rng.nextDouble() < rate) {
          final group = GeneGroups.geneToGroup[gene];
          if (group == GeneGroups.core) continue; // protect core
          final u1 = rng.nextDouble();
          final u2 = rng.nextDouble();
          final z = sqrt(-2.0 * log(u1)) * cos(2.0 * pi * u2);
          final current = expr[gene] ?? 1.0;
          expr[gene] = (current + z * 0.2).clamp(0.0, 1.0);
        }
      }
    } else if (typeRoll < 0.85) {
      // Type B: group-level silence/activate.
      if (GeneGroups.optionalGroups.isNotEmpty) {
        final groupName = GeneGroups.optionalGroups[
            rng.nextInt(GeneGroups.optionalGroups.length)];
        final groupGenes = GeneGroups.groups[groupName] ?? [];

        // Determine current group state (average expression).
        var sum = 0.0;
        var count = 0;
        for (final g in groupGenes) {
          if (c.genes.containsKey(g)) {
            sum += expr[g] ?? 1.0;
            count++;
          }
        }
        final avgExpr = count > 0 ? sum / count : 1.0;

        if (avgExpr > 0.5) {
          // Silence: set to [0.0, 0.1].
          for (final g in groupGenes) {
            if (c.genes.containsKey(g)) {
              expr[g] = rng.nextDouble() * 0.1;
            }
          }
        } else {
          // Activate: set to [0.7, 1.0].
          for (final g in groupGenes) {
            if (c.genes.containsKey(g)) {
              expr[g] = 0.7 + rng.nextDouble() * 0.3;
            }
          }
        }
      }
    } else {
      // Type C: spotlight — boost a random gene to 1.0.
      final geneKeys = c.genes.keys.toList();
      if (geneKeys.isNotEmpty) {
        final pick = geneKeys[rng.nextInt(geneKeys.length)];
        expr[pick] = 1.0;
      }
    }

    return Chromosome(
      genes: Map.of(c.genes),
      fitness: c.fitness,
      expression: expr,
    );
  }
}
