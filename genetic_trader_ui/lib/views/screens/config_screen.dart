import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../viewmodels/config_viewmodel.dart';

/// Configuration screen for editing genetic algorithm parameters
class ConfigScreen extends StatelessWidget {
  const ConfigScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Configuration'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Reset to Defaults',
            onPressed: () {
              _showResetDialog(context);
            },
          ),
          IconButton(
            icon: const Icon(Icons.save),
            tooltip: 'Save Configuration',
            onPressed: () async {
              try {
                await context.read<ConfigViewModel>().saveConfig();
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Configuration saved successfully!'),
                      backgroundColor: Colors.green,
                    ),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Error saving configuration: $e'),
                      backgroundColor: Colors.red,
                    ),
                  );
                }
              }
            },
          ),
        ],
      ),
      body: Consumer<ConfigViewModel>(
        builder: (context, viewModel, child) {
          final config = viewModel.config;

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Database Selection
              _buildSection(
                context,
                title: 'Database',
                icon: Icons.storage,
                subtitle: config.databasePath,
                children: [
                  _DatabaseSelector(
                    currentPath: config.databasePath,
                    onChanged: viewModel.updateDatabasePath,
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Train / Test Split
              _buildSection(
                context,
                title: 'Train / Test Split',
                icon: Icons.call_split,
                children: [
                  SwitchListTile(
                    title: const Text('Out-of-Sample Testing'),
                    subtitle: Text(
                      config.useOutOfSampleTest
                          ? 'Train on ${config.trainingYears} years, '
                              'test on remaining data'
                          : 'Use full date range for training',
                    ),
                    value: config.useOutOfSampleTest,
                    onChanged: (value) {
                      viewModel.updateUseOutOfSampleTest(value);
                    },
                  ),
                  if (config.useOutOfSampleTest) ...[
                    _buildSliderTile(
                      context,
                      title: 'Training Years',
                      subtitle:
                          'Test period uses the remaining data',
                      value: config.trainingYears.toDouble(),
                      min: 1,
                      max: 9,
                      divisions: 8,
                      label: '${config.trainingYears} years',
                      onChanged: (value) {
                        viewModel.updateTrainingYears(
                          value.toInt(),
                        );
                      },
                    ),
                    _TrainTestDateDisplay(
                      trainStartDate: config.trainStartDate,
                      testEndDate: config.testEndDate,
                      trainingYears: config.trainingYears,
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 8),

              // Portfolio Settings
              _buildSection(
                context,
                title: 'Portfolio Settings',
                icon: Icons.account_balance_wallet,
                children: [
                  SwitchListTile(
                    title: const Text('Auto-Select Stocks'),
                    subtitle: Text(
                      config.autoSelectPortfolio
                          ? 'Randomly select stocks from '
                              'database'
                          : 'Specify stocks manually',
                    ),
                    value: config.autoSelectPortfolio,
                    onChanged: (value) {
                      viewModel.updateAutoSelectPortfolio(
                        value,
                      );
                    },
                  ),
                  if (config.autoSelectPortfolio)
                    _buildSliderTile(
                      context,
                      title: 'Portfolio Size',
                      value: config.portfolioSize.toDouble(),
                      min: 1,
                      max: 50,
                      divisions: 49,
                      label: '${config.portfolioSize} stocks',
                      onChanged: (value) {
                        viewModel.updatePortfolioSize(
                          value.toInt(),
                        );
                      },
                    ),
                  if (config.autoSelectPortfolio)
                    _SectorFilterChips(
                      selectedSectors: config.portfolioSectors,
                      onToggle: viewModel.togglePortfolioSector,
                      onClearAll: () {
                        viewModel.updatePortfolioSectors([]);
                      },
                    ),
                  if (!config.autoSelectPortfolio)
                    _StockInputField(
                      stocks: config.portfolioStocks,
                      onChanged: (stocks) {
                        viewModel.updatePortfolioStocks(stocks);
                        viewModel.updatePortfolioSize(
                          stocks.isEmpty ? 1 : stocks.length,
                        );
                      },
                    ),
                  _buildSliderTile(
                    context,
                    title: 'Initial Allocation',
                    subtitle: 'Percentage of capital to '
                        'allocate at start',
                    value: config.initialAllocationPct,
                    min: 0,
                    max: 100,
                    divisions: 20,
                    label:
                        '${config.initialAllocationPct.toInt()}%',
                    onChanged: (value) {
                      viewModel.updateInitialAllocation(value);
                    },
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Macroeconomic Context
              _buildSection(
                context,
                title: 'Macroeconomic Context',
                icon: Icons.public,
                children: [
                  SwitchListTile(
                    title: const Text('Enable Macro Factors'),
                    subtitle: const Text(
                      'Add macro-awareness genes to the chromosome',
                    ),
                    value: config.useMacroData,
                    onChanged: (value) {
                      viewModel.updateUseMacroData(value);
                    },
                  ),
                  if (config.useMacroData) ...[
                    ListTile(
                      leading: Icon(
                        Icons.check_circle,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      title: const Text('Indicators'),
                      subtitle: const Text(
                        'VIX, Yield Curve, Fed Funds Rate, '
                        'CPI, Unemployment',
                      ),
                    ),
                    ListTile(
                      leading: Icon(
                        Icons.info_outline,
                        color: Theme.of(context).colorScheme.secondary,
                      ),
                      title: const Text('Gene Impact'),
                      subtitle: const Text(
                        '+15 macro genes added to chromosome '
                        '(21 total). Genes control how macro '
                        'conditions modify position sizing, '
                        'trade gating, and risk thresholds.',
                      ),
                    ),
                    ListTile(
                      leading: Icon(
                        Icons.warning_amber,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      title: const Text('Data Required'),
                      subtitle: const Text(
                        'Run populate_macro_data.py or '
                        'import_macro_csv.py to load macro '
                        'data into the database first.',
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 16),

              // Technical Indicator Filters
              _buildSection(
                context,
                title: 'Technical Indicator Filters',
                icon: Icons.analytics,
                children: [
                  SwitchListTile(
                    title: const Text('Enable TI Filters'),
                    subtitle: const Text(
                      'Add per-stock indicator genes to the chromosome',
                    ),
                    value: config.useTechnicalIndicators,
                    onChanged: (value) {
                      viewModel.updateUseTechnicalIndicators(value);
                    },
                  ),
                  if (config.useTechnicalIndicators) ...[
                    ListTile(
                      leading: Icon(
                        Icons.check_circle,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      title: const Text('Indicators'),
                      subtitle: const Text(
                        'RSI, ADX, NATR, MFI, MACD Histogram',
                      ),
                    ),
                    ListTile(
                      leading: Icon(
                        Icons.info_outline,
                        color: Theme.of(context).colorScheme.secondary,
                      ),
                      title: const Text('Gene Impact'),
                      subtitle: Text(
                        '+12 TI genes added to chromosome '
                        '(${config.useMacroData ? 33 : 18} total). '
                        'Genes filter buys by momentum, trend '
                        'strength, volatility, and volume.',
                      ),
                    ),
                    ListTile(
                      leading: Icon(
                        Icons.warning_amber,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      title: const Text('Data Required'),
                      subtitle: const Text(
                        'Database must contain rsi, adx, natr, '
                        'mfi, macdhist columns in daily_indicators.',
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 16),

              // Ensemble Signals
              _buildSection(
                context,
                title: 'Ensemble Signals',
                icon: Icons.merge_type,
                children: [
                  SwitchListTile(
                    title: const Text('Enable Ensemble Signals'),
                    subtitle: const Text(
                      'Combine multiple signal generators '
                      'with evolved weights',
                    ),
                    value: config.useEnsembleSignals,
                    onChanged: (value) {
                      viewModel.updateUseEnsembleSignals(value);
                    },
                  ),
                  if (config.useEnsembleSignals) ...[
                    ListTile(
                      leading: Icon(
                        Icons.check_circle,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      title: const Text('Signal Sources'),
                      subtitle: const Text(
                        'MA Crossover, Bollinger Bands, '
                        'Stochastic, MACD, RSI',
                      ),
                    ),
                    ListTile(
                      leading: Icon(
                        Icons.info_outline,
                        color: Theme.of(context).colorScheme.secondary,
                      ),
                      title: const Text('Gene Impact'),
                      subtitle: const Text(
                        '+13 ensemble genes added to chromosome. '
                        'Genes control signal weights, buy/sell '
                        'thresholds, and per-signal parameters.',
                      ),
                    ),
                    ListTile(
                      leading: Icon(
                        Icons.warning_amber,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      title: const Text('Data Required'),
                      subtitle: const Text(
                        'Database must contain bb_top, bb_mid, '
                        'bb_bot, slowk, slowd, macd, signal '
                        'columns in daily_indicators.',
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 16),

              // K-Fold Cross-Validation
              _buildSection(
                context,
                title: 'K-Fold Cross-Validation',
                icon: Icons.view_timeline,
                children: [
                  SwitchListTile(
                    title: const Text('Enable K-Fold CV'),
                    subtitle: const Text(
                      'Split training period into multiple '
                      'folds for more robust evaluation',
                    ),
                    value: config.useKfoldValidation,
                    onChanged: (value) {
                      viewModel.updateUseKfoldValidation(value);
                    },
                  ),
                  if (config.useKfoldValidation) ...[
                    _buildSliderTile(
                      context,
                      title: 'Number of Folds',
                      subtitle: 'How many time windows to '
                          'evaluate',
                      value: config.kfoldNumFolds.toDouble(),
                      min: 2,
                      max: 7,
                      divisions: 5,
                      label: '${config.kfoldNumFolds} folds',
                      onChanged: (value) {
                        viewModel.updateKfoldNumFolds(
                          value.toInt(),
                        );
                      },
                    ),
                    _buildSliderTile(
                      context,
                      title: 'Years Per Fold',
                      subtitle: 'Duration of each time window',
                      value: config.kfoldFoldYears.toDouble(),
                      min: 1,
                      max: 5,
                      divisions: 4,
                      label: '${config.kfoldFoldYears} years',
                      onChanged: (value) {
                        viewModel.updateKfoldFoldYears(
                          value.toInt(),
                        );
                      },
                    ),
                    SwitchListTile(
                      title: const Text(
                        'Allow Overlapping Folds',
                      ),
                      subtitle: const Text(
                        'Sliding window — folds can share '
                        'data for more coverage',
                      ),
                      value: config.kfoldAllowOverlap,
                      onChanged: (value) {
                        viewModel.updateKfoldAllowOverlap(
                          value,
                        );
                      },
                    ),
                    ListTile(
                      leading: Icon(
                        Icons.info_outline,
                        color: Theme.of(context)
                            .colorScheme
                            .secondary,
                      ),
                      title: const Text('Fold Preview'),
                      subtitle: Text(
                        _computeFoldPreview(config),
                      ),
                    ),
                    SwitchListTile(
                      title: const Text('Weight Recent Folds'),
                      subtitle: const Text(
                        'Give more importance to recent '
                        'time periods',
                      ),
                      value: config.kfoldWeightRecent,
                      onChanged: (value) {
                        viewModel.updateKfoldWeightRecent(
                          value,
                        );
                      },
                    ),
                    if (config.kfoldWeightRecent)
                      _buildSliderTile(
                        context,
                        title: 'Recent Weight Factor',
                        subtitle: 'Extra weight for the last '
                            'fold',
                        value: config.kfoldRecentWeightFactor,
                        min: 1.0,
                        max: 3.0,
                        divisions: 20,
                        label: config.kfoldRecentWeightFactor
                            .toStringAsFixed(1),
                        onChanged: (value) {
                          viewModel
                              .updateKfoldRecentWeightFactor(
                            value,
                          );
                        },
                      ),
                    ListTile(
                      leading: Icon(
                        Icons.warning_amber,
                        color:
                            Theme.of(context).colorScheme.error,
                      ),
                      title: const Text('Performance Impact'),
                      subtitle: Text(
                        '${_computeNumFolds(config)} folds = '
                        '${_computeNumFolds(config)}x more '
                        'backtests per trader. Parallel '
                        'evaluation is recommended.',
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 16),

              // Genetic Algorithm
              _buildSection(
                context,
                title: 'Genetic Algorithm',
                icon: Icons.psychology,
                children: [
                  _buildSliderTile(
                    context,
                    title: 'Population Size',
                    subtitle: 'Number of traders per generation',
                    value: config.populationSize.toDouble(),
                    min: 10,
                    max: 100,
                    divisions: 18,
                    label: '${config.populationSize}',
                    onChanged: (value) {
                      viewModel.updatePopulationSize(value.toInt());
                    },
                  ),
                  _buildSliderTile(
                    context,
                    title: 'Generations',
                    subtitle: 'Number of evolution cycles',
                    value: config.numGenerations.toDouble(),
                    min: 10,
                    max: 200,
                    divisions: 19,
                    label: '${config.numGenerations}',
                    onChanged: (value) {
                      viewModel.updateNumGenerations(value.toInt());
                    },
                  ),
                  _buildSliderTile(
                    context,
                    title: 'Mutation Rate',
                    subtitle: 'Probability of random gene changes',
                    value: config.mutationRate,
                    min: 0.0,
                    max: 1.0,
                    divisions: 20,
                    label: config.mutationRate.toStringAsFixed(2),
                    onChanged: (value) {
                      viewModel.updateMutationRate(value);
                    },
                  ),
                  _buildSliderTile(
                    context,
                    title: 'Crossover Rate',
                    subtitle: 'Probability of parent gene mixing',
                    value: config.crossoverRate,
                    min: 0.0,
                    max: 1.0,
                    divisions: 20,
                    label: config.crossoverRate.toStringAsFixed(2),
                    onChanged: (value) {
                      viewModel.updateCrossoverRate(value);
                    },
                  ),
                  _buildSliderTile(
                    context,
                    title: 'Elitism %',
                    subtitle: 'Top % of population preserved each generation',
                    value: config.elitismPct,
                    min: 0.0,
                    max: 50.0,
                    divisions: 50,
                    label: '${config.elitismPct.toStringAsFixed(1)}% (${(config.populationSize * config.elitismPct / 100).ceil()} traders)',
                    onChanged: (value) {
                      viewModel.updateElitismPct(value);
                    },
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Fitness Weights
              _buildSection(
                context,
                title: 'Fitness Weights',
                icon: Icons.tune,
                subtitle: 'Automatically normalized to 100%',
                children: config.fitnessWeights.entries.map((entry) {
                  return _buildSliderTile(
                    context,
                    title: _formatWeightName(entry.key),
                    value: entry.value,
                    min: 0.0,
                    max: 1.0,
                    divisions: 20,
                    label: '${(entry.value * 100).toInt()}%',
                    onChanged: (value) {
                      viewModel.updateFitnessWeight(entry.key, value);
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),

              // Backtrader Settings
              _buildSection(
                context,
                title: 'Backtrader Settings',
                icon: Icons.attach_money,
                children: [
                  ListTile(
                    title: const Text('Initial Cash'),
                    subtitle: Text('\$${config.initialCash.toStringAsFixed(0)}'),
                    trailing: const Icon(Icons.edit),
                    onTap: () {
                      _showEditDialog(
                        context,
                        title: 'Initial Cash',
                        currentValue: config.initialCash.toString(),
                        onSave: (value) {
                          final cash = double.tryParse(value);
                          if (cash != null) {
                            viewModel.updateInitialCash(cash);
                          }
                        },
                      );
                    },
                  ),
                  ListTile(
                    title: const Text('Commission'),
                    subtitle: Text('${(config.commission * 100).toStringAsFixed(2)}%'),
                    trailing: const Icon(Icons.edit),
                    onTap: () {
                      _showEditDialog(
                        context,
                        title: 'Commission (%)',
                        currentValue: (config.commission * 100).toString(),
                        onSave: (value) {
                          final pct = double.tryParse(value);
                          if (pct != null) {
                            viewModel.updateCommission(pct / 100);
                          }
                        },
                      );
                    },
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Performance Settings
              _buildSection(
                context,
                title: 'Performance',
                icon: Icons.speed,
                children: [
                  SwitchListTile(
                    title: const Text('Parallel Evaluation'),
                    subtitle: const Text('Use multiple CPU cores'),
                    value: config.useParallelEvaluation,
                    onChanged: (value) {
                      viewModel.updateUseParallelEvaluation(value);
                    },
                  ),
                ],
              ),
              const SizedBox(height: 32),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSection(
    BuildContext context, {
    required String title,
    required IconData icon,
    String? subtitle,
    required List<Widget> children,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 12),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
            const SizedBox(height: 8),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _buildSliderTile(
    BuildContext context, {
    required String title,
    String? subtitle,
    required double value,
    required double min,
    required double max,
    required int divisions,
    required String label,
    required ValueChanged<double> onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ListTile(
          title: Text(title),
          subtitle: subtitle != null ? Text(subtitle) : null,
          trailing: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.onPrimaryContainer,
              ),
            ),
          ),
        ),
        Slider(
          value: value,
          min: min,
          max: max,
          divisions: divisions,
          label: label,
          onChanged: onChanged,
        ),
      ],
    );
  }

  String _formatWeightName(String key) {
    return key
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }

  int _computeNumFolds(config) {
    final start = DateTime.tryParse(config.trainStartDate);
    final end = DateTime.tryParse(config.trainEndDate);
    if (start == null || end == null) return 1;
    final totalDays = end.difference(start).inDays;
    final foldDays = (config.kfoldFoldYears * 365.25).toInt();
    if (foldDays <= 0) return 1;

    var numFolds = config.kfoldNumFolds as int;
    if (!config.kfoldAllowOverlap) {
      final maxFolds = totalDays ~/ foldDays;
      numFolds = numFolds.clamp(1, maxFolds.clamp(1, 7));
    }
    return numFolds;
  }

  String _computeFoldPreview(config) {
    final start = DateTime.tryParse(config.trainStartDate);
    final end = DateTime.tryParse(config.trainEndDate);
    if (start == null || end == null) return 'Invalid date range';

    final totalDays = end.difference(start).inDays;
    var foldDays = (config.kfoldFoldYears * 365.25).toInt();
    if (foldDays <= 0) return 'Invalid fold size';
    foldDays = foldDays.clamp(1, totalDays);

    var numFolds = config.kfoldNumFolds as int;
    final allowOverlap = config.kfoldAllowOverlap as bool;

    double stride;
    if (allowOverlap) {
      stride = numFolds > 1
          ? (totalDays - foldDays) / (numFolds - 1)
          : totalDays.toDouble();
    } else {
      stride = foldDays.toDouble();
      final maxFolds = totalDays ~/ foldDays;
      numFolds = numFolds.clamp(1, maxFolds.clamp(1, 7));
    }

    final folds = <String>[];
    for (var i = 0; i < numFolds; i++) {
      final foldStart = start.add(
        Duration(days: (i * stride).toInt()),
      );
      var foldEnd = foldStart.add(
        Duration(days: foldDays - 1),
      );
      if (foldEnd.isAfter(end)) foldEnd = end;
      folds.add(
        'Fold ${i + 1}: '
        '${_fmtDate(foldStart)} - ${_fmtDate(foldEnd)}',
      );
    }

    if (!allowOverlap && config.kfoldNumFolds > numFolds) {
      folds.add(
        '(Capped from ${config.kfoldNumFolds} to '
        '$numFolds — not enough data for '
        'non-overlapping folds)',
      );
    }

    return folds.join('\n');
  }

  String _fmtDate(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}';

  void _showResetDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reset Configuration'),
        content: const Text(
          'Are you sure you want to reset all settings to defaults?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              context.read<ConfigViewModel>().resetToDefaults();
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Configuration reset to defaults'),
                ),
              );
            },
            child: const Text('Reset'),
          ),
        ],
      ),
    );
  }

  void _showEditDialog(
    BuildContext context, {
    required String title,
    required String currentValue,
    required ValueChanged<String> onSave,
  }) {
    final controller = TextEditingController(text: currentValue);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Edit $title'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: InputDecoration(
            labelText: title,
            border: const OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              onSave(controller.text);
              Navigator.pop(context);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }
}

/// Database selector with preset options and file browser.
class _DatabaseSelector extends StatelessWidget {
  const _DatabaseSelector({
    required this.currentPath,
    required this.onChanged,
  });

  final String currentPath;
  final ValueChanged<String> onChanged;

  static const _projectDir =
      '/Users/fred/Development/Genetic Trader';

  static const _presets = [
    _DbPreset(
      label: 'S&P 500 (SPY_Data.db)',
      path: '$_projectDir/SPY_Data.db',
      description: '503 symbols, 10 years, with TI',
    ),
    _DbPreset(
      label: 'Alpaca/Polygon',
      path: '/Users/fred/alpaca_Big_polygon.db',
      description: '4656 symbols, 10 years, with TI',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final isPreset = _presets.any((p) => p.path == currentPath);
    final dropdownValue = isPreset ? currentPath : '__custom__';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          initialValue: dropdownValue,
          decoration: const InputDecoration(
            labelText: 'Database Source',
            border: OutlineInputBorder(),
          ),
          isExpanded: true,
          items: [
            for (final preset in _presets)
              DropdownMenuItem(
                value: preset.path,
                child: Text(preset.label),
              ),
            if (!isPreset)
              DropdownMenuItem(
                value: '__custom__',
                child: Text(
                  'Custom: ${_fileName(currentPath)}',
                ),
              ),
          ],
          onChanged: (value) {
            if (value != null && value != '__custom__') {
              onChanged(value);
            }
          },
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: Text(
                _presetDescription(currentPath) ??
                    currentPath,
                style:
                    Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurfaceVariant,
                        ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            TextButton.icon(
              icon: const Icon(Icons.folder_open, size: 18),
              label: const Text('Browse'),
              onPressed: () async {
                final result =
                    await FilePicker.platform.pickFiles(
                  type: FileType.custom,
                  allowedExtensions: ['db', 'sqlite', 'sqlite3'],
                  dialogTitle: 'Select Database File',
                );
                if (result != null &&
                    result.files.single.path != null) {
                  onChanged(result.files.single.path!);
                }
              },
            ),
          ],
        ),
      ],
    );
  }

  String? _presetDescription(String path) {
    for (final preset in _presets) {
      if (preset.path == path) return preset.description;
    }
    return null;
  }

  static String _fileName(String path) {
    final idx = path.lastIndexOf('/');
    return idx >= 0 ? path.substring(idx + 1) : path;
  }
}

class _DbPreset {
  const _DbPreset({
    required this.label,
    required this.path,
    required this.description,
  });

  final String label;
  final String path;
  final String description;
}

/// Displays computed train and test date ranges.
class _TrainTestDateDisplay extends StatelessWidget {
  const _TrainTestDateDisplay({
    required this.trainStartDate,
    required this.testEndDate,
    required this.trainingYears,
  });

  final String trainStartDate;
  final String testEndDate;
  final int trainingYears;

  @override
  Widget build(BuildContext context) {
    final start = DateTime.tryParse(trainStartDate);
    final end = DateTime.tryParse(testEndDate);
    if (start == null || end == null) {
      return const SizedBox.shrink();
    }

    final splitDate = DateTime(
      start.year + trainingYears,
      start.month,
      start.day,
    );
    final testStart = splitDate.add(const Duration(days: 1));
    final totalDays = end.difference(start).inDays;
    final trainDays = splitDate.difference(start).inDays;
    final testDays = end.difference(testStart).inDays;

    final trainPct = totalDays > 0
        ? (trainDays / totalDays * 100).toStringAsFixed(0)
        : '0';
    final testPct = totalDays > 0
        ? (testDays / totalDays * 100).toStringAsFixed(0)
        : '0';

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 8,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: _DateRangeChip(
                  label: 'Train ($trainPct%)',
                  startDate: _fmt(start),
                  endDate: _fmt(splitDate),
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _DateRangeChip(
                  label: 'Test ($testPct%)',
                  startDate: _fmt(testStart),
                  endDate: _fmt(end),
                  color: Theme.of(context).colorScheme.tertiary,
                ),
              ),
            ],
          ),
          if (testDays <= 0)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Warning: No test data remaining. '
                'Reduce training years.',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.error,
                  fontSize: 12,
                ),
              ),
            ),
        ],
      ),
    );
  }

  String _fmt(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';
}

/// A colored chip showing a date range label.
class _DateRangeChip extends StatelessWidget {
  const _DateRangeChip({
    required this.label,
    required this.startDate,
    required this.endDate,
    required this.color,
  });

  final String label;
  final String startDate;
  final String endDate;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: color.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: color,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '$startDate\n$endDate',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

/// Sector filter chips for narrowing auto-selected stocks
class _SectorFilterChips extends StatelessWidget {
  static const List<String> _availableSectors = [
    'Communication Services',
    'Consumer Discretionary',
    'Consumer Staples',
    'Energy',
    'Financials',
    'Health Care',
    'Industrials',
    'Information Technology',
    'Materials',
    'Real Estate',
    'Utilities',
  ];

  final List<String> selectedSectors;
  final ValueChanged<String> onToggle;
  final VoidCallback onClearAll;

  const _SectorFilterChips({
    required this.selectedSectors,
    required this.onToggle,
    required this.onClearAll,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 8,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.category,
                size: 20,
                color: theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 8),
              Text(
                'Sector Filter',
                style: theme.textTheme.titleSmall,
              ),
              const Spacer(),
              if (selectedSectors.isNotEmpty)
                TextButton(
                  onPressed: onClearAll,
                  child: const Text('Clear All'),
                ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            selectedSectors.isEmpty
                ? 'All sectors eligible (no filter)'
                : '${selectedSectors.length} sector'
                    '${selectedSectors.length == 1 ? '' : 's'}'
                    ' selected',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: _availableSectors.map((sector) {
              final isSelected =
                  selectedSectors.contains(sector);
              return FilterChip(
                label: Text(sector),
                selected: isSelected,
                onSelected: (_) => onToggle(sector),
                showCheckmark: true,
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

/// Input field for manually entering stock symbols
class _StockInputField extends StatefulWidget {
  final List<String> stocks;
  final ValueChanged<List<String>> onChanged;

  const _StockInputField({
    required this.stocks,
    required this.onChanged,
  });

  @override
  State<_StockInputField> createState() => _StockInputFieldState();
}

class _StockInputFieldState extends State<_StockInputField> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _addSymbols(String text) {
    final newSymbols = text
        .split(RegExp(r'[,\s]+'))
        .map((s) => s.trim().toUpperCase())
        .where((s) => s.isNotEmpty)
        .toList();
    if (newSymbols.isEmpty) return;

    final updated = List<String>.from(widget.stocks);
    for (final sym in newSymbols) {
      if (!updated.contains(sym)) {
        updated.add(sym);
      }
    }
    _controller.clear();
    widget.onChanged(updated);
  }

  void _removeSymbol(String symbol) {
    final updated = List<String>.from(widget.stocks)
      ..remove(symbol);
    widget.onChanged(updated);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 8,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _controller,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(
              labelText: 'Add stock symbols',
              hintText: 'e.g. AAPL, MSFT, GOOG',
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                icon: const Icon(Icons.add),
                onPressed: () => _addSymbols(
                  _controller.text,
                ),
              ),
            ),
            onSubmitted: _addSymbols,
          ),
          const SizedBox(height: 8),
          if (widget.stocks.isNotEmpty) ...[
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: widget.stocks
                  .map(
                    (sym) => Chip(
                      label: Text(sym),
                      deleteIcon: const Icon(
                        Icons.close,
                        size: 16,
                      ),
                      onDeleted: () => _removeSymbol(sym),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 4),
            Text(
              '${widget.stocks.length} stock'
              '${widget.stocks.length == 1 ? '' : 's'}'
              ' selected',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ] else
            Text(
              'No stocks added yet',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.error,
              ),
            ),
        ],
      ),
    );
  }
}
