import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../models/evolution_result.dart';
import '../../viewmodels/evolution_viewmodel.dart';
import '../../viewmodels/results_viewmodel.dart';
import 'results_dashboard_screen.dart';

/// Screen for running and monitoring evolution process
class EvolutionScreen extends StatelessWidget {
  const EvolutionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => EvolutionViewModel(),
      child: const _EvolutionScreenContent(),
    );
  }
}

class _EvolutionScreenContent extends StatelessWidget {
  const _EvolutionScreenContent();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Evolution'),
        actions: [
          Consumer<EvolutionViewModel>(
            builder: (context, viewModel, child) {
              if (viewModel.isCompleted) {
                return IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'New Run',
                  onPressed: () {
                    viewModel.reset();
                  },
                );
              }
              return const SizedBox.shrink();
            },
          ),
        ],
      ),
      body: Consumer<EvolutionViewModel>(
        builder: (context, viewModel, child) {
          return Column(
            children: [
              // Control Panel
              _buildControlPanel(context, viewModel),

              // Progress Section
              if (viewModel.isRunning || viewModel.isCompleted)
                _buildProgressSection(context, viewModel),

              // Chart + Log tabs
              if (viewModel.isRunning || viewModel.isCompleted)
                Expanded(
                  child: _ChartAndLogTabs(viewModel: viewModel),
                )
              else
                Expanded(
                  child: _buildOutputLog(context, viewModel),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildControlPanel(
    BuildContext context,
    EvolutionViewModel viewModel,
  ) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            if (!viewModel.isRunning && !viewModel.isCompleted) ...[
              const Icon(
                Icons.rocket_launch,
                size: 64,
                color: Colors.deepPurple,
              ),
              const SizedBox(height: 16),
              const Text(
                'Ready to Start Evolution',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Click the button below to begin evolving trading strategies',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                icon: const Icon(Icons.play_arrow),
                label: const Text('Start Evolution'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32,
                    vertical: 16,
                  ),
                ),
                onPressed: () {
                  viewModel.startEvolution();
                },
              ),
            ] else if (viewModel.isRunning) ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const CircularProgressIndicator(),
                  const SizedBox(width: 16),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Evolution Running...',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        'Generation ${viewModel.currentGeneration}'
                        '/${viewModel.totalGenerations}',
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                icon: const Icon(Icons.stop),
                label: const Text('Stop Evolution'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                ),
                onPressed: () {
                  _showStopDialog(context, viewModel);
                },
              ),
            ] else if (viewModel.isCompleted) ...[
              Icon(
                viewModel.error != null ? Icons.error : Icons.check_circle,
                size: 64,
                color: viewModel.error != null ? Colors.red : Colors.green,
              ),
              const SizedBox(height: 16),
              Text(
                viewModel.error != null
                    ? 'Evolution Failed'
                    : 'Evolution Complete!',
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              if (viewModel.error != null) ...[
                const SizedBox(height: 8),
                Text(
                  viewModel.error!,
                  style: const TextStyle(color: Colors.red),
                  textAlign: TextAlign.center,
                ),
              ],
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton.icon(
                    icon: const Icon(Icons.refresh),
                    label: const Text('New Run'),
                    onPressed: () {
                      viewModel.reset();
                    },
                  ),
                  const SizedBox(width: 16),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.analytics),
                    label: const Text('View Results'),
                    onPressed: viewModel.runId != null
                        ? () {
                            final resultsVm = ResultsViewModel();
                            resultsVm
                                .loadAndSelectResult(viewModel.runId!);
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) =>
                                    ChangeNotifierProvider.value(
                                  value: resultsVm,
                                  child: const ResultsDashboardScreen(),
                                ),
                              ),
                            );
                          }
                        : null,
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildProgressSection(
    BuildContext context,
    EvolutionViewModel viewModel,
  ) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Progress',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                Text(
                  '${viewModel.progressPercentage.toStringAsFixed(1)}%',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: viewModel.progress.progress,
              minHeight: 8,
              backgroundColor: Colors.grey[300],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    context,
                    icon: Icons.trending_up,
                    label: 'Best Fitness',
                    value: viewModel.bestFitness.toStringAsFixed(2),
                    color: Colors.green,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildStatCard(
                    context,
                    icon: Icons.show_chart,
                    label: 'Avg Fitness',
                    value: viewModel.avgFitness.toStringAsFixed(2),
                    color: Colors.blue,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildStatCard(
                    context,
                    icon: Icons.trending_down,
                    label: 'Worst Fitness',
                    value: viewModel.worstFitness.toStringAsFixed(2),
                    color: Colors.grey,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildStatCard(
                    context,
                    icon: Icons.flag,
                    label: 'Generation',
                    value: '${viewModel.currentGeneration}'
                        '/${viewModel.totalGenerations}',
                    color: Colors.deepPurple,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }

  Widget _buildOutputLog(
    BuildContext context,
    EvolutionViewModel viewModel,
  ) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const Icon(Icons.terminal),
                const SizedBox(width: 8),
                const Text(
                  'Output Log',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                Text(
                  '${viewModel.outputLines.length} lines',
                  style: TextStyle(color: Colors.grey[600], fontSize: 12),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: viewModel.outputLines.isEmpty
                ? Center(
                    child: Text(
                      'No output yet. Start evolution to see logs.',
                      style: TextStyle(color: Colors.grey[600]),
                    ),
                  )
                : ListView.builder(
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
                                : Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.color,
                          ),
                        ),
                      );
                    },
                  ),
          ),
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
      builder: (context) => AlertDialog(
        title: const Text('Stop Evolution'),
        content: const Text(
          'Are you sure you want to stop the evolution process?\n\n'
          'Current progress will be lost.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              viewModel.stopEvolution();
              Navigator.pop(context);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Stop'),
          ),
        ],
      ),
    );
  }
}

/// Tabbed section with live chart and output log
class _ChartAndLogTabs extends StatelessWidget {
  final EvolutionViewModel viewModel;

  const _ChartAndLogTabs({required this.viewModel});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Card(
        margin: const EdgeInsets.all(16),
        child: Column(
          children: [
            TabBar(
              tabs: const [
                Tab(icon: Icon(Icons.show_chart), text: 'Chart'),
                Tab(icon: Icon(Icons.terminal), text: 'Output Log'),
              ],
              labelColor: Theme.of(context).colorScheme.primary,
              unselectedLabelColor:
                  Theme.of(context).colorScheme.onSurfaceVariant,
              indicatorColor: Theme.of(context).colorScheme.primary,
            ),
            const Divider(height: 1),
            Expanded(
              child: TabBarView(
                children: [
                  _LiveFitnessChart(history: viewModel.fitnessHistory),
                  _OutputLogTab(viewModel: viewModel),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Live fitness chart that updates as generations complete
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
                          'Waiting for first generation to complete...',
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
            spots: history
                .map(
                  (e) => FlSpot(
                    e.generation.toDouble(),
                    e.bestFitness,
                  ),
                )
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
            spots: history
                .map(
                  (e) => FlSpot(
                    e.generation.toDouble(),
                    e.avgFitness,
                  ),
                )
                .toList(),
            isCurved: true,
            color: Colors.orange,
            barWidth: 2,
            dotData: const FlDotData(show: false),
          ),
          // Worst fitness line
          LineChartBarData(
            spots: history
                .map(
                  (e) => FlSpot(
                    e.generation.toDouble(),
                    e.worstFitness,
                  ),
                )
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

/// Output log tab content
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
