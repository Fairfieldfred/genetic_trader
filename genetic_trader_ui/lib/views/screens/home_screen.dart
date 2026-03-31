import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../core/services/data_sync_service.dart';
import '../../core/services/database_service.dart';
import '../../core/services/index_service.dart';
import '../../core/services/yahoo_finance_service.dart';
import '../../models/evolution_result.dart';
import '../../viewmodels/config_viewmodel.dart';
import '../../viewmodels/evolution_viewmodel.dart';
import '../../viewmodels/results_viewmodel.dart';
import 'results_dashboard_screen.dart';
import 'results_list_screen.dart';

/// Combined two-panel home screen: config (left) + evolution (right).
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Genetic Trader'),
        actions: [
          IconButton(
            icon: const Icon(Icons.show_chart),
            tooltip: 'View Results',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => const ResultsListScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: Row(
        children: [
          // LEFT PANEL — Configuration
          SizedBox(
            width: 560,
            child: _LeftConfigPanel(),
          ),
          const VerticalDivider(width: 1),
          // RIGHT PANEL — Evolution Launcher
          Expanded(
            child: ChangeNotifierProvider(
              create: (_) => EvolutionViewModel(),
              child: const _RightEvolutionPanel(),
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────
// LEFT PANEL
// ─────────────────────────────────────────

class _LeftConfigPanel extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<ConfigViewModel>(
      builder: (context, viewModel, _) {
        final config = viewModel.config;
        return Column(
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(8),
                children: [
                  // 1. Data Source — index selection + sync
                  _compactSection(
                    context,
                    icon: Icons.cloud_download,
                    title: 'Data Source',
                    subtitle: '${_totalSymbolCount(config.selectedIndices)}'
                        ' symbols',
                    children: [
                      _IndexSelector(
                        selectedIndices: config.selectedIndices,
                        onToggle: viewModel.toggleIndex,
                      ),
                    ],
                  ),

                  // 2. Train/Test Split
                  _compactSection(
                    context,
                    icon: Icons.call_split,
                    title: 'Train / Test Split',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Out-of-Sample Testing'),
                        subtitle: Text(
                          config.useOutOfSampleTest
                              ? 'Train ${config.trainingYears}y, '
                                  'test on rest'
                              : 'Full range for training',
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall,
                        ),
                        value: config.useOutOfSampleTest,
                        onChanged: viewModel.updateUseOutOfSampleTest,
                      ),
                      if (config.useOutOfSampleTest) ...[
                        _compactSlider(
                          context,
                          title: 'Training Years',
                          value: config.trainingYears.toDouble(),
                          min: 1,
                          max: 9,
                          divisions: 8,
                          label: '${config.trainingYears}y',
                          onChanged: (v) =>
                              viewModel.updateTrainingYears(v.toInt()),
                        ),
                        _TrainTestDateDisplay(
                          trainStartDate: config.trainStartDate,
                          testEndDate: config.testEndDate,
                          trainingYears: config.trainingYears,
                        ),
                      ],
                    ],
                  ),

                  // 3. Portfolio
                  _compactSection(
                    context,
                    icon: Icons.account_balance_wallet,
                    title: 'Portfolio',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Auto-Select Stocks'),
                        value: config.autoSelectPortfolio,
                        onChanged: viewModel.updateAutoSelectPortfolio,
                      ),
                      if (config.autoSelectPortfolio)
                        _compactSlider(
                          context,
                          title: 'Portfolio Size',
                          value: config.portfolioSize.toDouble(),
                          min: 1,
                          max: 50,
                          divisions: 49,
                          label: '${config.portfolioSize}',
                          onChanged: (v) =>
                              viewModel.updatePortfolioSize(v.toInt()),
                        ),
                      if (config.autoSelectPortfolio)
                        _SectorFilterChips(
                          selectedSectors: config.portfolioSectors,
                          onToggle: viewModel.togglePortfolioSector,
                          onClearAll: () =>
                              viewModel.updatePortfolioSectors([]),
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
                      _compactSlider(
                        context,
                        title: 'Initial Allocation',
                        value: config.initialAllocationPct,
                        min: 0,
                        max: 100,
                        divisions: 20,
                        label:
                            '${config.initialAllocationPct.toInt()}%',
                        onChanged: viewModel.updateInitialAllocation,
                      ),
                    ],
                  ),

                  // 4. Feature Toggles
                  _compactSection(
                    context,
                    icon: Icons.extension,
                    title: 'Feature Toggles',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Macro Factors'),
                        subtitle: config.useMacroData
                            ? Text(
                                '+15 macro genes',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Theme.of(context)
                                      .colorScheme
                                      .primary,
                                ),
                              )
                            : null,
                        value: config.useMacroData,
                        onChanged: viewModel.updateUseMacroData,
                      ),
                      SwitchListTile(
                        dense: true,
                        title: const Text('TI Filters'),
                        subtitle: config.useTechnicalIndicators
                            ? Text(
                                '+12 TI genes',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Theme.of(context)
                                      .colorScheme
                                      .primary,
                                ),
                              )
                            : null,
                        value: config.useTechnicalIndicators,
                        onChanged:
                            viewModel.updateUseTechnicalIndicators,
                      ),
                      SwitchListTile(
                        dense: true,
                        title: const Text('Ensemble Signals'),
                        subtitle: config.useEnsembleSignals
                            ? Text(
                                '+13 ensemble genes',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Theme.of(context)
                                      .colorScheme
                                      .primary,
                                ),
                              )
                            : null,
                        value: config.useEnsembleSignals,
                        onChanged:
                            viewModel.updateUseEnsembleSignals,
                      ),
                      SwitchListTile(
                        dense: true,
                        title: const Text('K-Fold CV'),
                        value: config.useKfoldValidation,
                        onChanged:
                            viewModel.updateUseKfoldValidation,
                      ),
                      if (config.useKfoldValidation) ...[
                        _compactSlider(
                          context,
                          title: 'Folds',
                          value: config.kfoldNumFolds.toDouble(),
                          min: 2,
                          max: 7,
                          divisions: 5,
                          label: '${config.kfoldNumFolds}',
                          onChanged: (v) =>
                              viewModel.updateKfoldNumFolds(v.toInt()),
                        ),
                        _compactSlider(
                          context,
                          title: 'Years/Fold',
                          value: config.kfoldFoldYears.toDouble(),
                          min: 1,
                          max: 5,
                          divisions: 4,
                          label: '${config.kfoldFoldYears}y',
                          onChanged: (v) =>
                              viewModel.updateKfoldFoldYears(
                                  v.toInt()),
                        ),
                        SwitchListTile(
                          dense: true,
                          title: const Text('Overlap'),
                          value: config.kfoldAllowOverlap,
                          onChanged:
                              viewModel.updateKfoldAllowOverlap,
                        ),
                        SwitchListTile(
                          dense: true,
                          title: const Text('Weight Recent'),
                          value: config.kfoldWeightRecent,
                          onChanged:
                              viewModel.updateKfoldWeightRecent,
                        ),
                        if (config.kfoldWeightRecent)
                          _compactSlider(
                            context,
                            title: 'Weight Factor',
                            value: config.kfoldRecentWeightFactor,
                            min: 1.0,
                            max: 3.0,
                            divisions: 20,
                            label: config.kfoldRecentWeightFactor
                                .toStringAsFixed(1),
                            onChanged: viewModel
                                .updateKfoldRecentWeightFactor,
                          ),
                        Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 4,
                          ),
                          child: Text(
                            _computeFoldPreview(config),
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(
                                  color: Theme.of(context)
                                      .colorScheme
                                      .onSurfaceVariant,
                                ),
                          ),
                        ),
                      ],
                    ],
                  ),

                  // Advanced Oscillators
                  _compactSection(
                    context,
                    icon: Icons.ssid_chart,
                    title: 'Advanced Oscillators',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Enable Advanced Oscillators'),
                        value: config.useAdvancedOscillators,
                        onChanged: viewModel.updateUseAdvancedOscillators,
                      ),
                      if (config.useAdvancedOscillators) ...[
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.check_circle, size: 16, color: Theme.of(context).colorScheme.primary),
                          title: const Text('Genes Added'),
                          subtitle: const Text('+13 genes'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.info_outline, size: 16, color: Theme.of(context).colorScheme.secondary),
                          title: const Text('Signals'),
                          subtitle: const Text('Williams %R, CCI, CMO, Awesome Oscillator, Stochastic RSI, Ultimate Oscillator, Rate of Change'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.warning_amber, size: 16, color: Theme.of(context).colorScheme.error),
                          title: const Text('Data Required'),
                          subtitle: const Text('Re-run calculate_indicators.py — new columns: wr, cci, cmo, ao, stochrsi_k/d, uo, roc'),
                        ),
                      ],
                    ],
                  ),

                  // Trend Signals
                  _compactSection(
                    context,
                    icon: Icons.trending_up,
                    title: 'Trend Signals',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Enable Trend Signals'),
                        value: config.useTrendSignals,
                        onChanged: viewModel.updateUseTrendSignals,
                      ),
                      if (config.useTrendSignals) ...[
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.check_circle, size: 16, color: Theme.of(context).colorScheme.primary),
                          title: const Text('Genes Added'),
                          subtitle: const Text('+7 genes'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.info_outline, size: 16, color: Theme.of(context).colorScheme.secondary),
                          title: const Text('Signals'),
                          subtitle: const Text('Parabolic SAR direction, Supertrend filter, Ichimoku Cloud gate, Linear Regression slope/R\u00B2, TRIX zero-cross'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.warning_amber, size: 16, color: Theme.of(context).colorScheme.error),
                          title: const Text('Data Required'),
                          subtitle: const Text('Re-run calculate_indicators.py — new columns: psar, supertrend_dir, ichimoku_above_cloud, linreg_slope, linreg_r2, trix'),
                        ),
                      ],
                    ],
                  ),

                  // Volume Signals
                  _compactSection(
                    context,
                    icon: Icons.bar_chart,
                    title: 'Volume Signals',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Enable Volume Signals'),
                        value: config.useVolumeSignals,
                        onChanged: viewModel.updateUseVolumeSignals,
                      ),
                      if (config.useVolumeSignals) ...[
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.check_circle, size: 16, color: Theme.of(context).colorScheme.primary),
                          title: const Text('Genes Added'),
                          subtitle: const Text('+8 genes'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.info_outline, size: 16, color: Theme.of(context).colorScheme.secondary),
                          title: const Text('Signals'),
                          subtitle: const Text('Chaikin Oscillator accumulation, Force Index, VWAP filter mode, VWMA vs SMA, Klinger Oscillator, NVI/PVI smart-money'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.warning_amber, size: 16, color: Theme.of(context).colorScheme.error),
                          title: const Text('Data Required'),
                          subtitle: const Text('Re-run calculate_indicators.py — new columns: chaikin, force_index, vwap, vwma_20, klinger, nvi/pvi + SMAs'),
                        ),
                      ],
                    ],
                  ),

                  // Volatility & Breakout
                  _compactSection(
                    context,
                    icon: Icons.bolt,
                    title: 'Volatility & Breakout',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Enable Volatility & Breakout'),
                        value: config.useVolatilityBreakout,
                        onChanged: viewModel.updateUseVolatilityBreakout,
                      ),
                      if (config.useVolatilityBreakout) ...[
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.check_circle, size: 16, color: Theme.of(context).colorScheme.primary),
                          title: const Text('Genes Added'),
                          subtitle: const Text('+6 genes'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.info_outline, size: 16, color: Theme.of(context).colorScheme.secondary),
                          title: const Text('Signals'),
                          subtitle: const Text('Donchian breakout confirm, Keltner Channel extended filter, Bollinger %B position, BB Width squeeze gate, Ulcer Index risk cap'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.warning_amber, size: 16, color: Theme.of(context).colorScheme.error),
                          title: const Text('Data Required'),
                          subtitle: const Text('Re-run calculate_indicators.py — new columns: donchian_upper/lower, keltner_upper/lower, bb_pct_b, bb_width, ulcer'),
                        ),
                      ],
                    ],
                  ),

                  // Support & Resistance
                  _compactSection(
                    context,
                    icon: Icons.horizontal_rule,
                    title: 'Support & Resistance',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Enable Support & Resistance'),
                        value: config.useSupportResistance,
                        onChanged: viewModel.updateUseSupportResistance,
                      ),
                      if (config.useSupportResistance) ...[
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.check_circle, size: 16, color: Theme.of(context).colorScheme.primary),
                          title: const Text('Genes Added'),
                          subtitle: const Text('+5 genes'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.info_outline, size: 16, color: Theme.of(context).colorScheme.secondary),
                          title: const Text('Signals'),
                          subtitle: const Text('Pivot Points R1/S1/R2/S2 resistance filter, Fibonacci 38.2% and 61.8% retracement buy zones'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.warning_amber, size: 16, color: Theme.of(context).colorScheme.error),
                          title: const Text('Data Required'),
                          subtitle: const Text('Re-run calculate_indicators.py — new columns: pivot_r1/s1/r2/s2, fib_38, fib_62'),
                        ),
                      ],
                    ],
                  ),

                  // Market Regime Detection
                  _compactSection(
                    context,
                    icon: Icons.public,
                    title: 'Market Regime Detection',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Enable Regime Detection'),
                        value: config.useRegimeDetection,
                        onChanged: viewModel.updateUseRegimeDetection,
                      ),
                      if (config.useRegimeDetection) ...[
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.check_circle, size: 16, color: Theme.of(context).colorScheme.primary),
                          title: const Text('Genes Added'),
                          subtitle: const Text('+4 genes'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.info_outline, size: 16, color: Theme.of(context).colorScheme.secondary),
                          title: const Text('Signals'),
                          subtitle: const Text('SMA200 bear market gate, multi-timeframe trend score (SMA20/50/200), evolved regime window'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.warning_amber, size: 16, color: Theme.of(context).colorScheme.error),
                          title: const Text('Data Required'),
                          subtitle: const Text('Uses existing sma_20, sma_50 columns — no new columns needed'),
                        ),
                      ],
                    ],
                  ),

                  // Advanced Position Sizing
                  _compactSection(
                    context,
                    icon: Icons.account_balance,
                    title: 'Advanced Position Sizing',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Enable Advanced Sizing'),
                        value: config.useAdvancedSizing,
                        onChanged: viewModel.updateUseAdvancedSizing,
                      ),
                      if (config.useAdvancedSizing) ...[
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.check_circle, size: 16, color: Theme.of(context).colorScheme.primary),
                          title: const Text('Genes Added'),
                          subtitle: const Text('+4 genes'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.info_outline, size: 16, color: Theme.of(context).colorScheme.secondary),
                          title: const Text('Signals'),
                          subtitle: const Text('Sizing model: Fixed% / Fixed-Risk / Fractional Kelly / Volatility-ATR. Evolved Kelly fraction, ATR stop multiple, risk% per trade'),
                        ),
                        ListTile(
                          dense: true,
                          leading: Icon(Icons.warning_amber, size: 16, color: Theme.of(context).colorScheme.error),
                          title: const Text('Data Required'),
                          subtitle: const Text('Uses existing atr_14 column — no new columns needed'),
                        ),
                      ],
                    ],
                  ),

                  // 5. Genetic Algorithm
                  _compactSection(
                    context,
                    icon: Icons.psychology,
                    title: 'Genetic Algorithm',
                    children: [
                      _compactSlider(
                        context,
                        title: 'Population',
                        value: config.populationSize.toDouble(),
                        min: 10,
                        max: 100,
                        divisions: 18,
                        label: '${config.populationSize}',
                        onChanged: (v) =>
                            viewModel.updatePopulationSize(v.toInt()),
                      ),
                      _compactSlider(
                        context,
                        title: 'Generations',
                        value: config.numGenerations.toDouble(),
                        min: 10,
                        max: 200,
                        divisions: 19,
                        label: '${config.numGenerations}',
                        onChanged: (v) =>
                            viewModel.updateNumGenerations(v.toInt()),
                      ),
                      _compactSlider(
                        context,
                        title: 'Mutation Rate',
                        value: config.mutationRate,
                        min: 0.0,
                        max: 1.0,
                        divisions: 20,
                        label:
                            config.mutationRate.toStringAsFixed(2),
                        onChanged: viewModel.updateMutationRate,
                      ),
                      _compactSlider(
                        context,
                        title: 'Crossover Rate',
                        value: config.crossoverRate,
                        min: 0.0,
                        max: 1.0,
                        divisions: 20,
                        label:
                            config.crossoverRate.toStringAsFixed(2),
                        onChanged: viewModel.updateCrossoverRate,
                      ),
                      _compactSlider(
                        context,
                        title: 'Elitism %',
                        value: config.elitismPct,
                        min: 0.0,
                        max: 50.0,
                        divisions: 50,
                        label:
                            '${config.elitismPct.toStringAsFixed(1)}%',
                        onChanged: viewModel.updateElitismPct,
                      ),
                    ],
                  ),

                  // 6. Fitness Weights
                  _compactSection(
                    context,
                    icon: Icons.tune,
                    title: 'Fitness Weights',
                    subtitle: 'Auto-normalized to 100%',
                    children: config.fitnessWeights.entries.map((e) {
                      return _compactSlider(
                        context,
                        title: _formatWeightName(e.key),
                        value: e.value,
                        min: 0.0,
                        max: 1.0,
                        divisions: 20,
                        label: '${(e.value * 100).toInt()}%',
                        onChanged: (v) =>
                            viewModel.updateFitnessWeight(e.key, v),
                      );
                    }).toList(),
                  ),

                  // 7. Backtesting Engine
                  _compactSection(
                    context,
                    icon: Icons.settings_applications,
                    title: 'Backtesting Engine',
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 4,
                          vertical: 4,
                        ),
                        child: SizedBox(
                          width: double.infinity,
                          child: SegmentedButton<String>(
                            segments: const [
                              ButtonSegment(
                                value: 'backtrader',
                                label: Text('Backtrader'),
                              ),
                              ButtonSegment(
                                value: 'vectorbt',
                                label: Text('VectorBT'),
                              ),
                              ButtonSegment(
                                value: 'tradix',
                                label: Text('Tradix'),
                              ),
                            ],
                            selected: {config.backtestingEngine},
                            onSelectionChanged: (s) =>
                                viewModel.updateBacktestingEngine(
                                    s.first),
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 4,
                        ),
                        child: SizedBox(
                          width: double.infinity,
                          child: SegmentedButton<String>(
                            segments: const [
                              ButtonSegment(
                                value: 'sqlite',
                                label: Text('SQLite'),
                              ),
                              ButtonSegment(
                                value: 'yahoo',
                                label: Text('Yahoo'),
                              ),
                            ],
                            selected: {config.dataSource},
                            onSelectionChanged: (s) =>
                                viewModel.updateDataSource(s.first),
                          ),
                        ),
                      ),
                      ListTile(
                        dense: true,
                        title: Text(
                          'Cash: \$${config.initialCash.toStringAsFixed(0)}'
                          '  |  Commission: '
                          '${(config.commission * 100).toStringAsFixed(2)}%',
                        ),
                        trailing: const Icon(Icons.edit, size: 16),
                        onTap: () => _showCashCommissionDialog(
                          context,
                          viewModel,
                          config,
                        ),
                      ),
                    ],
                  ),

                  // 8. Performance
                  _compactSection(
                    context,
                    icon: Icons.speed,
                    title: 'Performance',
                    children: [
                      SwitchListTile(
                        dense: true,
                        title: const Text('Parallel Evaluation'),
                        value: config.useParallelEvaluation,
                        onChanged:
                            viewModel.updateUseParallelEvaluation,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                ],
              ),
            ),

            // Sticky footer
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 8,
              ),
              decoration: BoxDecoration(
                border: Border(
                  top: BorderSide(
                    color: Theme.of(context).dividerColor,
                  ),
                ),
              ),
              child: Row(
                children: [
                  OutlinedButton.icon(
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text('Reset'),
                    onPressed: () => _showResetDialog(context),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.save, size: 16),
                      label: const Text('Save Config'),
                      onPressed: () async {
                        try {
                          await context
                              .read<ConfigViewModel>()
                              .saveConfig();
                          if (context.mounted) {
                            ScaffoldMessenger.of(context)
                                .showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Configuration saved!',
                                ),
                                backgroundColor: Colors.green,
                              ),
                            );
                          }
                        } catch (e) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context)
                                .showSnackBar(
                              SnackBar(
                                content: Text('Error: $e'),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        }
                      },
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

