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

  BestTraderResult({
    required this.generation,
    required this.fitness,
    required this.genes,
    required this.performance,
  });

  factory BestTraderResult.fromJson(Map<String, dynamic> json) {
    return BestTraderResult(
      generation: json['generation'] as int? ?? 0,
      fitness: (json['fitness'] as num?)?.toDouble() ?? 0.0,
      genes: Map<String, dynamic>.from(json['genes'] as Map? ?? {}),
      performance: TraderPerformance.fromJson(
        json['performance'] as Map<String, dynamic>? ?? {},
      ),
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

/// A single row from the fitness history CSV
class FitnessHistoryEntry {
  final int generation;
  final double bestFitness;
  final double avgFitness;
  final double worstFitness;
  final double stdFitness;

  FitnessHistoryEntry({
    required this.generation,
    required this.bestFitness,
    required this.avgFitness,
    required this.worstFitness,
    required this.stdFitness,
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
