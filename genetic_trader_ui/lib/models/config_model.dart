/// Configuration model representing config.py parameters
class GeneticConfig {
  // Database configuration
  String databasePath;
  String testSymbol;

  // Portfolio configuration
  bool usePortfolio;
  int portfolioSize;
  List<String> portfolioStocks;
  bool autoSelectPortfolio;
  List<String> portfolioSectors;
  double initialAllocationPct;

  // Date range
  String trainStartDate;
  String trainEndDate;
  String testStartDate;
  String testEndDate;

  // Genetic algorithm parameters
  int populationSize;
  int numGenerations;
  double mutationRate;
  double crossoverRate;
  double elitismPct;  // Percentage of population to preserve as elite
  int tournamentSize;

  // Gene definitions
  Map<String, GeneDefinition> geneDefinitions;

  // Backtrader configuration
  double initialCash;
  double commission;

  // Fitness weights
  Map<String, double> fitnessWeights;

  // Minimum trades
  int minTradesRequired;

  // Backtesting configuration
  String backtestingEngine;
  String dataSource;

  // Performance settings
  bool useParallelEvaluation;
  int? maxParallelWorkers;

  // Random seed
  int? randomSeed;

  // Macroeconomic context
  bool useMacroData;

  // Technical indicator filters
  bool useTechnicalIndicators;

  // Ensemble signals
  bool useEnsembleSignals;

  // Out-of-sample testing
  bool useOutOfSampleTest;
  int trainingYears;

  // K-Fold cross-validation
  bool useKfoldValidation;
  int kfoldNumFolds;
  int kfoldFoldYears;
  bool kfoldAllowOverlap;
  bool kfoldWeightRecent;
  double kfoldRecentWeightFactor;
  int kfoldMinBarsPerFold;

  GeneticConfig({
    this.databasePath =
        '/Users/macmini/Dev/Genetic Trader/SPY_Data.db',
    this.testSymbol = 'AAPL',
    this.usePortfolio = true,
    this.portfolioSize = 20,
    this.portfolioStocks = const [],
    this.autoSelectPortfolio = true,  // Auto-select random stocks by default
    this.portfolioSectors = const [],
    this.initialAllocationPct = 80.0,
    this.trainStartDate = '2016-03-09',
    this.trainEndDate = '2024-03-09',
    this.testStartDate = '2024-03-10',
    this.testEndDate = '2026-03-06',
    this.populationSize = 30,
    this.numGenerations = 40,
    this.mutationRate = 0.2,
    this.crossoverRate = 0.9,
    this.elitismPct = 20.0,  // 20% of population
    this.tournamentSize = 4,
    this.geneDefinitions = const {},
    this.initialCash = 100000.0,
    this.commission = 0.001,
    this.fitnessWeights = const {
      'total_return': 0.40,
      'sharpe_ratio': 0.24,
      'max_drawdown': 0.24,
      'win_rate': 0.12,
    },
    this.minTradesRequired = 5,
    this.backtestingEngine = 'backtrader',
    this.dataSource = 'sqlite',
    this.useParallelEvaluation = true,
    this.maxParallelWorkers,
    this.randomSeed = 42,
    this.useMacroData = false,
    this.useTechnicalIndicators = false,
    this.useEnsembleSignals = false,
    this.useOutOfSampleTest = true,
    this.trainingYears = 8,
    this.useKfoldValidation = false,
    this.kfoldNumFolds = 2,
    this.kfoldFoldYears = 3,
    this.kfoldAllowOverlap = false,
    this.kfoldWeightRecent = false,
    this.kfoldRecentWeightFactor = 1.5,
    this.kfoldMinBarsPerFold = 200,
  });

