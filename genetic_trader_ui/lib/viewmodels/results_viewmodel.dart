import 'package:flutter/foundation.dart';
import '../models/evolution_result.dart';
import '../services/results_service.dart';

/// ViewModel for browsing and viewing evolution results
class ResultsViewModel extends ChangeNotifier {
  final ResultsService _service = ResultsService();

  List<EvolutionResult> _results = [];
  EvolutionResult? _selectedResult;
  List<FitnessHistoryEntry>? _fitnessHistory;
  bool _isLoading = false;
  String? _error;

  List<EvolutionResult> get results => _results;
  EvolutionResult? get selectedResult => _selectedResult;
  List<FitnessHistoryEntry>? get fitnessHistory => _fitnessHistory;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Load all results from disk
  Future<void> loadResults() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _results = await _service.loadAllResults();
    } catch (e) {
      _error = 'Failed to load results: $e';
    }

    _isLoading = false;
    notifyListeners();
  }

  /// Select a result and load its fitness history
  Future<void> selectResult(EvolutionResult result) async {
    _selectedResult = result;
    _fitnessHistory = null;
    notifyListeners();

    try {
      _fitnessHistory = await _service.loadHistory(result.runId);
    } catch (e) {
      if (kDebugMode) {
        print('Failed to load history for ${result.runId}: $e');
      }
    }
    notifyListeners();
  }

  /// Load a specific result by run_id and select it
  Future<void> loadAndSelectResult(String runId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final result = await _service.loadResult(runId);
      if (result != null) {
        _selectedResult = result;
        _fitnessHistory = await _service.loadHistory(runId);
      } else {
        _error = 'Result not found for run $runId';
      }
    } catch (e) {
      _error = 'Failed to load result: $e';
    }

    _isLoading = false;
    notifyListeners();
  }

  /// Delete a result and refresh the list
  Future<void> deleteResult(String runId) async {
    try {
      await _service.deleteResult(runId);
      _results.removeWhere((r) => r.runId == runId);
      if (_selectedResult?.runId == runId) {
        _selectedResult = null;
        _fitnessHistory = null;
      }
      notifyListeners();
    } catch (e) {
      _error = 'Failed to delete result: $e';
      notifyListeners();
    }
  }
}
