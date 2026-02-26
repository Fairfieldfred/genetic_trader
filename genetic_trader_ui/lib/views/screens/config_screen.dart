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
                    title: const Text('Use Portfolio Mode'),
                    subtitle: const Text('Trade multiple stocks simultaneously'),
                    value: config.usePortfolio,
                    onChanged: (value) {
                      viewModel.updateUsePortfolio(value);
                    },
                  ),
                  _buildSliderTile(
                    context,
                    title: 'Portfolio Size',
                    value: config.portfolioSize.toDouble(),
                    min: 1,
                    max: 50,
                    divisions: 49,
                    label: '${config.portfolioSize} stocks',
                    onChanged: (value) {
                      viewModel.updatePortfolioSize(value.toInt());
                    },
                  ),
                  _buildSliderTile(
                    context,
                    title: 'Initial Allocation',
                    subtitle: 'Percentage of capital to allocate at start',
                    value: config.initialAllocationPct,
                    min: 0,
                    max: 100,
                    divisions: 20,
                    label: '${config.initialAllocationPct.toInt()}%',
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
