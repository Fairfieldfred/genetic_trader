import 'package:flutter/foundation.dart';
import '../models/evolution_result.dart';
import '../services/python_bridge.dart';

/// ViewModel for managing evolution execution state
class EvolutionViewModel extends ChangeNotifier {
  final PythonBridge _pythonBridge = PythonBridge();

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

  /// Start evolution process
  Future<void> startEvolution({String? resumeRunId}) async {
    if (_isRunning) return;

    // Reset state
    _isRunning = true;
    _isCompleted = false;
    _error = null;
    _outputLines.clear();
    _progress = EvolutionProgress();
    notifyListeners();

    await _pythonBridge.startEvolution(
      resumeRunId: resumeRunId,
      onOutput: (line) {
        _outputLines.add(line);

        // Keep only last 1000 lines to prevent memory issues
        if (_outputLines.length > 1000) {
          _outputLines.removeAt(0);
        }

        notifyListeners();
      },
      onProgress: (progress) {
        // Capture run_id when it appears
        if (progress.runId != null) {
          _runId = progress.runId;
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
        notifyListeners();
      },
    );
  }

  /// Stop evolution process
  void stopEvolution() {
    if (_isRunning) {
      _pythonBridge.stop();
      _isRunning = false;
      _error = 'Evolution stopped by user';
      notifyListeners();
    }
  }

  /// Reset state for new run
  void reset() {
    _isRunning = false;
    _isCompleted = false;
    _error = null;
    _runId = null;
    _outputLines.clear();
    _fitnessHistory.clear();
    _lastRecordedGeneration = -1;
    _pendingGeneChanges = [];
    _progress = EvolutionProgress();
    _pythonBridge.clearOutput();
    notifyListeners();
  }

  @override
  void dispose() {
    _pythonBridge.stop();
    super.dispose();
  }
}