// ─────────────────────────────────────────
// RIGHT PANEL
// ─────────────────────────────────────────

class _RightEvolutionPanel extends StatelessWidget {
  const _RightEvolutionPanel();

  @override
  Widget build(BuildContext context) {
    return Consumer<EvolutionViewModel>(
      builder: (context, viewModel, _) {
        return Column(
          children: [
            // TOP — App header
            _buildHeader(context),

            // MIDDLE — Evolution control
            _buildControlCard(context, viewModel),

            // Progress stats
            if (viewModel.isRunning || viewModel.isCompleted)
              _buildProgressStats(context, viewModel),

            // BOTTOM — Chart + Log tabs
            Expanded(
              child: Card(
                margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: DefaultTabController(
                  length: 3,
                  child: Column(
                    children: [
                      TabBar(
                        tabs: const [
                          Tab(
                            icon: Icon(Icons.show_chart),
                            text: 'Chart',
                          ),
                          Tab(
                            icon: Icon(Icons.tune),
                            text: 'Expression',
                          ),
                          Tab(
                            icon: Icon(Icons.terminal),
                            text: 'Output Log',
                          ),
                        ],
                        labelColor:
                            Theme.of(context).colorScheme.primary,
                        unselectedLabelColor: Theme.of(context)
                            .colorScheme
                            .onSurfaceVariant,
                        indicatorColor:
                            Theme.of(context).colorScheme.primary,
                      ),
                      const Divider(height: 1),
                      Expanded(
                        child: TabBarView(
                          children: [
                            _LiveFitnessChart(
                              history: viewModel.fitnessHistory,
                            ),
                            _ExpressionPanel(
                              groupActivityRates:
                                  viewModel.groupActivityRates,
                              avgActiveGenes:
                                  viewModel.avgActiveGenes,
                              totalGenes: 93,
                            ),
                            _OutputLogTab(viewModel: viewModel),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Icon(
            Icons.trending_up,
            size: 48,
            color: Theme.of(context).colorScheme.primary,
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Genetic Trader',
                style: Theme.of(context)
                    .textTheme
                    .headlineMedium
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
              Text(
                'AI-Powered Trading Strategy Evolution',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(
                      color: Theme.of(context)
                          .colorScheme
                          .onSurfaceVariant,
                    ),
              ),
            ],
          ),
          ),
          Flexible(
            child: Consumer<ResultsViewModel>(
              builder: (context, vm, _) {
                final results = vm.results;
                final totalRuns = results.length;
                String bestReturn = '-';
                if (results.isNotEmpty) {
                  final best = results
                      .map((r) =>
                          r.bestTrader.performance.totalReturn)
                      .reduce((a, b) => a > b ? a : b);
                  bestReturn =
                      '${best >= 0 ? '+' : ''}${best.toStringAsFixed(1)}%';
                }
                String lastRun = 'Never';
                if (results.isNotEmpty) {
                  lastRun = DateFormat('MMM d').format(
                    results.first.runDate,
                  );
                }
                return Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    _statChip(context, 'Runs', '$totalRuns'),
                    _statChip(context, 'Best', bestReturn),
                    _statChip(context, 'Last', lastRun),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _statChip(BuildContext context, String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Theme.of(context)
            .colorScheme
            .primaryContainer
            .withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            value,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: Theme.of(context)
                      .colorScheme
                      .onSurfaceVariant,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildControlCard(
    BuildContext context,
    EvolutionViewModel viewModel,
  ) {
    Widget content;

    if (!viewModel.isRunning && !viewModel.isCompleted) {
      content = Column(
        children: [
          Icon(
            Icons.rocket_launch,
            size: 56,
            color: Colors.deepPurple,
          ),
          const SizedBox(height: 8),
          Text(
            'Ready to Start Evolution',
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          Text(
            'Configure parameters on the left, then start.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey,
                ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Start Evolution'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      vertical: 18,
                    ),
                  ),
                  onPressed: () {
                    final cfg = context.read<ConfigViewModel>().config;
                    viewModel.startEvolution(config: cfg);
                  },
                ),
              ),
            ],
          ),
        ],
      );
    } else if (viewModel.isRunning) {
      content = Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Evolution Running...',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  Text(
                    'Gen ${viewModel.currentGeneration}'
                    '/${viewModel.totalGenerations}',
                    style: const TextStyle(
                      color: Colors.grey,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          LinearProgressIndicator(
            value: viewModel.progress.progress,
            minHeight: 8,
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              ElevatedButton.icon(
                icon: const Icon(Icons.stop),
                label: const Text('Stop'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                ),
                onPressed: () =>
                    _showStopDialog(context, viewModel),
              ),
            ],
          ),
        ],
      );
    } else {
      // Completed
      final hasError = viewModel.error != null;
      content = Column(
        children: [
          Icon(
            hasError ? Icons.error : Icons.check_circle,
            size: 48,
            color: hasError ? Colors.red : Colors.green,
          ),
          Text(
            hasError ? 'Evolution Failed' : 'Evolution Complete!',
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          if (hasError) ...[
            const SizedBox(height: 4),
            Text(
              viewModel.error!,
              style: const TextStyle(color: Colors.red),
              textAlign: TextAlign.center,
            ),
          ],
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton.icon(
                icon: const Icon(Icons.refresh),
                label: const Text('New Run'),
                onPressed: () => viewModel.reset(),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                icon: const Icon(Icons.fast_forward),
                label: const Text('Resume'),
                onPressed: viewModel.runId != null
                    ? () {
                        final runId = viewModel.runId!;
                        final cfg =
                            context.read<ConfigViewModel>().config;
                        viewModel.reset();
                        viewModel.startEvolution(
                          resumeRunId: runId,
                          config: cfg,
                        );
                      }
                    : null,
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                icon: const Icon(Icons.analytics),
                label: const Text('View Results'),
                onPressed: viewModel.runId != null
                    ? () {
                        final result = viewModel.buildResult();
                        if (result == null) return;
                        final resultsVm = ResultsViewModel();
                        resultsVm.selectResultWithHistory(
                          result,
                          viewModel.fitnessHistory,
                        );
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) =>
                                ChangeNotifierProvider.value(
                              value: resultsVm,
                              child:
                                  const ResultsDashboardScreen(),
                            ),
                          ),
                        );
                      }
                    : null,
              ),
            ],
          ),
        ],
      );
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: content,
      ),
    );
  }

  Widget _buildProgressStats(
    BuildContext context,
    EvolutionViewModel viewModel,
  ) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Expanded(
              child: _miniStat(
                context,
                Icons.trending_up,
                'Best',
                viewModel.bestFitness.toStringAsFixed(2),
                Colors.green,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _miniStat(
                context,
                Icons.show_chart,
                'Avg',
                viewModel.avgFitness.toStringAsFixed(2),
                Colors.blue,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _miniStat(
                context,
                Icons.trending_down,
                'Worst',
                viewModel.worstFitness.toStringAsFixed(2),
                Colors.grey,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _miniStat(
                context,
                Icons.flag,
                'Gen',
                '${viewModel.currentGeneration}'
                    '/${viewModel.totalGenerations}',
                Colors.deepPurple,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _miniStat(
    BuildContext context,
    IconData icon,
    String label,
    String value,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(label, style: TextStyle(fontSize: 10, color: color)),
        ],
      ),
    );
  }

  void _showStopDialog(
    BuildContext context,
    EvolutionViewModel viewModel,
  ) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Stop Evolution'),
        content: const Text(
          'Are you sure? Current progress will be lost.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              viewModel.stopEvolution();
              Navigator.pop(ctx);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Stop'),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────
// COMPACT SECTION / SLIDER HELPERS
// ─────────────────────────────────────────

Widget _compactSection(
  BuildContext context, {
  required IconData icon,
  required String title,
  String? subtitle,
  required List<Widget> children,
}) {
  return Card(
    margin: const EdgeInsets.only(bottom: 6),
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                icon,
                size: 18,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                title,
                style: Theme.of(context)
                    .textTheme
                    .titleSmall
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              if (subtitle != null)
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
            ],
          ),
          const SizedBox(height: 4),
          ...children,
        ],
      ),
    ),
  );
}

Widget _compactSlider(
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
  return Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                title,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 8,
                vertical: 2,
              ),
              decoration: BoxDecoration(
                color: Theme.of(context)
                    .colorScheme
                    .primaryContainer,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context)
                      .colorScheme
                      .onPrimaryContainer,
                ),
              ),
            ),
          ],
        ),
        if (subtitle != null)
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context)
                      .colorScheme
                      .onSurfaceVariant,
                ),
          ),
        SliderTheme(
          data: SliderThemeData(
            trackHeight: 3,
            thumbShape: const RoundSliderThumbShape(
              enabledThumbRadius: 7,
            ),
            overlayShape: const RoundSliderOverlayShape(
              overlayRadius: 14,
            ),
          ),
          child: Slider(
            value: value,
            min: min,
            max: max,
            divisions: divisions,
            label: label,
            onChanged: onChanged,
          ),
        ),
      ],
    ),
  );
}

