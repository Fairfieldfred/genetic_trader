import '../models/chromosome.dart';
import 'gene_groups.dart';

/// Analyzes expression patterns across a population.
class ExpressionAnalytics {
  ExpressionAnalytics._();

  /// Fraction of chromosomes where a group is "active"
  /// (avg expression > 0.5).
  static Map<String, double> groupActivityRates(
    List<Chromosome> population,
  ) {
    if (population.isEmpty) return {};

    final rates = <String, double>{};
    for (final groupName in GeneGroups.allGroups) {
      final groupGenes = GeneGroups.groups[groupName] ?? [];
      if (groupGenes.isEmpty) {
        rates[groupName] = 0.0;
        continue;
      }

      var activeCount = 0;
      for (final c in population) {
        var sum = 0.0;
        var count = 0;
        for (final gene in groupGenes) {
          if (c.genes.containsKey(gene)) {
            sum += c.expression[gene] ?? 1.0;
            count++;
          }
        }
        if (count > 0 && sum / count > 0.5) {
          activeCount++;
        }
      }
      rates[groupName] = activeCount / population.length;
    }
    return rates;
  }

  /// Most silenced genes (expression < 0.2) across the population.
  ///
  /// Returns gene names sorted by ascending average expression.
  static List<String> mostSilencedGenes(
    List<Chromosome> population, {
    int top = 10,
  }) {
    if (population.isEmpty) return [];
    final avgExpr = _avgExpressionPerGene(population);
    final silenced = avgExpr.entries
        .where((e) => e.value < 0.2)
        .toList()
      ..sort((a, b) => a.value.compareTo(b.value));
    return silenced.take(top).map((e) => e.key).toList();
  }

  /// Most amplified genes (expression > 0.8) across the population.
  ///
  /// Returns gene names sorted by descending average expression.
  static List<String> mostAmplifiedGenes(
    List<Chromosome> population, {
    int top = 10,
  }) {
    if (population.isEmpty) return [];
    final avgExpr = _avgExpressionPerGene(population);
    final amplified = avgExpr.entries
        .where((e) => e.value > 0.8)
        .toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return amplified.take(top).map((e) => e.key).toList();
  }

  /// Diversity score: average pairwise expression distance.
  ///
  /// Uses L1 (Manhattan) distance normalized by gene count.
  /// Samples up to 50 pairs for efficiency with large populations.
  static double expressionDiversity(List<Chromosome> population) {
    if (population.length < 2) return 0.0;

    final geneNames = population.first.genes.keys.toList();
    if (geneNames.isEmpty) return 0.0;

    var totalDist = 0.0;
    var pairCount = 0;

    // Sample pairs for efficiency.
    final maxPairs = 50;
    if (population.length <= 10) {
      // All pairs for small populations.
      for (var i = 0; i < population.length; i++) {
        for (var j = i + 1; j < population.length; j++) {
          totalDist += _expressionDistance(
            population[i],
            population[j],
            geneNames,
          );
          pairCount++;
        }
      }
    } else {
      // Random sampling for larger populations.
      final rng = DateTime.now().millisecondsSinceEpoch;
      for (var p = 0; p < maxPairs; p++) {
        final i = (rng * (p + 1) * 7) % population.length;
        var j = (rng * (p + 1) * 13 + 3) % population.length;
        if (j == i) j = (j + 1) % population.length;
        totalDist += _expressionDistance(
          population[i],
          population[j],
          geneNames,
        );
        pairCount++;
      }
    }

    return pairCount > 0 ? totalDist / pairCount : 0.0;
  }

  /// Average active gene count across the population.
  static double avgActiveGenes(List<Chromosome> population) {
    if (population.isEmpty) return 0.0;
    var total = 0;
    for (final c in population) {
      total += c.activeGeneCount;
    }
    return total / population.length;
  }

  static Map<String, double> _avgExpressionPerGene(
    List<Chromosome> population,
  ) {
    final sums = <String, double>{};
    final counts = <String, int>{};

    for (final c in population) {
      for (final gene in c.genes.keys) {
        sums[gene] = (sums[gene] ?? 0.0) +
            (c.expression[gene] ?? 1.0);
        counts[gene] = (counts[gene] ?? 0) + 1;
      }
    }

    return {
      for (final gene in sums.keys)
        gene: sums[gene]! / counts[gene]!,
    };
  }

  static double _expressionDistance(
    Chromosome a,
    Chromosome b,
    List<String> genes,
  ) {
    var dist = 0.0;
    for (final gene in genes) {
      final ea = a.expression[gene] ?? 1.0;
      final eb = b.expression[gene] ?? 1.0;
      dist += (ea - eb).abs();
    }
    return dist / genes.length;
  }
}