  /// Create config from JSON
  factory GeneticConfig.fromJson(Map<String, dynamic> json) {
    return GeneticConfig(
      databasePath: json['DATABASE_PATH'] ?? 'spy.db',
      testSymbol: json['TEST_SYMBOL'] ?? 'AAPL',
      usePortfolio: json['USE_PORTFOLIO'] ?? true,
      portfolioSize: json['PORTFOLIO_SIZE'] ?? 20,
      portfolioStocks: List<String>.from(json['PORTFOLIO_STOCKS'] ?? []),
      autoSelectPortfolio: json['AUTO_SELECT_PORTFOLIO'] ?? true,
      portfolioSectors: List<String>.from(
        json['PORTFOLIO_SECTORS'] ?? [],
      ),
      initialAllocationPct: (json['INITIAL_ALLOCATION_PCT'] ?? 80.0).toDouble(),
      trainStartDate: json['TRAIN_START_DATE'] ?? '2012-01-01',
      trainEndDate: json['TRAIN_END_DATE'] ?? '2020-12-31',
      testStartDate: json['TEST_START_DATE'] ?? '2021-01-01',
      testEndDate: json['TEST_END_DATE'] ?? '2023-12-31',
      populationSize: json['POPULATION_SIZE'] ?? 30,
      numGenerations: json['NUM_GENERATIONS'] ?? 40,
      mutationRate: (json['MUTATION_RATE'] ?? 0.2).toDouble(),
      crossoverRate: (json['CROSSOVER_RATE'] ?? 0.9).toDouble(),
      elitismPct: (json['ELITISM_PCT'] ?? 20.0).toDouble(),
      tournamentSize: json['TOURNAMENT_SIZE'] ?? 4,
      initialCash: (json['INITIAL_CASH'] ?? 100000.0).toDouble(),
      commission: (json['COMMISSION'] ?? 0.001).toDouble(),
      fitnessWeights: Map<String, double>.from(json['FITNESS_WEIGHTS'] ?? {}),
      minTradesRequired: json['MIN_TRADES_REQUIRED'] ?? 5,
      backtestingEngine: json['BACKTESTING_ENGINE'] ?? 'backtrader',
      dataSource: json['DATA_SOURCE'] ?? 'sqlite',
      useParallelEvaluation: json['USE_PARALLEL_EVALUATION'] ?? true,
      maxParallelWorkers: json['MAX_PARALLEL_WORKERS'],
      randomSeed: json['RANDOM_SEED'],
      useMacroData: json['USE_MACRO_DATA'] ?? false,
      useTechnicalIndicators: json['USE_TECHNICAL_INDICATORS'] ?? false,
      useEnsembleSignals: json['USE_ENSEMBLE_SIGNALS'] ?? false,
      useOutOfSampleTest: json['USE_OUT_OF_SAMPLE_TEST'] ?? true,
      trainingYears: json['TRAINING_YEARS'] ?? 8,
      useKfoldValidation: json['USE_KFOLD_VALIDATION'] ?? false,
      kfoldNumFolds: json['KFOLD_NUM_FOLDS'] ?? 2,
      kfoldFoldYears: json['KFOLD_FOLD_YEARS'] ?? 3,
      kfoldAllowOverlap: json['KFOLD_ALLOW_OVERLAP'] ?? false,
      kfoldWeightRecent: json['KFOLD_WEIGHT_RECENT'] ?? false,
      kfoldRecentWeightFactor:
          (json['KFOLD_RECENT_WEIGHT_FACTOR'] ?? 1.5).toDouble(),
      kfoldMinBarsPerFold: json['KFOLD_MIN_BARS_PER_FOLD'] ?? 200,
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'DATABASE_PATH': databasePath,
      'TEST_SYMBOL': testSymbol,
      'USE_PORTFOLIO': usePortfolio,
      'PORTFOLIO_SIZE': portfolioSize,
      'PORTFOLIO_STOCKS': portfolioStocks,
      'AUTO_SELECT_PORTFOLIO': autoSelectPortfolio,
      'PORTFOLIO_SECTORS': portfolioSectors,
      'INITIAL_ALLOCATION_PCT': initialAllocationPct,
      'TRAIN_START_DATE': trainStartDate,
      'TRAIN_END_DATE': trainEndDate,
      'TEST_START_DATE': testStartDate,
      'TEST_END_DATE': testEndDate,
      'POPULATION_SIZE': populationSize,
      'NUM_GENERATIONS': numGenerations,
      'MUTATION_RATE': mutationRate,
      'CROSSOVER_RATE': crossoverRate,
      'ELITISM_PCT': elitismPct,
      'TOURNAMENT_SIZE': tournamentSize,
      'INITIAL_CASH': initialCash,
      'COMMISSION': commission,
      'FITNESS_WEIGHTS': fitnessWeights,
      'MIN_TRADES_REQUIRED': minTradesRequired,
      'BACKTESTING_ENGINE': backtestingEngine,
      'DATA_SOURCE': dataSource,
      'USE_PARALLEL_EVALUATION': useParallelEvaluation,
      'MAX_PARALLEL_WORKERS': maxParallelWorkers,
      'RANDOM_SEED': randomSeed,
      'USE_MACRO_DATA': useMacroData,
      'USE_TECHNICAL_INDICATORS': useTechnicalIndicators,
      'USE_ENSEMBLE_SIGNALS': useEnsembleSignals,
      'USE_OUT_OF_SAMPLE_TEST': useOutOfSampleTest,
      'TRAINING_YEARS': trainingYears,
      'USE_KFOLD_VALIDATION': useKfoldValidation,
      'KFOLD_NUM_FOLDS': kfoldNumFolds,
      'KFOLD_FOLD_YEARS': kfoldFoldYears,
      'KFOLD_ALLOW_OVERLAP': kfoldAllowOverlap,
      'KFOLD_WEIGHT_RECENT': kfoldWeightRecent,
      'KFOLD_RECENT_WEIGHT_FACTOR': kfoldRecentWeightFactor,
      'KFOLD_MIN_BARS_PER_FOLD': kfoldMinBarsPerFold,
    };
  }

