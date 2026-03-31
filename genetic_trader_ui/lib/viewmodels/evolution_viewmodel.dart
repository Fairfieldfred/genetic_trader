import 'package:flutter/foundation.dart';
import '../core/genetic/gene_groups.dart';
import '../models/config_model.dart';
import '../models/evolution_result.dart';
import '../services/python_bridge.dart';
import '../services/evolution_service.dart';

/// ViewModel for managing evolution execution state
class EvolutionViewModel extends ChangeNotifier {
  final EvolutionService _evolutionService = EvolutionService();

  // State
  bool _isRunning = false;
  bool _isCompleted = false;
  String? _error;
  final List<String> _outputLines = [];
  EvolutionProgress _progress = EvolutionProgress();
  final List<FitnessHistoryEntry> _fitnessHistory = [];
  int _lastRecordedGeneration = -1;
  List<GeneChange> _pendingGeneChanges = [];

  String? _runId;
  Map<String, double>? _bestGenes;
  GeneticConfig? _lastConfig;
  double? _bestTotalReturn;
  double? _bestSharpeRatio;
  double? _bestMaxDrawdown;
  double? _bestWinRate;
  int? _bestTradeCount;
  Map<String, Map<String, dynamic>>? _perStockPerformance;
  double? _buyAndHoldReturn;

  // Getters
  bool get isRunning => _isRunning;
  bool get isCompleted => _isCompleted;
  String? get error => _error;
  List<String> get outputLines => List.unmodifiable(_outputLines);
  EvolutionProgress get progress => _progress;
  List<FitnessHistoryEntry> get fitnessHistory =>
      List.unmodifiable(_fitnessHistory);
  String? get runId => _runId;

  int get currentGeneration => _progress.currentGeneration ?? 0;
  int get totalGenerations => _progress.totalGenerations ?? 0;
  double get bestFitness => _progress.bestFitness ?? 0.0;
  double get avgFitness => _progress.avgFitness ?? 0.0;
  double get worstFitness => _progress.worstFitness ?? 0.0;
  double get stdDev => _progress.stdDev ?? 0.0;
  double get progressPercentage => _progress.progress * 100;
  Map<String, double> get groupActivityRates =>
      _progress.groupActivityRates ?? {};
  int get avgActiveGenes => _progress.avgActiveGenes ?? 0;