// ─────────────────────────────────────────
// SHARED HELPERS
// ─────────────────────────────────────────

String _formatWeightName(String key) {
  return key
      .split('_')
      .map((w) => w[0].toUpperCase() + w.substring(1))
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
    final foldStart =
        start.add(Duration(days: (i * stride).toInt()));
    var foldEnd =
        foldStart.add(Duration(days: foldDays - 1));
    if (foldEnd.isAfter(end)) foldEnd = end;
    folds.add(
      'Fold ${i + 1}: ${_fmtDate(foldStart)} - ${_fmtDate(foldEnd)}',
    );
  }
  if (!allowOverlap && config.kfoldNumFolds > numFolds) {
    folds.add(
      '(Capped to $numFolds — not enough data)',
    );
  }
  return folds.join('\n');
}

String _fmtDate(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}';

// ─────────────────────────────────────────
// DIALOGS
// ─────────────────────────────────────────

void _showResetDialog(BuildContext context) {
  showDialog(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Reset Configuration'),
      content: const Text('Reset all settings to defaults?'),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: () {
            context.read<ConfigViewModel>().resetToDefaults();
            Navigator.pop(ctx);
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

void _showCashCommissionDialog(
  BuildContext context,
  ConfigViewModel viewModel,
  config,
) {
  final cashCtrl = TextEditingController(
    text: config.initialCash.toStringAsFixed(0),
  );
  final commCtrl = TextEditingController(
    text: (config.commission * 100).toString(),
  );
  showDialog(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Edit Cash & Commission'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: cashCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Initial Cash (\$)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: commCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Commission (%)',
              border: OutlineInputBorder(),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: () {
            final cash = double.tryParse(cashCtrl.text);
            if (cash != null) viewModel.updateInitialCash(cash);
            final pct = double.tryParse(commCtrl.text);
            if (pct != null) viewModel.updateCommission(pct / 100);
            Navigator.pop(ctx);
          },
          child: const Text('Save'),
        ),
      ],
    ),
  );
}

