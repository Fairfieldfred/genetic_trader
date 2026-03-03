import 'package:flutter/foundation.dart';
import '../models/config_model.dart';
import 'dart:io';

/// ViewModel for managing genetic algorithm configuration
class ConfigViewModel extends ChangeNotifier {
  GeneticConfig _config = GeneticConfig();

  GeneticConfig get config => _config;

  // Portfolio Settings
  void updateUsePortfolio(bool value) {
    _config = _config.copyWith(usePortfolio: value);
    notifyListeners();
  }

  void updatePortfolioSize(int size) {
    _config = _config.copyWith(portfolioSize: size);
    notifyListeners();
  }

  void updateInitialAllocation(double pct) {
    _config = _config.copyWith(initialAllocationPct: pct);
    notifyListeners();
  }

  void updateAutoSelectPortfolio(bool value) {
    _config = _config.copyWith(autoSelectPortfolio: value);
    notifyListeners();
  }

  void updatePortfolioStocks(List<String> stocks) {
    _config = _config.copyWith(portfolioStocks: stocks);
    notifyListeners();
  }

  // Date Range
  void updateTrainStartDate(String date) {
    _config = _config.copyWith(trainStartDate: date);
    notifyListeners();
  }

  void updateTrainEndDate(String date) {
    _config = _config.copyWith(trainEndDate: date);
    notifyListeners();
  }

  // Genetic Algorithm Parameters
  void updatePopulationSize(int size) {
    _config = _config.copyWith(populationSize: size);
    notifyListeners();
  }

  void updateNumGenerations(int gens) {
    _config = _config.copyWith(numGenerations: gens);
    notifyListeners();
  }

  void updateMutationRate(double rate) {
    _config = _config.copyWith(mutationRate: rate);
    notifyListeners();
  }

  void updateCrossoverRate(double rate) {
    _config = _config.copyWith(crossoverRate: rate);
    notifyListeners();
  }

  void updateElitismPct(double pct) {
    _config = _config.copyWith(elitismPct: pct);
    notifyListeners();
  }

  // Backtrader Settings
  void updateInitialCash(double cash) {
    _config = _config.copyWith(initialCash: cash);
    notifyListeners();
  }

  void updateCommission(double commission) {
    _config = _config.copyWith(commission: commission);
    notifyListeners();
  }

  // Fitness Weights
  void updateFitnessWeight(String key, double value) {
    final weights = Map<String, double>.from(_config.fitnessWeights);
    weights[key] = value;

    // Normalize to sum to 1.0
    final total = weights.values.reduce((a, b) => a + b);
    if (total > 0) {
      weights.updateAll((k, v) => v / total);
    }

    _config = _config.copyWith(fitnessWeights: weights);
    notifyListeners();
  }

  // Performance Settings
  void updateUseParallelEvaluation(bool value) {
    _config = _config.copyWith(useParallelEvaluation: value);
    notifyListeners();
  }

  void updateMaxParallelWorkers(int? workers) {
    _config = _config.copyWith(maxParallelWorkers: workers);
    notifyListeners();
  }

  // Random Seed
  void updateRandomSeed(int? seed) {
    _config = _config.copyWith(randomSeed: seed);
    notifyListeners();
  }

  // Macroeconomic Context
  void updateUseMacroData(bool value) {
    _config = _config.copyWith(useMacroData: value);
    notifyListeners();
  }

  // Technical Indicator Filters
  void updateUseTechnicalIndicators(bool value) {
    _config = _config.copyWith(useTechnicalIndicators: value);
    notifyListeners();
  }

  // Ensemble Signals
  void updateUseEnsembleSignals(bool value) {
    _config = _config.copyWith(useEnsembleSignals: value);
    notifyListeners();
  }

  // K-Fold Cross-Validation
  void updateUseKfoldValidation(bool value) {
    _config = _config.copyWith(useKfoldValidation: value);
    notifyListeners();
  }

  void updateKfoldNumFolds(int value) {
    _config = _config.copyWith(kfoldNumFolds: value);
    notifyListeners();
  }

  void updateKfoldFoldYears(int years) {
    _config = _config.copyWith(kfoldFoldYears: years);
    notifyListeners();
  }

  void updateKfoldAllowOverlap(bool value) {
    _config = _config.copyWith(kfoldAllowOverlap: value);
    notifyListeners();
  }

  void updateKfoldWeightRecent(bool value) {
    _config = _config.copyWith(kfoldWeightRecent: value);
    notifyListeners();
  }

  void updateKfoldRecentWeightFactor(double factor) {
    _config = _config.copyWith(kfoldRecentWeightFactor: factor);
    notifyListeners();
  }

  void updateKfoldMinBarsPerFold(int bars) {
    _config = _config.copyWith(kfoldMinBarsPerFold: bars);
    notifyListeners();
  }

  /// Save configuration to config.py file
  Future<void> saveConfig() async {
    try {
      // Use absolute path to the Genetic Trader directory
      const configPath = '/Users/fred/Development/Genetic Trader/config.py';
      final configFile = File(configPath);

      // Write the Python config file
      await configFile.writeAsString(_config.toPythonConfig());

      if (kDebugMode) {
        print('✓ Config saved to $configPath');
      }
    } catch (e) {
      if (kDebugMode) {
        print('✗ Error saving config: $e');
      }
      rethrow;
    }
  }

  /// Load configuration from config.py file
  Future<void> loadConfig() async {
    try {
      // TODO: Parse existing config.py file
      // For now, just use defaults
      _config = GeneticConfig();
      notifyListeners();

      if (kDebugMode) {
        print('✓ Config loaded (defaults)');
      }
    } catch (e) {
      if (kDebugMode) {
        print('✗ Error loading config: $e');
      }
      rethrow;
    }
  }

  /// Reset configuration to defaults
  void resetToDefaults() {
    _config = GeneticConfig();
    notifyListeners();
  }
}