  /// Start evolution process using the provided config.
  Future<void> startEvolution({
    String? resumeRunId,
    GeneticConfig? config,
  }) async {
    if (_isRunning) return;

    // Reset state
    _isRunning = true;
    _isCompleted = false;
    _error = null;
    _bestGenes = null;
    _lastConfig = config;
    _outputLines.clear();
    _progress = EvolutionProgress();
    notifyListeners();

    await _evolutionService.startEvolution(
      resumeRunId: resumeRunId,
      populationSize: config?.populationSize ?? 50,
      numGenerations: config?.numGenerations ?? 20,
      mutationRate: config?.mutationRate ?? 0.1,
      crossoverRate: config?.crossoverRate ?? 0.8,
      elitismPct: config?.elitismPct ?? 10.0,
      tournamentSize: config?.tournamentSize ?? 4,
      initialCash: config?.initialCash ?? 100000.0,
      commissionPct: config?.commission ?? 0.001,
      randomSeed: config?.randomSeed,
      fitnessWeights: config?.fitnessWeights,
      portfolioSize: config?.portfolioSize ?? 20,
      portfolioStocks: config?.portfolioStocks ?? const [],
      autoSelectPortfolio: config?.autoSelectPortfolio ?? true,
      selectedIndices: config?.selectedIndices ?? const {'DJIA'},
      enabledGroups: config != null ? _buildEnabledGroups(config) : null,
      onOutput: (line) {
        _outputLines.add(line);

        // Keep only last 1000 lines to prevent memory issues
        if (_outputLines.length > 1000) {
          _outputLines.removeAt(0);
        }

        notifyListeners();
      },
      onProgress: (progress) {
        // Capture run_id and best genes when they appear
        if (progress.runId != null) {
          _runId = progress.runId;
        }
        if (progress.bestGenes != null) {
          _bestGenes = progress.bestGenes;
        }
        if (progress.bestTotalReturn != null) {
          _bestTotalReturn = progress.bestTotalReturn;
          _bestSharpeRatio = progress.bestSharpeRatio;
          _bestMaxDrawdown = progress.bestMaxDrawdown;
          _bestWinRate = progress.bestWinRate;
          _bestTradeCount = progress.bestTradeCount;
          _perStockPerformance = progress.perStockPerformance;
          _buyAndHoldReturn = progress.buyAndHoldReturn;
        }

        // Accumulate gene changes for current generation
        if (progress.geneChanges != null) {
          for (final gc in progress.geneChanges!) {
            _pendingGeneChanges.add(GeneChange(
              gene: gc.gene,
              oldValue: gc.oldValue,
              newValue: gc.newValue,
            ));
          }
        }

        // Merge progress updates
        _progress = _progress.copyWith(
          currentGeneration:
              progress.currentGeneration ??
              _progress.currentGeneration,
          totalGenerations:
              progress.totalGenerations ??
              _progress.totalGenerations,
          bestFitness:
              progress.bestFitness ?? _progress.bestFitness,
          avgFitness:
              progress.avgFitness ?? _progress.avgFitness,
          worstFitness:
              progress.worstFitness ?? _progress.worstFitness,
          stdDev: progress.stdDev ?? _progress.stdDev,
          groupActivityRates:
              progress.groupActivityRates ??
              _progress.groupActivityRates,
          avgActiveGenes:
              progress.avgActiveGenes ??
              _progress.avgActiveGenes,
        );

        // Detect generation complete: when worst fitness arrives
        // and we have all metrics for a new generation
        if (progress.worstFitness != null &&
            _progress.currentGeneration != null &&
            _progress.currentGeneration! >
                _lastRecordedGeneration &&
            _progress.bestFitness != null &&
            _progress.avgFitness != null) {
          _fitnessHistory.add(FitnessHistoryEntry(
            generation: _progress.currentGeneration!,
            bestFitness: _progress.bestFitness!,
            avgFitness: _progress.avgFitness!,
            worstFitness: _progress.worstFitness!,
            stdFitness: _progress.stdDev ?? 0.0,
            geneChanges: _pendingGeneChanges.isNotEmpty
                ? List.of(_pendingGeneChanges)
                : null,
            groupActivityRates: _progress.groupActivityRates,
            avgActiveGenes: _progress.avgActiveGenes,
          ));
          _lastRecordedGeneration =
              _progress.currentGeneration!;
          _pendingGeneChanges = [];
        }

        notifyListeners();
      },
      onComplete: () {
        _isRunning = false;
        _isCompleted = true;
        notifyListeners();
      },
      onError: (error) {
        _error = error;
        _isRunning = false;
        _isCompleted = true;
        notifyListeners();
      },
    );
  }

  /// Stop evolution process
  void stopEvolution() {
    if (_isRunning) {
      _evolutionService.stop();
      _isRunning = false;
      _error = 'Evolution stopped by user';
      notifyListeners();
    }
  }