  /// Helper to convert Dart boolean to Python boolean
  String _toPythonBool(bool value) {
    return value ? 'True' : 'False';
  }

  /// Helper to convert nullable int to Python (None or number)
  String _toPythonNullableInt(int? value) {
    return value == null ? 'None' : value.toString();
  }

  /// Convert to Python config.py format
  String toPythonConfig() {
    final buffer = StringBuffer();

    buffer.writeln('"""');
    buffer.writeln('Configuration file for genetic trading algorithm.');
    buffer.writeln('Auto-generated from Flutter UI.');
    buffer.writeln('"""');
    buffer.writeln();

    buffer.writeln('# Database configuration');
    buffer.writeln('DATABASE_PATH = "$databasePath"');
    buffer.writeln('TEST_SYMBOL = "$testSymbol"');
    buffer.writeln();

    buffer.writeln('# Multi-stock portfolio configuration');
    buffer.writeln('USE_PORTFOLIO = ${_toPythonBool(usePortfolio)}');
    buffer.writeln('PORTFOLIO_SIZE = $portfolioSize');
    buffer.writeln('PORTFOLIO_STOCKS = [');
    for (var stock in portfolioStocks) {
      buffer.writeln('    "$stock",');
    }
    buffer.writeln(']');
    buffer.writeln('AUTO_SELECT_PORTFOLIO = ${_toPythonBool(autoSelectPortfolio)}');
    buffer.writeln('PORTFOLIO_SECTORS = [');
    for (var sector in portfolioSectors) {
      buffer.writeln('    "$sector",');
    }
    buffer.writeln(']');
    buffer.writeln();

    // Compute train/test split from trainingYears
    final dataStart = DateTime.tryParse(trainStartDate);
    final dataEnd = DateTime.tryParse(testEndDate);
    String computedTrainEnd = trainEndDate;
    String computedTestStart = testStartDate;
    if (dataStart != null && dataEnd != null && useOutOfSampleTest) {
      final splitDate = DateTime(
        dataStart.year + trainingYears,
        dataStart.month,
        dataStart.day,
      );
      computedTrainEnd =
          '${splitDate.year}-${splitDate.month.toString().padLeft(2, '0')}'
          '-${splitDate.day.toString().padLeft(2, '0')}';
      final testDate = splitDate.add(const Duration(days: 1));
      computedTestStart =
          '${testDate.year}-${testDate.month.toString().padLeft(2, '0')}'
          '-${testDate.day.toString().padLeft(2, '0')}';
    } else if (!useOutOfSampleTest && dataEnd != null) {
      // Use full date range for training when OOS is disabled
      computedTrainEnd = testEndDate;
      computedTestStart = testEndDate;
    }

    buffer.writeln('# Data split configuration');
    buffer.writeln('TRAIN_START_DATE = "$trainStartDate"');
    buffer.writeln('TRAIN_END_DATE = "$computedTrainEnd"');
    buffer.writeln('TEST_START_DATE = "$computedTestStart"');
    buffer.writeln('TEST_END_DATE = "$testEndDate"');
    buffer.writeln(
        'USE_OUT_OF_SAMPLE_TEST = ${_toPythonBool(useOutOfSampleTest)}');
    buffer.writeln('TRAINING_YEARS = $trainingYears');
    buffer.writeln();

    buffer.writeln('# K-Fold Temporal Cross-Validation');
    buffer.writeln(
        'USE_KFOLD_VALIDATION = ${_toPythonBool(useKfoldValidation)}');
    buffer.writeln('KFOLD_NUM_FOLDS = $kfoldNumFolds');
    buffer.writeln('KFOLD_FOLD_YEARS = $kfoldFoldYears');
    buffer.writeln(
        'KFOLD_ALLOW_OVERLAP = ${_toPythonBool(kfoldAllowOverlap)}');
    buffer.writeln(
        'KFOLD_WEIGHT_RECENT = ${_toPythonBool(kfoldWeightRecent)}');
    buffer.writeln(
        'KFOLD_RECENT_WEIGHT_FACTOR = $kfoldRecentWeightFactor');
    buffer.writeln('KFOLD_MIN_BARS_PER_FOLD = $kfoldMinBarsPerFold');
    buffer.writeln();

    buffer.writeln('# Genetic algorithm configuration');
    buffer.writeln('POPULATION_SIZE = $populationSize');
    buffer.writeln('NUM_GENERATIONS = $numGenerations');
    buffer.writeln('MUTATION_RATE = $mutationRate');
    buffer.writeln('CROSSOVER_RATE = $crossoverRate');

    // Calculate elitism count from percentage (round up)
    final elitismCount = (populationSize * elitismPct / 100).ceil();
    buffer.writeln('ELITISM_COUNT = $elitismCount  # ${elitismPct.toStringAsFixed(1)}% of population');
    buffer.writeln();

    buffer.writeln('# Tournament selection');
    buffer.writeln('TOURNAMENT_SIZE = $tournamentSize');
    buffer.writeln();

    buffer.writeln('# Gene definitions and bounds');
    buffer.writeln('# Each gene is defined as: (min_value, max_value, data_type)');
    buffer.writeln('GENE_DEFINITIONS = {');
    buffer.writeln('    # Moving Average Strategy genes');
    buffer.writeln('    \'ma_short_period\': (5, 30, int),      # Short MA period (fast signal)');
    buffer.writeln('    \'ma_long_period\': (30, 100, int),     # Long MA period (slow signal)');
    buffer.writeln('    \'ma_type\': (0, 1, int),                # 0 = SMA, 1 = EMA');
    buffer.writeln();
    buffer.writeln('    # Risk Management genes');
    buffer.writeln('    \'stop_loss_pct\': (1.0, 10.0, float),');
    buffer.writeln('    \'take_profit_pct\': (2.0, 15.0, float),');
    buffer.writeln('    \'position_size_pct\': (5.0, 25.0, float),');

    if (useMacroData) {
      buffer.writeln();
      buffer.writeln('    # Macroeconomic Context genes');
      buffer.writeln(
          '    \'macro_enabled\': (0, 1, int),');
      buffer.writeln(
          '    \'macro_weight\': (0.0, 1.0, float),');
      buffer.writeln(
          '    \'macro_vix_threshold\': (15.0, 50.0, float),');
      buffer.writeln(
          '    \'macro_vix_position_scale\': (0.2, 1.0, float),');
      buffer.writeln(
          '    \'macro_yc_threshold\': (-1.0, 1.0, float),');
      buffer.writeln(
          '    \'macro_yc_action\': (0, 2, int),');
      buffer.writeln(
          '    \'macro_rate_threshold\': (1.0, 8.0, float),');
      buffer.writeln(
          '    \'macro_rate_position_scale\': (0.3, 1.0, float),');
      buffer.writeln(
          '    \'macro_cpi_threshold\': (2.0, 8.0, float),');
      buffer.writeln(
          '    \'macro_cpi_position_scale\': (0.3, 1.0, float),');
      buffer.writeln(
          '    \'macro_unemp_threshold\': (4.0, 10.0, float),');
      buffer.writeln(
          '    \'macro_unemp_action\': (0, 2, int),');
      buffer.writeln(
          '    \'macro_risk_stop_adj\': (0.5, 2.0, float),');
      buffer.writeln(
          '    \'macro_risk_tp_adj\': (0.5, 2.0, float),');
      buffer.writeln(
          '    \'macro_regime_count_req\': (1, 4, int),');
    }

    if (useTechnicalIndicators) {
      buffer.writeln();
      buffer.writeln('    # Technical Indicator filter genes');
      buffer.writeln(
          '    \'ti_enabled\': (0, 1, int),');
      buffer.writeln(
          '    \'ti_weight\': (0.0, 1.0, float),');
      buffer.writeln(
          '    \'ti_rsi_overbought\': (60, 90, int),');
      buffer.writeln(
          '    \'ti_rsi_oversold\': (10, 40, int),');
      buffer.writeln(
          '    \'ti_adx_threshold\': (15, 40, int),');
      buffer.writeln(
          '    \'ti_adx_position_scale\': (0.2, 1.0, float),');
      buffer.writeln(
          '    \'ti_natr_threshold\': (2.0, 8.0, float),');
      buffer.writeln(
          '    \'ti_natr_risk_action\': (0, 2, int),');
      buffer.writeln(
          '    \'ti_mfi_overbought\': (70, 95, int),');
      buffer.writeln(
          '    \'ti_mfi_oversold\': (5, 30, int),');
      buffer.writeln(
          '    \'ti_macdhist_confirm\': (0, 1, int),');
      buffer.writeln(
          '    \'ti_macdhist_exit_confirm\': (0, 1, int),');
    }

    if (useEnsembleSignals) {
      buffer.writeln();
      buffer.writeln('    # Ensemble Signal genes');
      buffer.writeln(
          '    \'ensemble_enabled\': (0, 1, int),');
      buffer.writeln(
          '    \'sig_ma_weight\': (0.0, 1.0, float),');
      buffer.writeln(
          '    \'sig_bb_weight\': (0.0, 1.0, float),');
      buffer.writeln(
          '    \'sig_stoch_weight\': (0.0, 1.0, float),');
      buffer.writeln(
          '    \'sig_macd_weight\': (0.0, 1.0, float),');
      buffer.writeln(
          '    \'sig_rsi_weight\': (0.0, 1.0, float),');
      buffer.writeln(
          '    \'sig_buy_threshold\': (0.1, 0.8, float),');
      buffer.writeln(
          '    \'sig_sell_threshold\': (-0.8, -0.1, float),');
      buffer.writeln(
          '    \'sig_bb_period_idx\': (0, 2, int),');
      buffer.writeln(
          '    \'sig_stoch_ob\': (70, 90, int),');
      buffer.writeln(
          '    \'sig_stoch_os\': (10, 30, int),');
      buffer.writeln(
          '    \'sig_rsi_ob\': (60, 85, int),');
      buffer.writeln(
          '    \'sig_rsi_os\': (15, 40, int),');
    }

    buffer.writeln('}');
    buffer.writeln();

    buffer.writeln('# Gene order in chromosome (important for consistency)');
    buffer.writeln('GENE_ORDER = [');
    buffer.writeln('    \'ma_short_period\',');
    buffer.writeln('    \'ma_long_period\',');
    buffer.writeln('    \'ma_type\',');
    buffer.writeln('    \'stop_loss_pct\',');
    buffer.writeln('    \'take_profit_pct\',');
    buffer.writeln('    \'position_size_pct\',');

    if (useMacroData) {
      buffer.writeln('    \'macro_enabled\',');
      buffer.writeln('    \'macro_weight\',');
      buffer.writeln('    \'macro_vix_threshold\',');
      buffer.writeln('    \'macro_vix_position_scale\',');
      buffer.writeln('    \'macro_yc_threshold\',');
      buffer.writeln('    \'macro_yc_action\',');
      buffer.writeln('    \'macro_rate_threshold\',');
      buffer.writeln('    \'macro_rate_position_scale\',');
      buffer.writeln('    \'macro_cpi_threshold\',');
      buffer.writeln('    \'macro_cpi_position_scale\',');
      buffer.writeln('    \'macro_unemp_threshold\',');
      buffer.writeln('    \'macro_unemp_action\',');
      buffer.writeln('    \'macro_risk_stop_adj\',');
      buffer.writeln('    \'macro_risk_tp_adj\',');
      buffer.writeln('    \'macro_regime_count_req\',');
    }

    if (useTechnicalIndicators) {
      buffer.writeln('    \'ti_enabled\',');
      buffer.writeln('    \'ti_weight\',');
      buffer.writeln('    \'ti_rsi_overbought\',');
      buffer.writeln('    \'ti_rsi_oversold\',');
      buffer.writeln('    \'ti_adx_threshold\',');
      buffer.writeln('    \'ti_adx_position_scale\',');
      buffer.writeln('    \'ti_natr_threshold\',');
      buffer.writeln('    \'ti_natr_risk_action\',');
      buffer.writeln('    \'ti_mfi_overbought\',');
      buffer.writeln('    \'ti_mfi_oversold\',');
      buffer.writeln('    \'ti_macdhist_confirm\',');
      buffer.writeln('    \'ti_macdhist_exit_confirm\',');
    }

    if (useEnsembleSignals) {
      buffer.writeln('    \'ensemble_enabled\',');
      buffer.writeln('    \'sig_ma_weight\',');
      buffer.writeln('    \'sig_bb_weight\',');
      buffer.writeln('    \'sig_stoch_weight\',');
      buffer.writeln('    \'sig_macd_weight\',');
      buffer.writeln('    \'sig_rsi_weight\',');
      buffer.writeln('    \'sig_buy_threshold\',');
      buffer.writeln('    \'sig_sell_threshold\',');
      buffer.writeln('    \'sig_bb_period_idx\',');
      buffer.writeln('    \'sig_stoch_ob\',');
      buffer.writeln('    \'sig_stoch_os\',');
      buffer.writeln('    \'sig_rsi_ob\',');
      buffer.writeln('    \'sig_rsi_os\',');
    }

    buffer.writeln(']');
    buffer.writeln();

    buffer.writeln('# Macroeconomic data configuration');
    buffer.writeln(
        'USE_MACRO_DATA = ${_toPythonBool(useMacroData)}');
    buffer.writeln("MACRO_DATA_TABLE = 'macro_indicators'");
    buffer.writeln();

    buffer.writeln('# Technical indicator filter configuration');
    buffer.writeln(
        'USE_TECHNICAL_INDICATORS = ${_toPythonBool(useTechnicalIndicators)}');
    buffer.writeln();

    buffer.writeln('# Ensemble signal configuration');
    buffer.writeln(
        'USE_ENSEMBLE_SIGNALS = ${_toPythonBool(useEnsembleSignals)}');
    buffer.writeln();

    buffer.writeln('# Backtesting configuration');
    buffer.writeln("BACKTESTING_ENGINE = '$backtestingEngine'");
    buffer.writeln("DATA_SOURCE = '$dataSource'");
    buffer.writeln('INITIAL_CASH = $initialCash');
    buffer.writeln('COMMISSION = $commission  # 0.1% commission per trade');
    buffer.writeln();

    buffer.writeln('# Portfolio initial allocation (only applies when USE_PORTFOLIO = True)');
    buffer.writeln('# Percentage of capital to allocate equally across all stocks at start');
    buffer.writeln('# Remaining percentage stays as cash for strategy signals');
    buffer.writeln('# Example: 80.0 means 80% divided equally among stocks, 20% reserved for trading');
    buffer.writeln('INITIAL_ALLOCATION_PCT = $initialAllocationPct  # Range: 0.0 to 100.0');
    buffer.writeln();

    buffer.writeln('# Fitness function weights');
    buffer.writeln('FITNESS_WEIGHTS = {');
    fitnessWeights.forEach((key, value) {
      buffer.writeln('    \'$key\': $value,');
    });
    buffer.writeln('}');
    buffer.writeln();

    buffer.writeln('# Minimum trades required for valid fitness');
    buffer.writeln('MIN_TRADES_REQUIRED = $minTradesRequired');
    buffer.writeln();

    buffer.writeln('# Logging configuration');
    buffer.writeln('LOG_LEVEL = "INFO"');
    buffer.writeln('LOG_EVERY_N_GENERATIONS = 1');
    buffer.writeln('SAVE_BEST_EVERY_N_GENERATIONS = 10');
    buffer.writeln();

    buffer.writeln('# Output paths');
    buffer.writeln('RESULTS_DIR = "results"');
    buffer.writeln('LOGS_DIR = "logs"');
    buffer.writeln('CHECKPOINT_DIR = "checkpoints"');
    buffer.writeln();

    buffer.writeln('# Random seed for reproducibility (set to None for random)');
    buffer.writeln('RANDOM_SEED = ${_toPythonNullableInt(randomSeed)}');
    buffer.writeln();

    buffer.writeln('# Performance optimization');
    buffer.writeln('USE_PARALLEL_EVALUATION = ${_toPythonBool(useParallelEvaluation)}  # Use multiprocessing for fitness evaluation');
    buffer.writeln('MAX_PARALLEL_WORKERS = ${_toPythonNullableInt(maxParallelWorkers)}     # None = use all CPU cores, or specify number');

    return buffer.toString();
  }