// ─────────────────────────────────────────
// PRIVATE WIDGET CLASSES (from config_screen)
// ─────────────────────────────────────────

/// Computes the deduplicated symbol count across selected indices.
int _totalSymbolCount(Set<String> selectedIndices) {
  final symbols = <String>{};
  for (final name in selectedIndices) {
    final idx = IndexType.values.firstWhere(
      (t) => t.name.toUpperCase() == name.toUpperCase(),
      orElse: () => IndexType.djia,
    );
    symbols.addAll(IndexService.getSymbols(idx));
  }
  return symbols.length;
}

/// Multi-select index picker with database status and sync button.
class _IndexSelector extends StatefulWidget {
  const _IndexSelector({
    required this.selectedIndices,
    required this.onToggle,
  });

  final Set<String> selectedIndices;
  final ValueChanged<String> onToggle;

  @override
  State<_IndexSelector> createState() => _IndexSelectorState();
}

class _IndexSelectorState extends State<_IndexSelector> {
  bool _isSyncing = false;
  int _syncDone = 0;
  int _syncTotal = 0;
  String? _syncError;
  bool _dbReady = false;
  bool _dbChecked = false;

  @override
  void initState() {
    super.initState();
    _checkDatabase();
  }

  Future<void> _checkDatabase() async {
    try {
      final db = DatabaseService();
      await db.open();
      final symbols = IndexService.getSymbols(IndexType.djia);
      final count = await db.getBarCount(symbols.first);
      if (!mounted) return;
      setState(() {
        _dbReady = count > 0;
        _dbChecked = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _dbReady = false;
        _dbChecked = true;
      });
    }
  }

