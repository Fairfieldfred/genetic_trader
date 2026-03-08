import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../models/evolution_result.dart';
import '../../viewmodels/results_viewmodel.dart';
import 'evolution_screen.dart';

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
            actions: [
              TextButton.icon(
                icon: const Icon(Icons.fast_forward),
                label: const Text('Resume'),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => EvolutionScreen(
                        resumeRunId: result.runId,
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _PerformanceSummary(result: result),
              const SizedBox(height: 16),
              _BenchmarkComparison(result: result),
              if (result.outOfSample != null) ...[
                const SizedBox(height: 16),
                _OutOfSampleSection(
                  trainPerformance:
                      result.bestTrader.performance,
                  oos: result.outOfSample!,
                  trainStartDate: result.startDate,
                  trainEndDate: result.endDate,
                ),
              ],
              const SizedBox(height: 16),
              _TradeDistribution(
                perStock: result.bestTrader.perStockPerformance,
              ),
              const SizedBox(height: 16),
              _ProfitContribution(
                perStock: result.bestTrader.perStockPerformance,
              ),
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

  void _showMaxDrawdownInfo(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(
              Icons.waterfall_chart,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(width: 12),
            const Text('Max Drawdown'),
          ],
        ),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'What is Max Drawdown?',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'Max drawdown measures the largest peak-to-trough '
                'decline in portfolio value during a backtest. For '
                'example, if the portfolio grows to \$120,000 then '
                'drops to \$90,000 before recovering, that\'s a '
                '-25% drawdown.',
              ),
              SizedBox(height: 16),
              Text(
                'How it factors into fitness',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'The fitness score is a weighted sum of four metrics:\n\n'
                '  fitness = W1 \u00d7 total_return\n'
                '         + W2 \u00d7 sharpe_ratio\n'
                '         + W3 \u00d7 max_drawdown\n'
                '         + W4 \u00d7 win_rate\n\n'
                'Max drawdown is always negative (or zero), so a '
                'less negative drawdown contributes a higher fitness '
                'score. A trader with -10% max drawdown gets a better '
                'fitness contribution than one with -40%.',
              ),
              SizedBox(height: 16),
              Text(
                'The evolutionary effect',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'The drawdown weight creates selection pressure against '
                'strategies that achieve high returns but with dangerous '
                'dips. A trader returning +50% with a -60% drawdown '
                'will often lose in tournament selection to one '
                'returning +30% with only -15% drawdown.',
              ),
              SizedBox(height: 16),
              Text(
                'Tuning the weight',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                '\u2022 Higher drawdown weight \u2192 evolution favors '
                'conservative, steady strategies\n'
                '\u2022 Lower drawdown weight \u2192 evolution favors '
                'aggressive, high-return strategies that may have '
                'volatile equity curves\n\n'
                'Increase it if you want strategies that are more '
                '"survivable" in live trading, or decrease it if you '
                'care more about raw returns and can tolerate the '
                'volatility.',
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Got it'),
          ),
        ],
      ),
    );
  }

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
            onInfoTap: () => _showMaxDrawdownInfo(context),
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
  final VoidCallback? onInfoTap;

  const _MetricCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    this.onInfoTap,
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
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Flexible(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
                if (onInfoTap != null) ...[
                  const SizedBox(width: 4),
                  GestureDetector(
                    onTap: onInfoTap,
                    child: Icon(
                      Icons.info_outline,
                      size: 16,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ],
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

/// Out-of-sample test results comparison
class _OutOfSampleSection extends StatelessWidget {
  final TraderPerformance trainPerformance;
  final OutOfSampleResult oos;
  final String trainStartDate;
  final String trainEndDate;

  const _OutOfSampleSection({
    required this.trainPerformance,
    required this.oos,
    required this.trainStartDate,
    required this.trainEndDate,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (oos.error != null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _sectionHeader(context),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Test failed: ${oos.error}',
                  style: TextStyle(
                    color: theme.colorScheme.error,
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final testPerf = oos.performance;
    if (testPerf == null) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionHeader(context),
            const SizedBox(height: 8),
            Text(
              'Trained: $trainStartDate to $trainEndDate  '
              '|  Tested: ${oos.testStartDate} to '
              '${oos.testEndDate}',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _MetricCompare(
                    label: 'Total Return',
                    trainValue: trainPerformance.totalReturn,
                    testValue: testPerf.totalReturn,
                    suffix: '%',
                    signed: true,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _MetricCompare(
                    label: 'Sharpe Ratio',
                    trainValue: trainPerformance.sharpeRatio,
                    testValue: testPerf.sharpeRatio,
                    decimals: 3,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _MetricCompare(
                    label: 'Max Drawdown',
                    trainValue: trainPerformance.maxDrawdown,
                    testValue: testPerf.maxDrawdown,
                    suffix: '%',
                    invertColor: true,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _MetricCompare(
                    label: 'Win Rate',
                    trainValue: trainPerformance.winRate,
                    testValue: testPerf.winRate,
                    suffix: '%',
                  ),
                ),
              ],
            ),
            if (oos.benchmark != null) ...[
              const SizedBox(height: 16),
              _testBenchmarkRow(context),
            ],
          ],
        ),
      ),
    );
  }

  Widget _sectionHeader(BuildContext context) {
    return Row(
      children: [
        Icon(
          Icons.science,
          color: Theme.of(context).colorScheme.tertiary,
        ),
        const SizedBox(width: 12),
        Text(
          'Out-of-Sample Test',
          style: Theme.of(context)
              .textTheme
              .titleLarge
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Widget _testBenchmarkRow(BuildContext context) {
    final bench = oos.benchmark!;
    final beats = bench.beatsBenchmark;

    return Container(
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
            size: 20,
          ),
          const SizedBox(width: 8),
          Text(
            beats
                ? 'Beats test benchmark by '
                    '+${bench.outperformance.toStringAsFixed(2)}%'
                : 'Underperforms test benchmark by '
                    '${bench.outperformance.toStringAsFixed(2)}%',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: beats ? Colors.green : Colors.red,
            ),
          ),
          const SizedBox(width: 16),
          Text(
            'B&H: '
            '${bench.buyAndHoldReturn.toStringAsFixed(2)}%',
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(
                  color: Theme.of(context)
                      .colorScheme
                      .onSurfaceVariant,
                ),
          ),
        ],
      ),
    );
  }
}

/// Side-by-side train vs test metric comparison
class _MetricCompare extends StatelessWidget {
  final String label;
  final double trainValue;
  final double testValue;
  final String suffix;
  final bool signed;
  final int decimals;
  final bool invertColor;

  const _MetricCompare({
    required this.label,
    required this.trainValue,
    required this.testValue,
    this.suffix = '',
    this.signed = false,
    this.decimals = 1,
    this.invertColor = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    // Determine health: test within 50% of train is "ok"
    final ratio = trainValue != 0
        ? testValue / trainValue
        : (testValue >= 0 ? 1.0 : 0.0);
    Color healthColor;
    if (invertColor) {
      // For drawdown: less negative test is better
      healthColor = testValue >= trainValue
          ? Colors.green
          : (ratio > 1.5 ? Colors.red : Colors.orange);
    } else {
      healthColor = ratio >= 0.5
          ? Colors.green
          : (ratio >= 0.0 ? Colors.orange : Colors.red);
    }

    String fmt(double v) {
      final s = v.toStringAsFixed(decimals);
      return signed && v >= 0 ? '+$s$suffix' : '$s$suffix';
    }

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: healthColor.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: healthColor.withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        children: [
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              Column(
                children: [
                  Text(
                    'Train',
                    style: theme.textTheme.labelSmall,
                  ),
                  Text(
                    fmt(trainValue),
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
              Icon(
                Icons.arrow_forward,
                size: 14,
                color: theme.colorScheme.onSurfaceVariant,
              ),
              Column(
                children: [
                  Text(
                    'Test',
                    style: theme.textTheme.labelSmall,
                  ),
                  Text(
                    fmt(testValue),
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                      color: healthColor,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
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
    final cfg = result.runConfig;

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

            // Overview (always shown)
            _ConfigRow(label: 'Mode', value: result.mode.toUpperCase()),
            _ConfigRow(
              label: 'Date Range',
              value: '${result.startDate}  to  ${result.endDate}',
            ),
            _ConfigRow(
              label: 'Portfolio Size',
              value: '${result.portfolioSize} stocks',
            ),
            _ConfigRow(
              label: 'Best Generation',
              value: '${result.bestTrader.generation + 1}',
            ),

            // Detailed config sections (from new config block)
            if (cfg != null) ...[
              const Divider(height: 24),
              _ConfigSection(
                title: 'GA Parameters',
                icon: Icons.tune,
                rows: [
                  _ConfigRow(
                    label: 'Population',
                    value: '${result.populationSize}',
                  ),
                  _ConfigRow(
                    label: 'Generations',
                    value: '${result.numGenerations}',
                  ),
                  _ConfigRow(
                    label: 'Mutation Rate',
                    value: '${(cfg.mutationRate * 100).toStringAsFixed(1)}%',
                  ),
                  _ConfigRow(
                    label: 'Crossover Rate',
                    value: '${(cfg.crossoverRate * 100).toStringAsFixed(1)}%',
                  ),
                  _ConfigRow(
                    label: 'Elitism Count',
                    value: '${cfg.elitismCount}',
                  ),
                  _ConfigRow(
                    label: 'Tournament Size',
                    value: '${cfg.tournamentSize}',
                  ),
                  _ConfigRow(
                    label: 'Random Seed',
                    value: cfg.randomSeed?.toString() ?? 'None',
                  ),
                ],
              ),
              _ConfigSection(
                title: 'Features',
                icon: Icons.extension,
                rows: [
                  _ConfigRow(
                    label: 'Macro Data',
                    value: cfg.useMacroData ? 'ON' : 'OFF',
                  ),
                  _ConfigRow(
                    label: 'Technical Indicators',
                    value: cfg.useTechnicalIndicators ? 'ON' : 'OFF',
                  ),
                  _ConfigRow(
                    label: 'Ensemble Signals',
                    value: cfg.useEnsembleSignals ? 'ON' : 'OFF',
                  ),
                ],
              ),
              if (cfg.useKfoldValidation)
                _ConfigSection(
                  title: 'K-Fold Validation',
                  icon: Icons.layers,
                  rows: [
                    _ConfigRow(label: 'Folds', value: '${cfg.kfoldNumFolds}'),
                    _ConfigRow(
                      label: 'Fold Years',
                      value: '${cfg.kfoldFoldYears}',
                    ),
                    _ConfigRow(
                      label: 'Overlapping',
                      value: cfg.kfoldAllowOverlap ? 'Yes' : 'No',
                    ),
                    _ConfigRow(
                      label: 'Weight Recent',
                      value: cfg.kfoldWeightRecent
                          ? 'Yes (${cfg.kfoldRecentWeightFactor}x)'
                          : 'No',
                    ),
                    _ConfigRow(
                      label: 'Min Bars/Fold',
                      value: '${cfg.kfoldMinBarsPerFold}',
                    ),
                  ],
                ),
              _ConfigSection(
                title: 'Backtrader',
                icon: Icons.account_balance_wallet,
                rows: [
                  _ConfigRow(
                    label: 'Initial Cash',
                    value: '\$${cfg.initialCash.toStringAsFixed(0)}',
                  ),
                  _ConfigRow(
                    label: 'Commission',
                    value: '${(cfg.commission * 100).toStringAsFixed(2)}%',
                  ),
                  _ConfigRow(
                    label: 'Allocation',
                    value: '${cfg.initialAllocationPct.toStringAsFixed(0)}%',
                  ),
                ],
              ),
              _ConfigSection(
                title: 'Fitness Weights',
                icon: Icons.fitness_center,
                rows: cfg.fitnessWeights.entries
                    .map(
                      (e) => _ConfigRow(
                        label: _formatWeightName(e.key),
                        value: e.value.toStringAsFixed(2),
                      ),
                    )
                    .toList(),
              ),
            ] else ...[
              // Fallback for old results without config block
              const Divider(height: 24),
              _ConfigRow(
                label: 'Population',
                value: '${result.populationSize} traders',
              ),
              _ConfigRow(
                label: 'Generations',
                value: '${result.numGenerations}',
              ),
              _ConfigRow(
                label: 'Initial Allocation',
                value: '${result.initialAllocationPct.toInt()}%',
              ),
              _ConfigRow(
                label: 'Total Trades',
                value: '${result.bestTrader.performance.tradeCount}',
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatWeightName(String key) {
    return key
        .replaceAll('_', ' ')
        .split(' ')
        .map(
          (w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '',
        )
        .join(' ');
  }
}

/// A collapsible section of config rows
class _ConfigSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<_ConfigRow> rows;

  const _ConfigSection({
    required this.title,
    required this.icon,
    required this.rows,
  });

  @override
  Widget build(BuildContext context) {
    return ExpansionTile(
      leading: Icon(icon, size: 20),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
      tilePadding: EdgeInsets.zero,
      childrenPadding: const EdgeInsets.only(left: 16),
      children: rows,
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
    final riskGenes = <String, dynamic>{};
    final macroGenes = <String, dynamic>{};
    final tiGenes = <String, dynamic>{};
    final ensembleGenes = <String, dynamic>{};

    for (final entry in genes.entries) {
      if (entry.key.startsWith('ma_') ||
          entry.key.startsWith('ensemble_') ||
          entry.key.startsWith('sig_')) {
        ensembleGenes[entry.key] = entry.value;
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

/// Trade distribution per stock (bar chart)
class _TradeDistribution extends StatelessWidget {
  final Map<String, StockPerformance>? perStock;

  const _TradeDistribution({required this.perStock});

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
                  Icons.swap_horiz,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Text(
                  'Trade Distribution',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (perStock == null || perStock!.isEmpty)
              const SizedBox(
                height: 100,
                child: Center(
                  child: Text('Per-stock data not available for this run'),
                ),
              )
            else
              _buildChart(context),
          ],
        ),
      ),
    );
  }

  Widget _buildChart(BuildContext context) {
    final sorted = perStock!.entries.toList()
      ..sort((a, b) => b.value.trades.compareTo(a.value.trades));

    final maxTrades = sorted.first.value.trades.toDouble();
    final chartHeight = (sorted.length * 36.0).clamp(150.0, 500.0);

    return SizedBox(
      height: chartHeight,
      child: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: maxTrades * 1.15,
          barTouchData: BarTouchData(
            touchTooltipData: BarTouchTooltipData(
              getTooltipItem: (group, gIdx, rod, rIdx) {
                final entry = sorted[group.x.toInt()];
                final s = entry.value;
                return BarTooltipItem(
                  '${entry.key}\n'
                  'Trades: ${s.trades}\n'
                  'Won: ${s.won} | Lost: ${s.lost}\n'
                  'Win Rate: '
                  '${s.winRate.toStringAsFixed(1)}%',
                  const TextStyle(color: Colors.white, fontSize: 12),
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
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 30,
                getTitlesWidget: (value, meta) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= sorted.length) {
                    return const SizedBox.shrink();
                  }
                  return SideTitleWidget(
                    meta: meta,
                    child: Text(
                      sorted[idx].key,
                      style: const TextStyle(fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 40,
                getTitlesWidget: (value, meta) {
                  return Text(
                    value.toInt().toString(),
                    style: const TextStyle(fontSize: 10),
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
          barGroups: sorted.asMap().entries.map((entry) {
            final idx = entry.key;
            final stock = entry.value.value;
            final wr = stock.winRate;
            final barColor = wr > 50
                ? Colors.green
                : wr > 40
                ? Colors.orange
                : Colors.red;
            return BarChartGroupData(
              x: idx,
              barRods: [
                BarChartRodData(
                  toY: stock.trades.toDouble(),
                  color: barColor,
                  width: 16,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(4),
                    topRight: Radius.circular(4),
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      ),
    );
  }
}

/// Profit contribution per stock (bar chart)
class _ProfitContribution extends StatelessWidget {
  final Map<String, StockPerformance>? perStock;

  const _ProfitContribution({required this.perStock});

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
                  Icons.monetization_on,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Text(
                  'Profit Contribution',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (perStock == null || perStock!.isEmpty)
              const SizedBox(
                height: 100,
                child: Center(
                  child: Text('Per-stock data not available for this run'),
                ),
              )
            else
              _buildChart(context),
          ],
        ),
      ),
    );
  }

  Widget _buildChart(BuildContext context) {
    final sorted = perStock!.entries.toList()
      ..sort((a, b) => b.value.pnl.compareTo(a.value.pnl));

    final maxPnl = sorted
        .map((e) => e.value.pnl.abs())
        .reduce((a, b) => a > b ? a : b);
    final yBound = maxPnl * 1.15;
    final chartHeight = (sorted.length * 36.0).clamp(150.0, 500.0);

    return SizedBox(
      height: chartHeight,
      child: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: yBound,
          minY: -yBound,
          barTouchData: BarTouchData(
            touchTooltipData: BarTouchTooltipData(
              getTooltipItem: (group, gIdx, rod, rIdx) {
                final entry = sorted[group.x.toInt()];
                final pnl = entry.value.pnl;
                final sign = pnl >= 0 ? '+' : '';
                return BarTooltipItem(
                  '${entry.key}\n'
                  'PnL: $sign'
                  '\$${pnl.toStringAsFixed(2)}\n'
                  'Trades: ${entry.value.trades}',
                  const TextStyle(color: Colors.white, fontSize: 12),
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
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 30,
                getTitlesWidget: (value, meta) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= sorted.length) {
                    return const SizedBox.shrink();
                  }
                  return SideTitleWidget(
                    meta: meta,
                    child: Text(
                      sorted[idx].key,
                      style: const TextStyle(fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              axisNameWidget: const Text(
                'PnL (\$)',
                style: TextStyle(fontSize: 12),
              ),
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 60,
                getTitlesWidget: (value, meta) {
                  return Text(
                    '\$${value.toStringAsFixed(0)}',
                    style: const TextStyle(fontSize: 10),
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
          barGroups: sorted.asMap().entries.map((entry) {
            final idx = entry.key;
            final pnl = entry.value.value.pnl;
            return BarChartGroupData(
              x: idx,
              barRods: [
                BarChartRodData(
                  toY: pnl,
                  color: pnl >= 0 ? Colors.green : Colors.red,
                  width: 16,
                  borderRadius: pnl >= 0
                      ? const BorderRadius.only(
                          topLeft: Radius.circular(4),
                          topRight: Radius.circular(4),
                        )
                      : const BorderRadius.only(
                          bottomLeft: Radius.circular(4),
                          bottomRight: Radius.circular(4),
                        ),
                ),
              ],
            );
          }).toList(),
        ),
      ),
    );
  }
}
