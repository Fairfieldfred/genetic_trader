/// Gene map with an associated fitness score and expression weights.
class Chromosome {
  final Map<String, double> genes;
  final double fitness;

  /// Gene expression weights: 0.0 (silenced) to 1.0 (fully active).
  /// Missing entries default to 1.0 (fully active).
  final Map<String, double> expression;

  const Chromosome({
    required this.genes,
    this.fitness = 0.0,
    this.expression = const {},
  });

  Chromosome copyWith({
    Map<String, double>? genes,
    double? fitness,
    Map<String, double>? expression,
  }) {
    return Chromosome(
      genes: genes ?? Map.of(this.genes),
      fitness: fitness ?? this.fitness,
      expression: expression ?? Map.of(this.expression),
    );
  }

  double operator [](String gene) => genes[gene] ?? 0.0;

  /// Effective value of a gene after applying expression weight.
  /// Silenced genes (expression < 0.05) return [neutral].
  double effectiveValue(String gene, {double neutral = 0.0}) {
    final raw = genes[gene] ?? neutral;
    final w = expression[gene] ?? 1.0;
    if (w < 0.05) return neutral; // silenced
    if (w > 0.95) return raw; // fully active
    return raw * w + neutral * (1.0 - w); // interpolate
  }

  /// True if a gene is effectively silenced (expression < 0.05).
  bool isSilenced(String gene) => (expression[gene] ?? 1.0) < 0.05;

  /// How many genes are currently active (expression >= 0.05).
  int get activeGeneCount =>
      genes.keys.where((g) => !isSilenced(g)).length;

  @override
  String toString() => 'Chromosome(fitness: $fitness, genes: $genes)';
}