  Future<void> _syncData() async {
    setState(() {
      _isSyncing = true;
      _syncDone = 0;
      _syncTotal = 0;
      _syncError = null;
    });

    try {
      final db = DatabaseService();
      await db.open();
      final yahoo = YahooFinanceService();
      final syncService = DataSyncService(yahoo: yahoo, db: db);

      final indices = <IndexType>{};
      for (final name in widget.selectedIndices) {
        final idx = IndexType.values.firstWhere(
          (t) => t.name.toUpperCase() == name.toUpperCase(),
          orElse: () => IndexType.djia,
        );
        indices.add(idx);
      }

      final result = await syncService.syncIndices(
        indices,
        onProgress: (done, total) {
          if (!mounted) return;
          setState(() {
            _syncDone = done;
            _syncTotal = total;
          });
        },
      );

      if (!mounted) return;
      setState(() {
        _isSyncing = false;
        _dbReady = true;
        if (result.symbolsFailed > 0) {
          _syncError = '${result.symbolsSynced} synced, '
              '${result.symbolsFailed} failed';
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isSyncing = false;
        _syncError = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Index checkboxes
        for (final entry in [
          ('DJIA', 'Dow Jones', 30),
          ('SP500', 'S&P 500', 503),
          ('NASDAQ100', 'Nasdaq-100', 100),
        ])
          CheckboxListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            title: Text(
              entry.$2,
              style: const TextStyle(fontSize: 13),
            ),
            subtitle: Text(
              '${entry.$3} stocks',
              style: TextStyle(fontSize: 11, color: cs.outline),
            ),
            value: widget.selectedIndices.contains(entry.$1),
            onChanged: (_) => widget.onToggle(entry.$1),
          ),

        const SizedBox(height: 8),

        // Database status
        if (_dbChecked)
          Row(
            children: [
              Icon(
                _dbReady
                    ? Icons.check_circle
                    : Icons.warning_amber,
                size: 16,
                color: _dbReady ? cs.primary : cs.error,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _dbReady
                      ? 'Database ready'
                      : 'No data — sync from Yahoo Finance',
                  style: TextStyle(
                    fontSize: 12,
                    color: _dbReady
                        ? cs.onSurfaceVariant
                        : cs.error,
                  ),
                ),
              ),
            ],
          ),

        const SizedBox(height: 8),

        // Sync progress bar
        if (_isSyncing && _syncTotal > 0) ...[
          LinearProgressIndicator(
            value: _syncDone / _syncTotal,
          ),
          const SizedBox(height: 4),
          Text(
            'Syncing $_syncDone / $_syncTotal symbols...',
            style: TextStyle(fontSize: 11, color: cs.outline),
          ),
          const SizedBox(height: 8),
        ],

        // Error message
        if (_syncError != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              _syncError!,
              style: TextStyle(fontSize: 11, color: cs.error),
            ),
          ),

        // Sync button
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: _isSyncing ? null : _syncData,
            icon: _isSyncing
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                    ),
                  )
                : const Icon(Icons.sync, size: 18),
            label: Text(
              _isSyncing
                  ? 'Syncing...'
                  : _dbReady
                      ? 'Re-sync Data'
                      : 'Sync from Yahoo Finance',
            ),
          ),
        ),
      ],
    );
  }
}

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
    if (start == null || end == null) return const SizedBox.shrink();

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
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
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
              const SizedBox(width: 6),
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
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'Warning: No test data. Reduce training years.',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.error,
                  fontSize: 11,
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
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: color,
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            '$startDate\n$endDate',
            style: const TextStyle(fontSize: 10),
          ),
        ],
      ),
    );
  }
}

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
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Sectors',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const Spacer(),
              if (selectedSectors.isNotEmpty)
                TextButton(
                  onPressed: onClearAll,
                  style: TextButton.styleFrom(
                    padding: EdgeInsets.zero,
                    minimumSize: const Size(0, 24),
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: const Text('Clear', style: TextStyle(fontSize: 11)),
                ),
            ],
          ),
          Wrap(
            spacing: 6,
            runSpacing: 2,
            children: _availableSectors.map((sector) {
              return FilterChip(
                label: Text(
                  sector,
                  style: const TextStyle(fontSize: 11),
                ),
                selected: selectedSectors.contains(sector),
                onSelected: (_) => onToggle(sector),
                showCheckmark: true,
                materialTapTargetSize:
                    MaterialTapTargetSize.shrinkWrap,
                visualDensity: VisualDensity.compact,
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

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
      if (!updated.contains(sym)) updated.add(sym);
    }
    _controller.clear();
    widget.onChanged(updated);
  }

  void _removeSymbol(String symbol) {
    final updated = List<String>.from(widget.stocks)..remove(symbol);
    widget.onChanged(updated);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _controller,
            textCapitalization: TextCapitalization.characters,
            style: const TextStyle(fontSize: 13),
            decoration: InputDecoration(
              labelText: 'Add symbols',
              hintText: 'AAPL, MSFT',
              isDense: true,
              border: const OutlineInputBorder(),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 10,
                vertical: 8,
              ),
              suffixIcon: IconButton(
                icon: const Icon(Icons.add, size: 18),
                onPressed: () => _addSymbols(_controller.text),
              ),
            ),
            onSubmitted: _addSymbols,
          ),
          const SizedBox(height: 4),
          if (widget.stocks.isNotEmpty)
            Wrap(
              spacing: 4,
              runSpacing: 2,
              children: widget.stocks
                  .map(
                    (sym) => Chip(
                      label: Text(sym, style: const TextStyle(fontSize: 11)),
                      deleteIcon: const Icon(Icons.close, size: 14),
                      onDeleted: () => _removeSymbol(sym),
                      materialTapTargetSize:
                          MaterialTapTargetSize.shrinkWrap,
                      visualDensity: VisualDensity.compact,
                    ),
                  )
                  .toList(),
            )
          else
            Text(
              'No stocks added',
              style: TextStyle(
                fontSize: 11,
                color: Theme.of(context).colorScheme.error,
              ),
            ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────
// PRIVATE WIDGET CLASSES (from evolution_screen)
// ─────────────────────────────────────────

class _LiveFitnessChart extends StatelessWidget {
  final List<FitnessHistoryEntry> history;

  const _LiveFitnessChart({required this.history});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.show_chart,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 12),
              Text(
                'Fitness Evolution',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: history.isEmpty
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.hourglass_empty,
                          size: 48,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Waiting for first generation...',
                          style: TextStyle(color: Colors.grey[600]),
                        ),
                      ],
                    ),
                  )
                : _buildChart(context),
          ),
          if (history.isNotEmpty) ...[
            const SizedBox(height: 12),
            _buildLegend(context),
          ],
        ],
      ),
    );
  }

  Widget _buildChart(BuildContext context) {
    final primaryColor = Theme.of(context).colorScheme.primary;

    double minY = double.infinity;
    double maxY = double.negativeInfinity;
    for (final entry in history) {
      if (entry.worstFitness < minY) minY = entry.worstFitness;
      if (entry.bestFitness > maxY) maxY = entry.bestFitness;
    }
    final yPadding = (maxY - minY) * 0.1;
    if (yPadding < 1) {
      minY -= 5;
      maxY += 5;
    } else {
      minY -= yPadding;
      maxY += yPadding;
    }

    return LineChart(
      LineChartData(
        minX: history.first.generation.toDouble(),
        maxX: history.last.generation.toDouble(),
        minY: minY,
        maxY: maxY,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (value) => FlLine(
            color: Colors.grey.withValues(alpha: 0.2),
            strokeWidth: 1,
          ),
        ),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          bottomTitles: AxisTitles(
            axisNameWidget: const Text(
              'Generation',
              style: TextStyle(fontSize: 12),
            ),
            sideTitles: SideTitles(
              showTitles: true,
              interval: _computeInterval(history.length),
              getTitlesWidget: (value, meta) {
                return Text(
                  value.toInt().toString(),
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          leftTitles: AxisTitles(
            axisNameWidget: const Text(
              'Fitness',
              style: TextStyle(fontSize: 12),
            ),
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 50,
              getTitlesWidget: (value, meta) {
                return Text(
                  value.toStringAsFixed(1),
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            fitInsideHorizontally: true,
            fitInsideVertically: true,
            getTooltipItems: (touchedSpots) {
              String? geneText;
              if (touchedSpots.isNotEmpty) {
                final gen = touchedSpots.first.x.toInt();
                final entry = history
                    .cast<FitnessHistoryEntry?>()
                    .firstWhere(
                      (e) => e!.generation == gen,
                      orElse: () => null,
                    );
                if (entry?.geneChanges != null &&
                    entry!.geneChanges!.isNotEmpty) {
                  final changes = entry.geneChanges!;
                  const maxShow = 4;
                  final lines = changes
                      .take(maxShow)
                      .map(
                        (gc) => '${_shortGeneName(gc.gene)}: '
                            '${gc.oldValue}\u2192${gc.newValue}',
                      )
                      .join('\n');
                  final extra = changes.length > maxShow
                      ? '\n+${changes.length - maxShow} more'
                      : '';
                  geneText = '\n\nGene changes:\n$lines$extra';
                }
              }
              return touchedSpots.map((spot) {
                final labels = ['Best', 'Avg', 'Worst'];
                final colors = [
                  primaryColor,
                  Colors.orange,
                  Colors.grey,
                ];
                final isLast =
                    spot.barIndex == touchedSpots.length - 1;
                return LineTooltipItem(
                  '${labels[spot.barIndex]}: '
                  '${spot.y.toStringAsFixed(2)}',
                  TextStyle(
                    color: colors[spot.barIndex],
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                  children: isLast && geneText != null
                      ? [
                          TextSpan(
                            text: geneText,
                            style: TextStyle(
                              color: Colors.greenAccent
                                  .withValues(alpha: 0.9),
                              fontSize: 10,
                              fontWeight: FontWeight.normal,
                              height: 1.4,
                            ),
                          ),
                        ]
                      : null,
                );
              }).toList();
            },
          ),
        ),
        lineBarsData: [
          LineChartBarData(
            spots: history
                .map((e) => FlSpot(
                      e.generation.toDouble(),
                      e.bestFitness,
                    ))
                .toList(),
            isCurved: true,
            color: primaryColor,
            barWidth: 3,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: primaryColor.withValues(alpha: 0.1),
            ),
          ),
          LineChartBarData(
            spots: history
                .map((e) => FlSpot(
                      e.generation.toDouble(),
                      e.avgFitness,
                    ))
                .toList(),
            isCurved: true,
            color: Colors.orange,
            barWidth: 2,
            dotData: const FlDotData(show: false),
          ),
          LineChartBarData(
            spots: history
                .map((e) => FlSpot(
                      e.generation.toDouble(),
                      e.worstFitness,
                    ))
                .toList(),
            isCurved: true,
            color: Colors.grey,
            barWidth: 1,
            dashArray: [5, 5],
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }

  double _computeInterval(int count) {
    if (count <= 10) return 1;
    if (count <= 30) return 5;
    if (count <= 60) return 10;
    return 20;
  }

  String _shortGeneName(String name) {
    const abbrevs = {
      'ma_short_period': 'ma_short',
      'ma_long_period': 'ma_long',
      'stop_loss_pct': 'stop_loss',
      'take_profit_pct': 'take_profit',
      'position_size_pct': 'pos_size',
      'macro_enabled': 'macro_on',
      'macro_weight': 'macro_wt',
      'macro_vix_threshold': 'vix_thresh',
      'macro_vix_position_scale': 'vix_scale',
      'macro_yc_threshold': 'yc_thresh',
      'macro_yc_action': 'yc_action',
      'macro_rate_threshold': 'rate_thresh',
      'macro_rate_position_scale': 'rate_scale',
      'macro_cpi_threshold': 'cpi_thresh',
      'macro_cpi_position_scale': 'cpi_scale',
      'macro_unemp_threshold': 'unemp_thresh',
      'macro_unemp_action': 'unemp_act',
      'macro_risk_stop_adj': 'risk_stop',
      'macro_risk_tp_adj': 'risk_tp',
      'macro_regime_count_req': 'regime_req',
      'ti_enabled': 'ti_on',
      'ti_rsi_overbought': 'rsi_ob',
      'ti_rsi_oversold': 'rsi_os',
      'ti_adx_threshold': 'adx_thresh',
      'ti_adx_position_scale': 'adx_scale',
      'ti_natr_threshold': 'natr_thresh',
      'ti_natr_risk_action': 'natr_act',
      'ti_mfi_overbought': 'mfi_ob',
      'ti_mfi_oversold': 'mfi_os',
      'ti_macdhist_confirm': 'macd_conf',
      'ti_macdhist_exit_confirm': 'macd_exit',
      'ensemble_enabled': 'ens_on',
      'sig_ma_weight': 'sig_ma',
      'sig_bb_weight': 'sig_bb',
      'sig_stoch_weight': 'sig_stoch',
      'sig_macd_weight': 'sig_macd',
      'sig_rsi_weight': 'sig_rsi',
      'sig_buy_threshold': 'buy_thresh',
      'sig_sell_threshold': 'sell_thresh',
      'sig_bb_period_idx': 'bb_period',
      'sig_stoch_ob': 'stoch_ob',
      'sig_stoch_os': 'stoch_os',
      'sig_rsi_ob': 'rsi_ob',
      'sig_rsi_os': 'rsi_os',
    };
    return abbrevs[name] ?? name;
  }

  Widget _buildLegend(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _LegendItem(
          color: Theme.of(context).colorScheme.primary,
          label: 'Best',
        ),
        const SizedBox(width: 24),
        const _LegendItem(color: Colors.orange, label: 'Average'),
        const SizedBox(width: 24),
        const _LegendItem(color: Colors.grey, label: 'Worst'),
      ],
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 3,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

/// Expression panel showing group activity rates as a bar chart.
class _ExpressionPanel extends StatelessWidget {
  final Map<String, double> groupActivityRates;
  final int avgActiveGenes;
  final int totalGenes;

  const _ExpressionPanel({
    required this.groupActivityRates,
    required this.avgActiveGenes,
    required this.totalGenes,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.tune,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 12),
              Text(
                'Gene Expression',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: Theme.of(context)
                      .colorScheme
                      .primaryContainer,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Text(
                  'Active: $avgActiveGenes / $totalGenes',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Theme.of(context)
                        .colorScheme
                        .onPrimaryContainer,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: groupActivityRates.isEmpty
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.hourglass_empty,
                          size: 48,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Waiting for first generation...',
                          style: TextStyle(
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                  )
                : _buildBarChart(context),
          ),
        ],
      ),
    );
  }

  Widget _buildBarChart(BuildContext context) {
    final entries = groupActivityRates.entries.toList();

    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: 1.0,
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              final name = entries[group.x.toInt()].key;
              final pct = (rod.toY * 100).toStringAsFixed(0);
              return BarTooltipItem(
                '$name\n$pct% active',
                const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              );
            },
          ),
        ),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return Text(
                  '${(value * 100).toInt()}%',
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (value, meta) {
                final idx = value.toInt();
                if (idx < 0 || idx >= entries.length) {
                  return const SizedBox.shrink();
                }
                return Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: RotatedBox(
                    quarterTurns: -1,
                    child: Text(
                      _shortGroupName(entries[idx].key),
                      style: const TextStyle(fontSize: 10),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (value) => FlLine(
            color: Colors.grey.withValues(alpha: 0.2),
            strokeWidth: 1,
          ),
        ),
        barGroups: List.generate(entries.length, (i) {
          final rate = entries[i].value;
          return BarChartGroupData(
            x: i,
            barRods: [
              BarChartRodData(
                toY: rate,
                width: 16,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(4),
                  topRight: Radius.circular(4),
                ),
                color: _barColor(rate, context),
                backDrawRodData: BackgroundBarChartRodData(
                  show: true,
                  toY: 1.0,
                  color: Colors.grey.withValues(alpha: 0.1),
                ),
              ),
            ],
          );
        }),
      ),
    );
  }

  Color _barColor(double rate, BuildContext context) {
    if (rate > 0.7) return Colors.green;
    if (rate > 0.3) return Colors.orange;
    return Colors.grey;
  }

  String _shortGroupName(String name) {
    const labels = {
      'core': 'Core',
      'macro': 'Macro',
      'technical_indicators': 'TI Filters',
      'ensemble': 'Ensemble',
      'advanced_oscillators': 'Adv Osc',
      'trend_signals': 'Trend',
      'volume_signals': 'Volume',
      'volatility_breakout': 'Vol Brk',
      'support_resistance': 'S/R',
      'regime_detection': 'Regime',
      'advanced_sizing': 'Sizing',
    };
    return labels[name] ?? name;
  }
}

class _OutputLogTab extends StatelessWidget {
  final EvolutionViewModel viewModel;

  const _OutputLogTab({required this.viewModel});

  @override
  Widget build(BuildContext context) {
    if (viewModel.outputLines.isEmpty) {
      return Center(
        child: Text(
          'No output yet.',
          style: TextStyle(color: Colors.grey[600]),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: viewModel.outputLines.length,
      itemBuilder: (context, index) {
        final line = viewModel.outputLines[index];
        final isError = line.startsWith('ERROR:');

        return Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Text(
            line,
            style: TextStyle(
              fontFamily: 'monospace',
              fontSize: 12,
              color: isError
                  ? Colors.red
                  : Theme.of(context).textTheme.bodyMedium?.color,
            ),
          ),
        );
      },
    );
  }
}
