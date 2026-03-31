import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import '../core/genetic/evolution_engine.dart';
import '../core/genetic/gene_definitions.dart';
import '../core/genetic/gene_groups.dart';
import '../core/genetic/fitness_evaluator.dart';
import '../core/backtesting/backtester.dart';
import '../core/models/bar.dart';
import '../core/services/database_service.dart';
import '../core/services/index_service.dart';
import 'python_bridge.dart';

/// Pure-Dart evolution service that replaces PythonBridge.
///
/// Provides the same callback-based API as PythonBridge so that
/// EvolutionViewModel requires only minimal changes.
class EvolutionService {
  EvolutionEngine? _engine;
  bool _isRunning = false;
  final List<String> _outputLines = [];

  bool get isRunning => _isRunning;
  List<String> get outputLines => List.unmodifiable(_outputLines);

  /// Start the evolution process using the native Dart engine.
  Future<void> startEvolution({
    required Function(String line) onOutput,
    required Function(EvolutionProgress progress) onProgress,
    required Function() onComplete,
    required Function(String error) onError,
    String? resumeRunId,
    // Config parameters
    int populationSize = 50,
    int numGenerations = 20,
    double mutationRate = 0.1,
    double crossoverRate = 0.8,
    double elitismPct = 0.1,
    int tournamentSize = 4,
    double initialCash = 100000.0,
    double commissionPct = 0.001,
    int? randomSeed,
    Map<String, double>? fitnessWeights,
    // Portfolio parameters
    int portfolioSize = 20,
    List<String> portfolioStocks = const [],
    bool autoSelectPortfolio = true,
    // Data parameters
    Set<String> selectedIndices = const {'DJIA'},
    List<Bar>? bars,
    DatabaseService? db,
    // Gene group toggles (matching UI switches)
    Set<String>? enabledGroups,
  }) async {
    if (_isRunning) {
      onError('Evolution is already running');
      return;
    }

    _isRunning = true;
    _outputLines.clear();
    _engine = EvolutionEngine();

    try {
      // Resolve bars
      List<Bar> dataBars;
      if (bars != null && bars.isNotEmpty) {
        dataBars = bars;
      } else {
        // Open the database and load bars for the selected indices
        final database = db ?? DatabaseService();
        if (!database.isOpen) {
          await database.open();
        }

        // Determine which symbols to use.
        List<String> symbolsToLoad;
        if (!autoSelectPortfolio && portfolioStocks.isNotEmpty) {
          // User specified exact stocks
          symbolsToLoad = portfolioStocks;
        } else {
          // Auto-select from index universe
          final universe = <String>[];
          for (final name in selectedIndices) {
            final idx = IndexType.values.firstWhere(
              (t) => t.name.toUpperCase() == name.toUpperCase(),
              orElse: () => IndexType.djia,
            );
            universe.addAll(IndexService.getSymbols(idx));
          }
          // Deduplicate and shuffle for random selection
          final deduped = universe.toSet().toList();
          if (randomSeed != null) {
            deduped.shuffle(Random(randomSeed));
          } else {
            deduped.shuffle();
          }
          symbolsToLoad =
              deduped.take(portfolioSize).toList();
        }

        _log(onOutput, 'Loading data for '
            '${symbolsToLoad.length} symbols...');

        dataBars = [];
        for (final symbol in symbolsToLoad) {
          final symbolBars = await database.getBars(symbol);
          dataBars.addAll(symbolBars);
        }

        if (dataBars.isEmpty) {
          _log(onOutput,
              'No bar data found. Using synthetic data.');
          dataBars = _generateSyntheticBars(500);
        } else {
          // Sort by date so multi-symbol bars interleave properly
          dataBars.sort((a, b) => a.date.compareTo(b.date));
          final uniqueSymbols = dataBars
              .map((b) => b.symbol)
              .toSet();
          _log(onOutput,
              'Loaded ${dataBars.length} bars across '
              '${uniqueSymbols.length} symbols');
        }
      }

      _log(onOutput, 'Starting Dart evolution engine...');
      _log(onOutput, 'Population: $populationSize, '
          'Generations: $numGenerations');
      _log(onOutput, 'Data: ${dataBars.length} bars');

      // Build fitness weights
      final fw = fitnessWeights ?? {};
      final evaluator = FitnessEvaluator(
        returnWeight: fw['total_return'] ?? 0.4,
        sharpeWeight: fw['sharpe_ratio'] ?? 0.24,
        drawdownWeight: fw['max_drawdown'] ?? 0.24,
        winRateWeight: fw['win_rate'] ?? 0.12,
        backtestConfig: BacktestConfig(
          initialCash: initialCash,
          commissionPct: commissionPct,
        ),
      );

      // Filter genes to only include enabled groups.
      // Core group is always included.
      final activeGroupNames = <String>{GeneGroups.core};
      if (enabledGroups != null) {
        activeGroupNames.addAll(enabledGroups);
      } else {
        // No filter specified — include everything.
        activeGroupNames.addAll(GeneGroups.allGroups);
      }

      final filteredGenes = <String, GeneRange>{};
      for (final entry in GeneDefinitions.defaultGenes.entries) {
        final group = GeneGroups.geneToGroup[entry.key];
        if (group != null && activeGroupNames.contains(group)) {
          filteredGenes[entry.key] = entry.value;
        }
      }

      _log(onOutput, 'Gene groups: ${activeGroupNames.length} active '
          '(${filteredGenes.length} genes)');

      final config = EvolutionConfig(
        populationSize: populationSize,
        numGenerations: numGenerations,
        mutationRate: mutationRate,
        crossoverRate: crossoverRate,
        elitismPct: elitismPct / 100.0, // Convert from percentage
        tournamentSize: tournamentSize,
        geneDefinitions: filteredGenes,
        backtestConfig: BacktestConfig(
          initialCash: initialCash,
          commissionPct: commissionPct,
        ),
        fitnessEvaluator: evaluator,
        randomSeed: randomSeed,
      );

      final result = await _engine!.run(
        config,
        dataBars,
        onGeneration: (genResult) {
          final gen = genResult.generation;
          final total = numGenerations;

          _log(onOutput, 'Generation $gen/$total');
          _log(onOutput, 'Best Fitness: '
              '${genResult.bestFitness.toStringAsFixed(4)}');
          _log(onOutput, 'Average Fitness: '
              '${genResult.avgFitness.toStringAsFixed(4)}');
          _log(onOutput, 'Worst Fitness: '
              '${genResult.worstFitness.toStringAsFixed(4)}');
          _log(onOutput, 'Std Dev: '
              '${genResult.stdDev.toStringAsFixed(4)}');
          _log(onOutput, 'Active Genes: '
              '${genResult.avgActiveGenes} / '
              '${filteredGenes.length} (avg)');

          onProgress(EvolutionProgress(
            currentGeneration: gen,
            totalGenerations: total,
          ));
          onProgress(EvolutionProgress(
            bestFitness: genResult.bestFitness,
          ));
          onProgress(EvolutionProgress(
            avgFitness: genResult.avgFitness,
          ));
          onProgress(EvolutionProgress(
            worstFitness: genResult.worstFitness,
          ));
          onProgress(EvolutionProgress(
            stdDev: genResult.stdDev,
          ));
          onProgress(EvolutionProgress(
            groupActivityRates: genResult.groupActivityRates,
            avgActiveGenes: genResult.avgActiveGenes,
          ));
        },
      );

      _log(onOutput, '');
      _log(onOutput, 'Evolution complete!');
      _log(onOutput, 'Best fitness: '
          '${result.bestFitness.toStringAsFixed(4)}');
      _log(onOutput, 'Best genes: ${result.bestChromosome.genes}');

      // Build per-stock performance from trades.
      final bt = result.bestBacktestResult;
      Map<String, Map<String, dynamic>>? perStock;
      if (bt != null && bt.trades.isNotEmpty) {
        final stockMap = <String, Map<String, dynamic>>{};
        for (final t in bt.trades) {
          final s = stockMap.putIfAbsent(
            t.symbol,
            () => <String, dynamic>{
              'trades': 0,
              'won': 0,
              'lost': 0,
              'pnl': 0.0,
            },
          );
          s['trades'] = (s['trades'] as int) + 1;
          if (t.isWin) {
            s['won'] = (s['won'] as int) + 1;
          } else {
            s['lost'] = (s['lost'] as int) + 1;
          }
          s['pnl'] = (s['pnl'] as double) + t.pnl;
        }
        // Add win rate per stock.
        for (final entry in stockMap.entries) {
          final trades = entry.value['trades'] as int;
          final won = entry.value['won'] as int;
          entry.value['win_rate'] =
              trades > 0 ? won / trades : 0.0;
        }
        perStock = stockMap;

        _log(onOutput, 'Return: '
            '${(bt.totalReturn * 100).toStringAsFixed(2)}%');
        _log(onOutput, 'Sharpe: '
            '${bt.sharpeRatio.toStringAsFixed(3)}');
        _log(onOutput, 'Max Drawdown: '
            '${(bt.maxDrawdown * 100).toStringAsFixed(2)}%');
        _log(onOutput, 'Win Rate: '
            '${(bt.winRate * 100).toStringAsFixed(1)}%');
        _log(onOutput, 'Trades: ${bt.numTrades}');
      }

      // Compute buy-and-hold benchmark.
      // Average return across all unique symbols in the data.
      double buyAndHold = 0.0;
      final symbolSet = dataBars.map((b) => b.symbol).toSet();
      if (symbolSet.isNotEmpty) {
        double totalBhReturn = 0.0;
        int counted = 0;
        for (final sym in symbolSet) {
          final symBars = dataBars
              .where((b) => b.symbol == sym)
              .toList();
          if (symBars.length >= 2) {
            final first = symBars.first.close;
            final last = symBars.last.close;
            if (first > 0) {
              totalBhReturn += (last - first) / first;
              counted++;
            }
          }
        }
        if (counted > 0) {
          buyAndHold = totalBhReturn / counted;
        }
        _log(onOutput, 'Buy & Hold (avg): '
            '${(buyAndHold * 100).toStringAsFixed(2)}%');
      }

      // Generate a run ID
      final now = DateTime.now();
      final runId = '${now.year}'
          '${now.month.toString().padLeft(2, '0')}'
          '${now.day.toString().padLeft(2, '0')}_'
          '${now.hour.toString().padLeft(2, '0')}'
          '${now.minute.toString().padLeft(2, '0')}'
          '${now.second.toString().padLeft(2, '0')}';
      onProgress(EvolutionProgress(
        runId: runId,
        bestGenes: Map<String, double>.from(
          result.bestChromosome.genes,
        ),
        bestTotalReturn: bt?.totalReturn,
        bestSharpeRatio: bt?.sharpeRatio,
        bestMaxDrawdown: bt?.maxDrawdown,
        bestWinRate: bt?.winRate,
        bestTradeCount: bt?.numTrades,
        perStockPerformance: perStock,
        buyAndHoldReturn: buyAndHold,
      ));

      _isRunning = false;
      onComplete();
    } catch (e, st) {
      _isRunning = false;
      if (kDebugMode) {
        print('Evolution error: $e\n$st');
      }
      onError('Evolution failed: $e');
    }
  }

  /// Stop the evolution process.
  void stop() {
    _engine?.stop();
    _isRunning = false;
  }

  /// Clear output history.
  void clearOutput() {
    _outputLines.clear();
  }

  /// Get the most recent output lines.
  List<String> getRecentOutput({int count = 100}) {
    if (_outputLines.length <= count) return _outputLines;
    return _outputLines.sublist(_outputLines.length - count);
  }

  void _log(Function(String) onOutput, String line) {
    _outputLines.add(line);
    onOutput(line);
    if (kDebugMode) {
      print('[DartEngine] $line');
    }
  }

  /// Generate synthetic bar data for testing without a database.
  List<Bar> _generateSyntheticBars(int count) {
    final bars = <Bar>[];
    var price = 100.0;
    for (var i = 0; i < count; i++) {
      // Simple random walk
      final change = (i % 7 - 3) * 0.5;
      price += change;
      if (price < 10) price = 10;
      bars.add(Bar(
        symbol: 'SYNTH',
        date: DateTime(2020, 1, 1).add(Duration(days: i)),
        open: price,
        high: price + 1.5,
        low: price - 1.5,
        close: price + 0.3,
        volume: 100000,
      ));
    }
    return bars;
  }
}
