import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../models/evolution_result.dart';
import '../../viewmodels/results_viewmodel.dart';

/// Dashboard screen showing detailed results for a single evolution run
class ResultsDashboardScreen extends StatelessWidget {
  const ResultsDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ResultsViewModel>(
      builder: (context, viewModel, child) {
        final result = viewModel.selectedResult;

        if (viewModel.isLoading) {
          return Scaffold(
            appBar: AppBar(title: const Text('Run Results')),
            body: const Center(child: CircularProgressIndicator()),
          );
        }

        if (result == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Run Results')),
            body: const Center(child: Text('No result selected')),
          );
        }

        final dateFormat = DateFormat('MMMM d, yyyy  HH:mm');

        return Scaffold(
          appBar: AppBar(
            title: Text('Run ${dateFormat.format(result.runDate)}'),
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _PerformanceSummary(result: result),
              const SizedBox(height: 16),
              _BenchmarkComparison(result: result),
              const SizedBox(height: 16),
              _FitnessChart(history: viewModel.fitnessHistory),
              const SizedBox(height: 16),
              _RunConfiguration(result: result),
              const SizedBox(height: 16),
              _BestTraderGenes(genes: result.bestTrader.genes),
              const SizedBox(height: 16),
              _PortfolioStocks(symbols: result.portfolioSymbols),
              const SizedBox(height: 32),
            ],
          ),
        );
      },
    );
  }
}

/// Top row of performance metric cards
class _PerformanceSummary extends StatelessWidget {
  final EvolutionResult result;

  const _PerformanceSummary({required this.result});

