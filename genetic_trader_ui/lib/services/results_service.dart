import 'dart:io';
import '../models/evolution_result.dart';

/// Service for loading evolution results from the results directory
class ResultsService {
  static const _resultsDir = '/Users/fred/Development/Genetic Trader/results';

  /// Load all evolution results, sorted by date descending
  Future<List<EvolutionResult>> loadAllResults() async {
    final dir = Directory(_resultsDir);
    if (!await dir.exists()) return [];

    final results = <EvolutionResult>[];
    final files = await dir
        .list()
        .where(
          (entity) =>
              entity is File &&
              entity.path.contains('summary_') &&
              entity.path.endsWith('.json'),
        )
        .cast<File>()
        .toList();

    for (final file in files) {
      final result = await EvolutionResult.loadFromFile(file);
      if (result != null) {
        results.add(result);
      }
    }

    // Sort by date descending (newest first)
    results.sort((a, b) => b.runDate.compareTo(a.runDate));
    return results;
  }

  /// Load fitness history CSV for a specific run
  Future<List<FitnessHistoryEntry>> loadHistory(String runId) async {
    final file = File('$_resultsDir/history_$runId.csv');
    if (!await file.exists()) return [];

    final content = await file.readAsString();
    return FitnessHistoryEntry.fromCsvContent(content);
  }

  /// Delete all files for a specific run
  Future<void> deleteResult(String runId) async {
    final suffixes = [
      'summary_$runId.json',
      'history_$runId.csv',
      'best_trader_$runId.json',
      'evolution_$runId.png',
    ];

    for (final suffix in suffixes) {
      final file = File('$_resultsDir/$suffix');
      if (await file.exists()) {
        await file.delete();
      }
    }
  }

  /// Find the most recent run_id from the results directory
  Future<String?> findMostRecentRunId() async {
    final results = await loadAllResults();
    if (results.isEmpty) return null;
    return results.first.runId;
  }

  /// Load a single result by run_id
  Future<EvolutionResult?> loadResult(String runId) async {
    final file = File('$_resultsDir/summary_$runId.json');
    return EvolutionResult.loadFromFile(file);
  }
}
