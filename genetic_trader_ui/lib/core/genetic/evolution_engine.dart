import 'dart:isolate';
import 'dart:math';
import '../models/bar.dart';
import '../models/chromosome.dart';
import 'gene_definitions.dart';
import 'operators.dart';
import 'fitness_evaluator.dart';
import 'expression_analytics.dart';
import '../backtesting/backtester.dart';
import '../models/backtest_result.dart';

/// Result of a single generation.
class GenerationResult {
  final int generation;
  final Chromosome bestChromosome;
  final double bestFitness;
  final double avgFitness;
  final double worstFitness;
  final double stdDev;

  /// Average active genes across the population.
  final int avgActiveGenes;

  /// Group name to fraction of population with group active.
  final Map<String, double> groupActivityRates;

  const GenerationResult({
    required this.generation,
    required this.bestChromosome,
    required this.bestFitness,
    required this.avgFitness,
    required this.worstFitness,
    required this.stdDev,
    this.avgActiveGenes = 0,
    this.groupActivityRates = const {},
  });
}

/// Final result of an evolution run.
class EvolutionResult {
  final Chromosome bestChromosome;
  final double bestFitness;
  final int totalGenerations;
  final List<GenerationResult> history;

  /// Full backtest result for the best chromosome.
  final BacktestResult? bestBacktestResult;

  const EvolutionResult({
    required this.bestChromosome,
    required this.bestFitness,
    required this.totalGenerations,
    required this.history,
    this.bestBacktestResult,
  });
}

/// Configuration for an evolution run.
class EvolutionConfig {
  final int populationSize;
  final int numGenerations;
  final double mutationRate;
  final double crossoverRate;
  final double elitismPct;
  final int tournamentSize;
  final Map<String, GeneRange> geneDefinitions;
  final BacktestConfig backtestConfig;
  final FitnessEvaluator fitnessEvaluator;
  final int? randomSeed;

  /// Expression mutation rate (separate from gene mutation rate).
  final double expressionMutationRate;

  const EvolutionConfig({
    this.populationSize = 50,
    this.numGenerations = 20,
    this.mutationRate = 0.1,
    this.crossoverRate = 0.8,
    this.elitismPct = 0.1,
    this.tournamentSize = 4,
    this.geneDefinitions = const {},
    this.backtestConfig = const BacktestConfig(),
    this.fitnessEvaluator = const FitnessEvaluator(),
    this.randomSeed,
    this.expressionMutationRate = 0.15,
  });
}

/// The main genetic algorithm evolution engine.
class EvolutionEngine {
  bool _stopped = false;

  /// Stop the evolution.
  void stop() {
    _stopped = true;
  }

