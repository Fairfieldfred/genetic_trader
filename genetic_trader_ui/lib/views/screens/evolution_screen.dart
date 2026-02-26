import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../viewmodels/evolution_viewmodel.dart';

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

              // Output Log
              Expanded(
                child: _buildOutputLog(context, viewModel),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildControlPanel(BuildContext context, EvolutionViewModel viewModel) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            if (!viewModel.isRunning && !viewModel.isCompleted) ...[
              // Ready to start
              const Icon(Icons.rocket_launch, size: 64, color: Colors.deepPurple),
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
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                ),
                onPressed: () {
                  viewModel.startEvolution();
                },
              ),
            ] else if (viewModel.isRunning) ...[
              // Running
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
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      Text(
                        'Generation ${viewModel.currentGeneration}/${viewModel.totalGenerations}',
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
              // Completed
              Icon(
                viewModel.error != null ? Icons.error : Icons.check_circle,
                size: 64,
                color: viewModel.error != null ? Colors.red : Colors.green,
              ),
              const SizedBox(height: 16),
              Text(
                viewModel.error != null ? 'Evolution Failed' : 'Evolution Complete!',
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
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
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Results screen coming soon!'),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildProgressSection(BuildContext context, EvolutionViewModel viewModel) {
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
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
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
                    icon: Icons.flag,
                    label: 'Generation',
                    value: '${viewModel.currentGeneration}/${viewModel.totalGenerations}',
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
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOutputLog(BuildContext context, EvolutionViewModel viewModel) {
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
                    reverse: false,
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
                  ),
          ),
        ],
      ),
    );
  }

  void _showStopDialog(BuildContext context, EvolutionViewModel viewModel) {
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