  @override
  Widget build(BuildContext context) {
    final perf = result.bestTrader.performance;
    final isPositive = perf.totalReturn >= 0;

    return Row(
      children: [
        Expanded(
          child: _MetricCard(
            icon: Icons.trending_up,
            label: 'Total Return',
            value:
                '${isPositive ? '+' : ''}${perf.totalReturn.toStringAsFixed(1)}%',
            color: isPositive ? Colors.green : Colors.red,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _MetricCard(
            icon: Icons.speed,
            label: 'Sharpe Ratio',
            value: perf.sharpeRatio.toStringAsFixed(3),
            color: perf.sharpeRatio > 0.5
                ? Colors.green
                : perf.sharpeRatio > 0
                ? Colors.orange
                : Colors.red,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _MetricCard(
            icon: Icons.waterfall_chart,
            label: 'Max Drawdown',
            value: '${perf.maxDrawdown.toStringAsFixed(1)}%',
            color: perf.maxDrawdown > -20
                ? Colors.green
                : perf.maxDrawdown > -40
                ? Colors.orange
                : Colors.red,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _MetricCard(
            icon: Icons.pie_chart,
            label: 'Win Rate',
            value: '${perf.winRate.toStringAsFixed(1)}%',
            color: perf.winRate > 50
                ? Colors.green
                : perf.winRate > 40
                ? Colors.orange
                : Colors.red,
          ),
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _MetricCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

/// Benchmark comparison card
class _BenchmarkComparison extends StatelessWidget {
  final EvolutionResult result;

  const _BenchmarkComparison({required this.result});

  @override
  Widget build(BuildContext context) {
    final perf = result.bestTrader.performance;
    final bench = result.benchmark;
    final beats = bench.beatsBenchmark;
    final outperf = bench.outperformance;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.balance,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Text(
                  'Benchmark Comparison',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _ComparisonBar(
                    label: 'Strategy',
                    value: perf.totalReturn,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _ComparisonBar(
                    label: 'Buy & Hold (${bench.allocationPct.toInt()}%)',
                    value: bench.buyAndHoldReturn,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: beats
                    ? Colors.green.withValues(alpha: 0.1)
                    : Colors.red.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: beats
                      ? Colors.green.withValues(alpha: 0.3)
                      : Colors.red.withValues(alpha: 0.3),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    beats ? Icons.check_circle : Icons.warning,
                    color: beats ? Colors.green : Colors.red,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    beats
                        ? 'Outperforms benchmark by +${outperf.toStringAsFixed(2)}%'
                        : 'Underperforms benchmark by ${outperf.toStringAsFixed(2)}%',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: beats ? Colors.green : Colors.red,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ComparisonBar extends StatelessWidget {
  final String label;
  final double value;
  final Color color;

  const _ComparisonBar({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final isPositive = value >= 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '${isPositive ? '+' : ''}${value.toStringAsFixed(2)}%',
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }
}

/// Fitness evolution chart using fl_chart
class _FitnessChart extends StatelessWidget {
  final List<FitnessHistoryEntry>? history;

  const _FitnessChart({required this.history});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
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
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (history == null || history!.isEmpty)
              const SizedBox(
                height: 200,
                child: Center(child: Text('No history data available')),
              )
            else
              SizedBox(height: 250, child: _buildChart(context)),
            if (history != null && history!.isNotEmpty) ...[
              const SizedBox(height: 12),
              _buildLegend(context),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildChart(BuildContext context) {
    final entries = history!;
    final primaryColor = Theme.of(context).colorScheme.primary;

    // Calculate Y-axis bounds with padding
    double minY = double.infinity;
    double maxY = double.negativeInfinity;
    for (final entry in entries) {
      if (entry.worstFitness < minY) minY = entry.worstFitness;
      if (entry.bestFitness > maxY) maxY = entry.bestFitness;
    }
    final yPadding = (maxY - minY) * 0.1;
    if (yPadding < 1) {
      // If all values are the same, add some padding
      minY -= 5;
      maxY += 5;
    } else {
      minY -= yPadding;
      maxY += yPadding;
    }

    return LineChart(
      LineChartData(
        minX: 0,
        maxX: (entries.length - 1).toDouble(),
        minY: minY,
        maxY: maxY,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (value) =>
              FlLine(color: Colors.grey.withValues(alpha: 0.2), strokeWidth: 1),
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
              interval: _computeInterval(entries.length),
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
            getTooltipItems: (touchedSpots) {
              return touchedSpots.map((spot) {
                final labels = ['Best', 'Avg', 'Worst'];
                final colors = [primaryColor, Colors.orange, Colors.grey];
                return LineTooltipItem(
                  '${labels[spot.barIndex]}: '
                  '${spot.y.toStringAsFixed(2)}',
                  TextStyle(
                    color: colors[spot.barIndex],
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                );
              }).toList();
            },
          ),
        ),
        lineBarsData: [
          // Best fitness line
          LineChartBarData(
            spots: entries
                .map((e) => FlSpot(e.generation.toDouble(), e.bestFitness))
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
          // Average fitness line
          LineChartBarData(
            spots: entries
                .map((e) => FlSpot(e.generation.toDouble(), e.avgFitness))
                .toList(),
            isCurved: true,
            color: Colors.orange,
            barWidth: 2,
            dotData: const FlDotData(show: false),
          ),
          // Worst fitness line
          LineChartBarData(
            spots: entries
                .map((e) => FlSpot(e.generation.toDouble(), e.worstFitness))
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

/// Run configuration card
class _RunConfiguration extends StatelessWidget {
  final EvolutionResult result;

  const _RunConfiguration({required this.result});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.settings,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Text(
                  'Run Configuration',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _ConfigRow(label: 'Mode', value: result.mode.toUpperCase()),
            _ConfigRow(
              label: 'Date Range',
              value: '${result.startDate}  to  ${result.endDate}',
            ),
            _ConfigRow(
              label: 'Population',
              value: '${result.populationSize} traders',
            ),
            _ConfigRow(label: 'Generations', value: '${result.numGenerations}'),
            _ConfigRow(
              label: 'Portfolio Size',
              value: '${result.portfolioSize} stocks',
            ),
            _ConfigRow(
              label: 'Initial Allocation',
              value: '${result.initialAllocationPct.toInt()}%',
            ),
            _ConfigRow(
              label: 'Total Trades',
              value: '${result.bestTrader.performance.tradeCount}',
            ),
            _ConfigRow(
              label: 'Best Generation',
              value: '${result.bestTrader.generation + 1}',
            ),
          ],
        ),
      ),
    );
  }
}

class _ConfigRow extends StatelessWidget {
  final String label;
  final String value;

  const _ConfigRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 140,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

/// Best trader genes display
class _BestTraderGenes extends StatelessWidget {
  final Map<String, dynamic> genes;

  const _BestTraderGenes({required this.genes});

  @override
  Widget build(BuildContext context) {
    // Group genes by category
    final maGenes = <String, dynamic>{};
    final riskGenes = <String, dynamic>{};
    final macroGenes = <String, dynamic>{};
    final tiGenes = <String, dynamic>{};
    final ensembleGenes = <String, dynamic>{};

    for (final entry in genes.entries) {
      if (entry.key.startsWith('ma_')) {
        maGenes[entry.key] = entry.value;
      } else if ([
        'stop_loss_pct',
        'take_profit_pct',
        'position_size_pct',
      ].contains(entry.key)) {
        riskGenes[entry.key] = entry.value;
      } else if (entry.key.startsWith('macro_')) {
        macroGenes[entry.key] = entry.value;
      } else if (entry.key.startsWith('ti_')) {
        tiGenes[entry.key] = entry.value;
      } else if (entry.key.startsWith('ensemble_') ||
          entry.key.startsWith('sig_')) {
        ensembleGenes[entry.key] = entry.value;
      }
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.psychology,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Text(
                  'Best Trader Genes',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _GeneGroup(
              title: 'MA Strategy',
              icon: Icons.show_chart,
              genes: maGenes,
            ),
            _GeneGroup(
              title: 'Risk Management',
              icon: Icons.shield,
              genes: riskGenes,
            ),
            if (macroGenes.isNotEmpty)
              _GeneGroup(
                title: 'Macro Filters',
                icon: Icons.public,
                genes: macroGenes,
              ),
            if (tiGenes.isNotEmpty)
              _GeneGroup(
                title: 'Technical Indicators',
                icon: Icons.analytics,
                genes: tiGenes,
              ),
            if (ensembleGenes.isNotEmpty)
              _GeneGroup(
                title: 'Ensemble Signals',
                icon: Icons.merge_type,
                genes: ensembleGenes,
              ),
          ],
        ),
      ),
    );
  }
}

class _GeneGroup extends StatelessWidget {
  final String title;
  final IconData icon;
  final Map<String, dynamic> genes;

  const _GeneGroup({
    required this.title,
    required this.icon,
    required this.genes,
  });

  @override
  Widget build(BuildContext context) {
    return ExpansionTile(
      leading: Icon(icon, size: 20),
      title: Text(
        '$title (${genes.length})',
        style: const TextStyle(fontWeight: FontWeight.w600),
      ),
      children: genes.entries.map((entry) {
        final formattedValue = _formatGeneValue(entry.value);
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
          child: Row(
            children: [
              SizedBox(
                width: 200,
                child: Text(
                  _formatGeneName(entry.key),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  formattedValue,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  String _formatGeneName(String key) {
    return key
        .replaceAll('_', ' ')
        .split(' ')
        .map(
          (w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '',
        )
        .join(' ');
  }

  String _formatGeneValue(dynamic value) {
    if (value is double) {
      return value.toStringAsFixed(4);
    }
    return value.toString();
  }
}

/// Portfolio stocks chip display
class _PortfolioStocks extends StatelessWidget {
  final List<String> symbols;

  const _PortfolioStocks({required this.symbols});

  @override
  Widget build(BuildContext context) {
    if (symbols.isEmpty) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.account_balance,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Text(
                  'Portfolio Stocks (${symbols.length})',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: symbols
                  .map(
                    (symbol) => Chip(
                      label: Text(
                        symbol,
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 12,
                        ),
                      ),
                      backgroundColor: Theme.of(
                        context,
                      ).colorScheme.primaryContainer.withValues(alpha: 0.5),
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }
}