  /// Run the evolution.
  Future<EvolutionResult> run(
    EvolutionConfig config,
    List<Bar> bars, {
    void Function(GenerationResult)? onGeneration,
  }) async {
    final genes = config.geneDefinitions.isEmpty
        ? GeneDefinitions.defaultGenes
        : config.geneDefinitions;

    // Initialize population.
    var population = GeneticOperators.initPopulation(
      config.populationSize,
      genes,
      seed: config.randomSeed,
    );

    final history = <GenerationResult>[];
    Chromosome bestOverall = population.first;

    for (var gen = 0;
        gen < config.numGenerations && !_stopped;
        gen++) {
      // Evaluate fitness using Isolate.run for each chromosome.
      population = await _evaluatePopulation(
        population,
        bars,
        config.fitnessEvaluator,
      );

      // Sort by fitness descending.
      population.sort((a, b) => b.fitness.compareTo(a.fitness));

      // Compute stats.
      final fitnesses =
          population.map((c) => c.fitness).toList();
      final best = fitnesses.first;
      final worst = fitnesses.last;
      final avg =
          fitnesses.reduce((a, b) => a + b) / fitnesses.length;
      var sumSq = 0.0;
      for (final f in fitnesses) {
        sumSq += (f - avg) * (f - avg);
      }
      final variance = fitnesses.length > 1
          ? sumSq / (fitnesses.length - 1)
          : 0.0;
      final stdDev = sqrt(variance);

      // Compute expression analytics.
      final activityRates =
          ExpressionAnalytics.groupActivityRates(population);
      final avgActive =
          ExpressionAnalytics.avgActiveGenes(population);

      final genResult = GenerationResult(
        generation: gen + 1,
        bestChromosome: population.first,
        bestFitness: best,
        avgFitness: avg,
        worstFitness: worst,
        stdDev: stdDev,
        avgActiveGenes: avgActive.round(),
        groupActivityRates: activityRates,
      );
      history.add(genResult);
      onGeneration?.call(genResult);

      if (population.first.fitness > bestOverall.fitness) {
        bestOverall = population.first;
      }

      // Last generation - no need to breed.
      if (gen == config.numGenerations - 1) break;

      // Create next generation.
      population = _evolveGeneration(
        population,
        genes,
        config,
      );
    }

    // Re-evaluate best chromosome to get full backtest metrics.
    final (_, bestResult) =
        config.fitnessEvaluator.evaluateWithResult(
      bestOverall,
      bars,
    );

    return EvolutionResult(
      bestChromosome: bestOverall,
      bestFitness: bestOverall.fitness,
      totalGenerations: history.length,
      history: history,
      bestBacktestResult: bestResult,
    );
  }

  /// Evaluate all chromosomes in the population concurrently.
  Future<List<Chromosome>> _evaluatePopulation(
    List<Chromosome> population,
    List<Bar> bars,
    FitnessEvaluator evaluator,
  ) async {
    final futures = population.map((chromosome) {
      return Isolate.run(() {
        return evaluator.evaluate(chromosome, bars);
      });
    }).toList();

    final fitnesses = await Future.wait(futures);

    return [
      for (var i = 0; i < population.length; i++)
        population[i].copyWith(fitness: fitnesses[i]),
    ];
  }

  /// Create the next generation via selection, crossover, and
  /// mutation (gene values + expression weights).
  List<Chromosome> _evolveGeneration(
    List<Chromosome> sortedPop,
    Map<String, GeneRange> genes,
    EvolutionConfig config,
  ) {
    final nextGen = <Chromosome>[];
    final eliteCount =
        (sortedPop.length * config.elitismPct).round();
    final rng = Random(config.randomSeed);

    // Elitism: carry over top individuals.
    for (var i = 0;
        i < eliteCount && i < sortedPop.length;
        i++) {
      nextGen.add(sortedPop[i]);
    }

    // Fill the rest via selection + crossover + mutation.
    while (nextGen.length < config.populationSize) {
      final parent1 = GeneticOperators.tournamentSelect(
        sortedPop,
        config.tournamentSize,
        rng: rng,
      );
      final parent2 = GeneticOperators.tournamentSelect(
        sortedPop,
        config.tournamentSize,
        rng: rng,
      );

      Chromosome child1;
      Chromosome child2;

      if (rng.nextDouble() < config.crossoverRate) {
        final children = GeneticOperators.uniformCrossover(
          parent1,
          parent2,
          rng: rng,
        );
        child1 = children.$1;
        child2 = children.$2;
      } else {
        child1 = parent1.copyWith(fitness: 0.0);
        child2 = parent2.copyWith(fitness: 0.0);
      }

      // Gene value mutation.
      child1 = GeneticOperators.gaussianMutate(
        child1,
        genes,
        config.mutationRate,
      );
      child2 = GeneticOperators.gaussianMutate(
        child2,
        genes,
        config.mutationRate,
      );

      // Expression mutation.
      child1 = GeneticOperators.expressionMutate(
        child1,
        config.expressionMutationRate,
      );
      child2 = GeneticOperators.expressionMutate(
        child2,
        config.expressionMutationRate,
      );

      nextGen.add(child1);
      if (nextGen.length < config.populationSize) {
        nextGen.add(child2);
      }
    }

    return nextGen;
  }
}