  /// Create a copy with modified fields
  GeneticConfig copyWith({
    String? databasePath,
    String? testSymbol,
    bool? usePortfolio,
    int? portfolioSize,
    List<String>? portfolioStocks,
    bool? autoSelectPortfolio,
    List<String>? portfolioSectors,
    double? initialAllocationPct,
    String? trainStartDate,
    String? trainEndDate,
    String? testStartDate,
    String? testEndDate,
    int? populationSize,
    int? numGenerations,
    double? mutationRate,
    double? crossoverRate,
    double? elitismPct,
    int? tournamentSize,
    double? initialCash,
    double? commission,
    Map<String, double>? fitnessWeights,
    int? minTradesRequired,
    String? backtestingEngine,
    String? dataSource,
    bool? useParallelEvaluation,
    int? maxParallelWorkers,
    int? randomSeed,
    bool? useMacroData,
    bool? useTechnicalIndicators,
    bool? useEnsembleSignals,
    bool? useOutOfSampleTest,
    int? trainingYears,
    bool? useKfoldValidation,
    int? kfoldNumFolds,
    int? kfoldFoldYears,
    bool? kfoldAllowOverlap,
    bool? kfoldWeightRecent,
    double? kfoldRecentWeightFactor,
    int? kfoldMinBarsPerFold,
  }) {
    return GeneticConfig(
      databasePath: databasePath ?? this.databasePath,
      testSymbol: testSymbol ?? this.testSymbol,
      usePortfolio: usePortfolio ?? this.usePortfolio,
      portfolioSize: portfolioSize ?? this.portfolioSize,
      portfolioStocks: portfolioStocks ?? this.portfolioStocks,
      autoSelectPortfolio: autoSelectPortfolio ?? this.autoSelectPortfolio,
      portfolioSectors: portfolioSectors ?? this.portfolioSectors,
      initialAllocationPct: initialAllocationPct ?? this.initialAllocationPct,
      trainStartDate: trainStartDate ?? this.trainStartDate,
      trainEndDate: trainEndDate ?? this.trainEndDate,
      testStartDate: testStartDate ?? this.testStartDate,
      testEndDate: testEndDate ?? this.testEndDate,
      populationSize: populationSize ?? this.populationSize,
      numGenerations: numGenerations ?? this.numGenerations,
      mutationRate: mutationRate ?? this.mutationRate,
      crossoverRate: crossoverRate ?? this.crossoverRate,
      elitismPct: elitismPct ?? this.elitismPct,
      tournamentSize: tournamentSize ?? this.tournamentSize,
      initialCash: initialCash ?? this.initialCash,
      commission: commission ?? this.commission,
      fitnessWeights: fitnessWeights ?? this.fitnessWeights,
      minTradesRequired: minTradesRequired ?? this.minTradesRequired,
      backtestingEngine: backtestingEngine ?? this.backtestingEngine,
      dataSource: dataSource ?? this.dataSource,
      useParallelEvaluation:
          useParallelEvaluation ?? this.useParallelEvaluation,
      maxParallelWorkers: maxParallelWorkers ?? this.maxParallelWorkers,
      randomSeed: randomSeed ?? this.randomSeed,
      useMacroData: useMacroData ?? this.useMacroData,
      useTechnicalIndicators:
          useTechnicalIndicators ?? this.useTechnicalIndicators,
      useEnsembleSignals:
          useEnsembleSignals ?? this.useEnsembleSignals,
      useOutOfSampleTest:
          useOutOfSampleTest ?? this.useOutOfSampleTest,
      trainingYears: trainingYears ?? this.trainingYears,
      useKfoldValidation:
          useKfoldValidation ?? this.useKfoldValidation,
      kfoldNumFolds: kfoldNumFolds ?? this.kfoldNumFolds,
      kfoldFoldYears: kfoldFoldYears ?? this.kfoldFoldYears,
      kfoldAllowOverlap:
          kfoldAllowOverlap ?? this.kfoldAllowOverlap,
      kfoldWeightRecent:
          kfoldWeightRecent ?? this.kfoldWeightRecent,
      kfoldRecentWeightFactor:
          kfoldRecentWeightFactor ?? this.kfoldRecentWeightFactor,
      kfoldMinBarsPerFold:
          kfoldMinBarsPerFold ?? this.kfoldMinBarsPerFold,
    );
  }
}

/// Gene definition model
class GeneDefinition {
  final String name;
  final double minValue;
  final double maxValue;
  final GeneType type;

  const GeneDefinition({
    required this.name,
    required this.minValue,
    required this.maxValue,
    required this.type,
  });
}

/// Gene data type
enum GeneType { int, float, bool }
