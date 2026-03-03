import 'package:flutter/material.dart';
import 'config_screen.dart';
import 'evolution_screen.dart';
import 'results_list_screen.dart';

/// Home screen with dashboard and quick actions
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Genetic Trader'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Settings',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const ConfigScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // App Icon
              Icon(
                Icons.trending_up,
                size: 120,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 24),

              // App Title
              Text(
                'Genetic Trader',
                style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.primary,
                    ),
              ),
              const SizedBox(height: 8),

              Text(
                'AI-Powered Trading Strategy Evolution',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 48),

              // Quick Stats Card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Quick Stats',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _buildStatItem(
                            context,
                            icon: Icons.analytics,
                            label: 'Total Runs',
                            value: '-',
                          ),
                          _buildStatItem(
                            context,
                            icon: Icons.stars,
                            label: 'Best Return',
                            value: '-',
                          ),
                          _buildStatItem(
                            context,
                            icon: Icons.access_time,
                            label: 'Last Run',
                            value: 'Never',
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Action Buttons
              SizedBox(
                width: 300,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    ElevatedButton.icon(
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Start Evolution'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const EvolutionScreen(),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 12),

                    OutlinedButton.icon(
                      icon: const Icon(Icons.show_chart),
                      label: const Text('View Results'),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) =>
                                const ResultsListScreen(),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 12),

                    OutlinedButton.icon(
                      icon: const Icon(Icons.tune),
                      label: const Text('Configuration'),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const ConfigScreen(),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 32),

              // Info
              Text(
                'Configure your genetic algorithm parameters\nand start evolving profitable trading strategies',
                textAlign: TextAlign.center,
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

  Widget _buildStatItem(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Column(
      children: [
        Icon(
          icon,
          size: 32,
          color: Theme.of(context).colorScheme.primary,
        ),
        const SizedBox(height: 8),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
      ],
    );
  }

}
