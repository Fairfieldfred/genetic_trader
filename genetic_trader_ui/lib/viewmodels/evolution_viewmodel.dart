import 'package:flutter/foundation.dart';
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

  // Getters
  bool get isRunning => _isRunning;
  bool get isCompleted => _isCompleted;
  String? get error => _error;
  List<String> get outputLines => List.unmodifiable(_outputLines);
  EvolutionProgress get progress => _progress;

  int get currentGeneration => _progress.currentGeneration ?? 0;
  int get totalGenerations => _progress.totalGenerations ?? 0;
  double get bestFitness => _progress.bestFitness ?? 0.0;
  double get avgFitness => _progress.avgFitness ?? 0.0;
  double get progressPercentage => _progress.progress * 100;

  /// Start evolution process
  Future<void> startEvolution() async {
    if (_isRunning) return;

    // Reset state
    _isRunning = true;
    _isCompleted = false;
    _error = null;
    _outputLines.clear();
    _progress = EvolutionProgress();
    notifyListeners();

    await _pythonBridge.startEvolution(
      onOutput: (line) {
        _outputLines.add(line);

        // Keep only last 1000 lines to prevent memory issues
        if (_outputLines.length > 1000) {
          _outputLines.removeAt(0);
        }

        notifyListeners();
      },
      onProgress: (progress) {
        // Merge progress updates
        _progress = _progress.copyWith(
          currentGeneration: progress.currentGeneration ?? _progress.currentGeneration,
          totalGenerations: progress.totalGenerations ?? _progress.totalGenerations,
          bestFitness: progress.bestFitness ?? _progress.bestFitness,
          avgFitness: progress.avgFitness ?? _progress.avgFitness,
          worstFitness: progress.worstFitness ?? _progress.worstFitness,
        );
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
    _outputLines.clear();
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
