import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../models/evolution_result.dart';
import '../../viewmodels/results_viewmodel.dart';
import 'results_dashboard_screen.dart';

/// Screen showing a list of all past evolution runs
class ResultsListScreen extends StatelessWidget {
  const ResultsListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ResultsViewModel()..loadResults(),
      child: const _ResultsListContent(),
    );
  }
}

class _ResultsListContent extends StatelessWidget {
  const _ResultsListContent();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Evolution Results'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: () {
              context.read<ResultsViewModel>().loadResults();
            },
          ),
        ],
      ),
      body: Consumer<ResultsViewModel>(
        builder: (context, viewModel, child) {
          if (viewModel.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (viewModel.error != null) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.error_outline,
                    size: 64,
                    color: Theme.of(context).colorScheme.error,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    viewModel.error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
              ),
            );
          }

          if (viewModel.results.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.inbox,
                    size: 80,
                    color: Theme.of(
                      context,
                    ).colorScheme.onSurfaceVariant.withValues(alpha: 0.5),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No evolution runs found',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Run an evolution to see results here',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurfaceVariant.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: viewModel.results.length,
            itemBuilder: (context, index) {
              return _ResultCard(result: viewModel.results[index]);
            },
          );
        },
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  final EvolutionResult result;

  const _ResultCard({required this.result});

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('MMM d, yyyy  HH:mm');
    final totalReturn = result.bestTrader.performance.totalReturn;
    final isPositive = totalReturn >= 0;
    final returnColor = isPositive ? Colors.green : Colors.red;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          final viewModel = context.read<ResultsViewModel>();
          viewModel.selectResult(result);
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => ChangeNotifierProvider.value(
                value: viewModel,
                child: const ResultsDashboardScreen(),
              ),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row: date + benchmark badge
              Row(
                children: [
                  Icon(
                    Icons.science,
                    size: 20,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      dateFormat.format(result.runDate),
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  _BenchmarkBadge(beats: result.benchmark.beatsBenchmark),
                ],
              ),
              const SizedBox(height: 12),

              // Stats row
              Row(
                children: [
                  _StatChip(
                    label: 'Return',
                    value:
                        '${isPositive ? '+' : ''}${totalReturn.toStringAsFixed(1)}%',
                    color: returnColor,
                  ),
                  const SizedBox(width: 8),
                  _StatChip(
                    label: 'Fitness',
                    value: result.bestTrader.fitness.toStringAsFixed(1),
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  _StatChip(
                    label: 'Trades',
                    value: '${result.bestTrader.performance.tradeCount}',
                    color: Theme.of(context).colorScheme.secondary,
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Config info
              Text(
                '${result.portfolioSize} stocks  |  '
                '${result.numGenerations} gens  |  '
                'Pop ${result.populationSize}  |  '
                '${result.startDate} to ${result.endDate}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatChip({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label: ',
            style: TextStyle(fontSize: 12, color: color.withValues(alpha: 0.8)),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _BenchmarkBadge extends StatelessWidget {
  final bool beats;

  const _BenchmarkBadge({required this.beats});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: beats
            ? Colors.green.withValues(alpha: 0.1)
            : Colors.red.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            beats ? Icons.check_circle : Icons.cancel,
            size: 14,
            color: beats ? Colors.green : Colors.red,
          ),
          const SizedBox(width: 4),
          Text(
            beats ? 'Beats B&H' : 'Under B&H',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: beats ? Colors.green : Colors.red,
            ),
          ),
        ],
      ),
    );
  }
}
