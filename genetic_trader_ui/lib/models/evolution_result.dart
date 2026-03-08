import 'dart:convert';
import 'dart:io';

/// Represents the results of a single evolution run
class EvolutionResult {
  final String runId;
  final DateTime runDate;
  final String mode;
  final List<String> portfolioSymbols;
  final int portfolioSize;
  final double initialAllocationPct;
  final String startDate;
  final String endDate;
  final int populationSize;
  final int numGenerations;
  final BestTraderResult bestTrader;
  final BenchmarkResult benchmark;
  final RunConfig? runConfig;
  final OutOfSampleResult? outOfSample;
  final String? resumedFrom;

  EvolutionResult({
    required this.runId,
    required this.runDate,
    required this.mode,
    required this.portfolioSymbols,
    required this.portfolioSize,
    required this.initialAllocationPct,
    required this.startDate,
    required this.endDate,
    required this.populationSize,
    required this.numGenerations,
    required this.bestTrader,
    required this.benchmark,
    this.runConfig,
    this.outOfSample,
    this.resumedFrom,
  });

  /// Parse run_id format "YYYYMMDD_HHMMSS" into DateTime
  static DateTime _parseRunDate(String runId) {
    try {
      final year = int.parse(runId.substring(0, 4));
      final month = int.parse(runId.substring(4, 6));
      final day = int.parse(runId.substring(6, 8));
      final hour = int.parse(runId.substring(9, 11));
      final minute = int.parse(runId.substring(11, 13));
      final second = int.parse(runId.substring(13, 15));
      return DateTime(year, month, day, hour, minute, second);
    } catch (_) {
      return DateTime.now();
    }
  }

  /// Create from parsed summary JSON
  factory EvolutionResult.fromJson(Map<String, dynamic> json) {
    final runId = json['run_id'] as String? ?? '';
    return EvolutionResult(
      runId: runId,
      runDate: _parseRunDate(runId),
      mode: json['mode'] as String? ?? 'portfolio',
      portfolioSymbols: List<String>.from(
        json['portfolio_symbols'] as List? ?? [],
      ),
      portfolioSize: json['portfolio_size'] as int? ?? 0,
      initialAllocationPct:
          (json['initial_allocation_pct'] as num?)?.toDouble() ?? 0.0,
      startDate: json['start_date'] as String? ?? '',
      endDate: json['end_date'] as String? ?? '',
      populationSize: json['population_size'] as int? ?? 0,
      numGenerations: json['num_generations'] as int? ?? 0,
      bestTrader: BestTraderResult.fromJson(
        json['best_trader'] as Map<String, dynamic>? ?? {},
      ),
      benchmark: BenchmarkResult.fromJson(
        json['benchmark'] as Map<String, dynamic>? ?? {},
      ),
      runConfig: json['config'] != null
          ? RunConfig.fromJson(json['config'] as Map<String, dynamic>)
          : null,
      outOfSample: json['out_of_sample'] != null
          ? OutOfSampleResult.fromJson(
              json['out_of_sample'] as Map<String, dynamic>,
            )
          : null,
      resumedFrom: json['resumed_from'] as String?,
    );
  }

  /// Load from a summary JSON file
  static Future<EvolutionResult?> loadFromFile(File file) async {
    try {
      final content = await file.readAsString();
      final json = jsonDecode(content) as Map<String, dynamic>;
      return EvolutionResult.fromJson(json);
    } catch (_) {
      return null;
    }
  }
}

/// Best trader performance from a run
class BestTraderResult {
  final int generation;
  final double fitness;
  final Map<String, dynamic> genes;
  final TraderPerformance performance;
  final Map<String, StockPerformance>? perStockPerformance;

  BestTraderResult({
    required this.generation,
    required this.fitness,
    required this.genes,
    required this.performance,
    this.perStockPerformance,
  });

