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