  /// Build an [EvolutionResult] from the in-memory run data.
  ///
  /// Returns null if the run hasn't completed or has no data.
  EvolutionResult? buildResult() {
    if (_runId == null || !_isCompleted) return null;
    final cfg = _lastConfig;

    final totalReturn = _bestTotalReturn ?? 0.0;
    final sharpe = _bestSharpeRatio ?? 0.0;
    final drawdown = _bestMaxDrawdown ?? 0.0;
    final winRate = _bestWinRate ?? 0.0;
    final tradeCount = _bestTradeCount ?? 0;

    // Build per-stock performance map.
    Map<String, StockPerformance>? perStock;
    if (_perStockPerformance != null) {
      perStock = _perStockPerformance!.map(
        (symbol, data) => MapEntry(
          symbol,
          StockPerformance(
            trades: data['trades'] as int? ?? 0,
            won: data['won'] as int? ?? 0,
            lost: data['lost'] as int? ?? 0,
            pnl: (data['pnl'] as num?)?.toDouble() ?? 0.0,
            winRate:
                (data['win_rate'] as num?)?.toDouble() ?? 0.0,
          ),
        ),
      );
    }

    return EvolutionResult(
      runId: _runId!,
      runDate: DateTime.now(),
      mode: 'portfolio',
      portfolioSymbols: cfg?.portfolioStocks ?? [],
      portfolioSize: cfg?.portfolioSize ?? 0,
      initialAllocationPct: cfg?.initialAllocationPct ?? 80.0,
      startDate: cfg?.trainStartDate ?? '',
      endDate: cfg?.testEndDate ?? '',
      populationSize: cfg?.populationSize ?? 0,
      numGenerations: cfg?.numGenerations ?? 0,
      bestTrader: BestTraderResult(
        generation: _progress.currentGeneration ?? 0,
        fitness: _progress.bestFitness ?? 0.0,
        genes: _bestGenes?.map(
              (k, v) => MapEntry(k, v as dynamic),
            ) ??
            {},
        performance: TraderPerformance(
          totalReturn: totalReturn * 100,
          sharpeRatio: sharpe,
          maxDrawdown: drawdown * 100,
          tradeCount: tradeCount,
          winRate: winRate * 100,
        ),
        perStockPerformance: perStock,
      ),
      benchmark: BenchmarkResult(
        // Scale buy-and-hold by allocation % so the benchmark
        // reflects the same capital deployment as the strategy.
        buyAndHoldReturn: (_buyAndHoldReturn ?? 0) *
            100 *
            (cfg?.initialAllocationPct ?? 80.0) /
            100.0,
        allocationPct: cfg?.initialAllocationPct ?? 80.0,
        outperformance: totalReturn * 100 -
            (_buyAndHoldReturn ?? 0) *
                100 *
                (cfg?.initialAllocationPct ?? 80.0) /
                100.0,
        beatsBenchmark: totalReturn >
            (_buyAndHoldReturn ?? 0) *
                (cfg?.initialAllocationPct ?? 80.0) /
                100.0,
      ),
    );
  }

  /// Map UI toggle booleans to gene group names.
  Set<String> _buildEnabledGroups(GeneticConfig config) {
    final groups = <String>{};
    if (config.useMacroData) groups.add(GeneGroups.macro);
    if (config.useTechnicalIndicators) {
      groups.add(GeneGroups.technicalIndicators);
    }
    if (config.useEnsembleSignals) groups.add(GeneGroups.ensemble);
    if (config.useAdvancedOscillators) {
      groups.add(GeneGroups.advancedOscillators);
    }
    if (config.useTrendSignals) groups.add(GeneGroups.trendSignals);
    if (config.useVolumeSignals) {
      groups.add(GeneGroups.volumeSignals);
    }
    if (config.useVolatilityBreakout) {
      groups.add(GeneGroups.volatilityBreakout);
    }
    if (config.useSupportResistance) {
      groups.add(GeneGroups.supportResistance);
    }
    if (config.useRegimeDetection) {
      groups.add(GeneGroups.regimeDetection);
    }
    if (config.useAdvancedSizing) {
      groups.add(GeneGroups.advancedSizing);
    }
    return groups;
  }

  /// Reset state for new run
  void reset() {
    _isRunning = false;
    _isCompleted = false;
    _error = null;
    _runId = null;
    _bestGenes = null;
    _lastConfig = null;
    _bestTotalReturn = null;
    _bestSharpeRatio = null;
    _bestMaxDrawdown = null;
    _bestWinRate = null;
    _bestTradeCount = null;
    _perStockPerformance = null;
    _buyAndHoldReturn = null;
    _outputLines.clear();
    _fitnessHistory.clear();
    _lastRecordedGeneration = -1;
    _pendingGeneChanges = [];
    _progress = EvolutionProgress();
    _evolutionService.clearOutput();
    notifyListeners();
  }

  @override
  void dispose() {
    _evolutionService.stop();
    super.dispose();
  }
}