  factory BestTraderResult.fromJson(Map<String, dynamic> json) {
    Map<String, StockPerformance>? perStock;
    final rawPerStock = json['per_stock_performance'] as Map<String, dynamic>?;
    if (rawPerStock != null) {
      perStock = rawPerStock.map(
        (key, value) => MapEntry(
          key,
          StockPerformance.fromJson(value as Map<String, dynamic>),
        ),
      );
    }

    return BestTraderResult(
      generation: json['generation'] as int? ?? 0,
      fitness: (json['fitness'] as num?)?.toDouble() ?? 0.0,
      genes: Map<String, dynamic>.from(json['genes'] as Map? ?? {}),
      performance: TraderPerformance.fromJson(
        json['performance'] as Map<String, dynamic>? ?? {},
      ),
      perStockPerformance: perStock,
    );
  }
}

/// Performance metrics for the best trader
class TraderPerformance {
  final double totalReturn;
  final double sharpeRatio;
  final double maxDrawdown;
  final int tradeCount;
  final double winRate;

  TraderPerformance({
    required this.totalReturn,
    required this.sharpeRatio,
    required this.maxDrawdown,
    required this.tradeCount,
    required this.winRate,
  });

  factory TraderPerformance.fromJson(Map<String, dynamic> json) {
    return TraderPerformance(
      totalReturn: (json['total_return'] as num?)?.toDouble() ?? 0.0,
      sharpeRatio: (json['sharpe_ratio'] as num?)?.toDouble() ?? 0.0,
      maxDrawdown: (json['max_drawdown'] as num?)?.toDouble() ?? 0.0,
      tradeCount: json['trade_count'] as int? ?? 0,
      winRate: (json['win_rate'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

/// Per-stock performance from the portfolio backtest
class StockPerformance {
  final int trades;
  final int won;
  final int lost;
  final double pnl;
  final double winRate;

  StockPerformance({
    required this.trades,
    required this.won,
    required this.lost,
    required this.pnl,
    required this.winRate,
  });

  factory StockPerformance.fromJson(Map<String, dynamic> json) {
    return StockPerformance(
      trades: json['trades'] as int? ?? 0,
      won: json['won'] as int? ?? 0,
      lost: json['lost'] as int? ?? 0,
      pnl: (json['pnl'] as num?)?.toDouble() ?? 0.0,
      winRate: (json['win_rate'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

/// Full run configuration for reproducibility
class RunConfig {
  // GA parameters
  final double mutationRate;
  final double crossoverRate;
  final int elitismCount;
  final int tournamentSize;
  final int? randomSeed;

  // K-fold
  final bool useKfoldValidation;
  final int kfoldNumFolds;
  final int kfoldFoldYears;
  final bool kfoldAllowOverlap;
  final bool kfoldWeightRecent;
  final double kfoldRecentWeightFactor;
  final int kfoldMinBarsPerFold;

  // Features
  final bool useMacroData;
  final bool useTechnicalIndicators;
  final bool useEnsembleSignals;

  // Backtrader
  final double initialCash;
  final double commission;
  final double initialAllocationPct;

  // Fitness
  final Map<String, double> fitnessWeights;
  final int minTradesRequired;

  // Execution
  final bool useParallelEvaluation;
  final int? maxParallelWorkers;
  final String? databasePath;

  RunConfig({
    required this.mutationRate,
    required this.crossoverRate,
    required this.elitismCount,
    required this.tournamentSize,
    this.randomSeed,
    required this.useKfoldValidation,
    required this.kfoldNumFolds,
    required this.kfoldFoldYears,
    required this.kfoldAllowOverlap,
    required this.kfoldWeightRecent,
    required this.kfoldRecentWeightFactor,
    required this.kfoldMinBarsPerFold,
    required this.useMacroData,
    required this.useTechnicalIndicators,
    required this.useEnsembleSignals,
    required this.initialCash,
    required this.commission,
    required this.initialAllocationPct,
    required this.fitnessWeights,
    required this.minTradesRequired,
    required this.useParallelEvaluation,
    this.maxParallelWorkers,
    this.databasePath,
  });

  factory RunConfig.fromJson(Map<String, dynamic> json) {
    final ga = json['ga_parameters'] as Map<String, dynamic>? ?? {};
    final kf = json['kfold'] as Map<String, dynamic>? ?? {};
    final feat = json['features'] as Map<String, dynamic>? ?? {};
    final bt = json['backtrader'] as Map<String, dynamic>? ?? {};
    final fit = json['fitness'] as Map<String, dynamic>? ?? {};
    final exec = json['execution'] as Map<String, dynamic>? ?? {};

    final rawWeights = fit['fitness_weights'] as Map<String, dynamic>? ?? {};
    final weights = rawWeights.map(
      (k, v) => MapEntry(k, (v as num?)?.toDouble() ?? 0.0),
    );

    return RunConfig(
      mutationRate: (ga['mutation_rate'] as num?)?.toDouble() ?? 0.0,
      crossoverRate: (ga['crossover_rate'] as num?)?.toDouble() ?? 0.0,
      elitismCount: ga['elitism_count'] as int? ?? 0,
      tournamentSize: ga['tournament_size'] as int? ?? 0,
      randomSeed: ga['random_seed'] as int?,
      useKfoldValidation: kf['use_kfold_validation'] as bool? ?? false,
      kfoldNumFolds: kf['kfold_num_folds'] as int? ?? 2,
      kfoldFoldYears: kf['kfold_fold_years'] as int? ?? 3,
      kfoldAllowOverlap: kf['kfold_allow_overlap'] as bool? ?? false,
      kfoldWeightRecent: kf['kfold_weight_recent'] as bool? ?? false,
      kfoldRecentWeightFactor:
          (kf['kfold_recent_weight_factor'] as num?)?.toDouble() ?? 1.5,
      kfoldMinBarsPerFold: kf['kfold_min_bars_per_fold'] as int? ?? 200,
      useMacroData: feat['use_macro_data'] as bool? ?? false,
      useTechnicalIndicators:
          feat['use_technical_indicators'] as bool? ?? false,
      useEnsembleSignals: feat['use_ensemble_signals'] as bool? ?? false,
      initialCash: (bt['initial_cash'] as num?)?.toDouble() ?? 100000.0,
      commission: (bt['commission'] as num?)?.toDouble() ?? 0.001,
      initialAllocationPct:
          (bt['initial_allocation_pct'] as num?)?.toDouble() ?? 80.0,
      fitnessWeights: weights,
      minTradesRequired: fit['min_trades_required'] as int? ?? 5,
      useParallelEvaluation: exec['use_parallel_evaluation'] as bool? ?? true,
      maxParallelWorkers: exec['max_parallel_workers'] as int?,
      databasePath: exec['database_path'] as String?,
    );
  }
}

/// Benchmark comparison results
class BenchmarkResult {
  final double buyAndHoldReturn;
  final double allocationPct;
  final double outperformance;
  final bool beatsBenchmark;

  BenchmarkResult({
    required this.buyAndHoldReturn,
    required this.allocationPct,
    required this.outperformance,
    required this.beatsBenchmark,
  });

  factory BenchmarkResult.fromJson(Map<String, dynamic> json) {
    return BenchmarkResult(
      buyAndHoldReturn:
          (json['buy_and_hold_return'] as num?)?.toDouble() ?? 0.0,
      allocationPct: (json['allocation_pct'] as num?)?.toDouble() ?? 100.0,
      outperformance:
          (json['strategy_outperformance'] as num?)?.toDouble() ?? 0.0,
      beatsBenchmark: json['beats_benchmark'] as bool? ?? false,
    );
  }
}

/// Out-of-sample test results
class OutOfSampleResult {
  final bool enabled;
  final String testStartDate;
  final String testEndDate;
  final TraderPerformance? performance;
  final OutOfSampleBenchmark? benchmark;
  final Map<String, StockPerformance>? perStockPerformance;
  final String? error;

  OutOfSampleResult({
    required this.enabled,
    required this.testStartDate,
    required this.testEndDate,
    this.performance,
    this.benchmark,
    this.perStockPerformance,
    this.error,
  });

  factory OutOfSampleResult.fromJson(Map<String, dynamic> json) {
    Map<String, StockPerformance>? perStock;
    final rawPerStock =
        json['per_stock_performance'] as Map<String, dynamic>?;
    if (rawPerStock != null) {
      perStock = rawPerStock.map(
        (key, value) => MapEntry(
          key,
          StockPerformance.fromJson(
            value as Map<String, dynamic>,
          ),
        ),
      );
    }

    return OutOfSampleResult(
      enabled: json['enabled'] as bool? ?? false,
      testStartDate:
          json['test_start_date'] as String? ?? '',
      testEndDate: json['test_end_date'] as String? ?? '',
      performance: json['performance'] != null
          ? TraderPerformance.fromJson(
              json['performance'] as Map<String, dynamic>,
            )
          : null,
      benchmark: json['benchmark'] != null
          ? OutOfSampleBenchmark.fromJson(
              json['benchmark'] as Map<String, dynamic>,
            )
          : null,
      perStockPerformance: perStock,
      error: json['error'] as String?,
    );
  }
}

/// Benchmark comparison for the out-of-sample test period
class OutOfSampleBenchmark {
  final double buyAndHoldReturn;
  final double outperformance;
  final bool beatsBenchmark;

  OutOfSampleBenchmark({
    required this.buyAndHoldReturn,
    required this.outperformance,
    required this.beatsBenchmark,
  });

  factory OutOfSampleBenchmark.fromJson(
    Map<String, dynamic> json,
  ) {
    return OutOfSampleBenchmark(
      buyAndHoldReturn:
          (json['buy_and_hold_return'] as num?)?.toDouble() ??
              0.0,
      outperformance:
          (json['outperformance'] as num?)?.toDouble() ?? 0.0,
      beatsBenchmark:
          json['beats_benchmark'] as bool? ?? false,
    );
  }
}

/// A gene change between generations
class GeneChange {
  final String gene;
  final String oldValue;
  final String newValue;

  const GeneChange({
    required this.gene,
    required this.oldValue,
    required this.newValue,
  });
}

/// A single row from the fitness history CSV
class FitnessHistoryEntry {
  final int generation;
  final double bestFitness;
  final double avgFitness;
  final double worstFitness;
  final double stdFitness;
  final List<GeneChange>? geneChanges;

  FitnessHistoryEntry({
    required this.generation,
    required this.bestFitness,
    required this.avgFitness,
    required this.worstFitness,
    required this.stdFitness,
    this.geneChanges,
  });

  /// Parse a CSV row (after header)
  static FitnessHistoryEntry? fromCsvRow(String row) {
    final parts = row.split(',');
    if (parts.length < 5) return null;
    try {
      return FitnessHistoryEntry(
        generation: int.parse(parts[0].trim()),
        bestFitness: double.parse(parts[1].trim()),
        avgFitness: double.parse(parts[2].trim()),
        worstFitness: double.parse(parts[3].trim()),
        stdFitness: double.parse(parts[4].trim()),
      );
    } catch (_) {
      return null;
    }
  }

  /// Parse all rows from a CSV file content
  static List<FitnessHistoryEntry> fromCsvContent(String content) {
    final lines = const LineSplitter().convert(content);
    if (lines.length < 2) return [];

    // Skip header row
    return lines
        .skip(1)
        .where((line) => line.trim().isNotEmpty)
        .map(FitnessHistoryEntry.fromCsvRow)
        .whereType<FitnessHistoryEntry>()
        .toList();
  }
}
