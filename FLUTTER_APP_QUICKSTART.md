# Flutter macOS App - Quick Start Guide

## Project Created ✅

A Flutter macOS app has been created at:
```
/Users/fred/Development/Genetic Trader/genetic_trader_ui/
```

## Project Structure

```
genetic_trader_ui/
├── lib/
│   ├── main.dart                 # App entry point (replace)
│   ├── models/
│   │   └── config_model.dart     # ✅ Created - Config data model
│   ├── viewmodels/               # Create these
│   ├── views/                    # Create these
│   ├── services/                 # Create these
│   └── utils/                    # Create these
├── macos/                        # macOS platform code
├── pubspec.yaml                  # Dependencies (updated ✅)
└── APP_DESIGN.md                 # ✅ Full app design document
```

## Dependencies Installed ✅

```yaml
dependencies:
  provider: ^6.1.5+1      # State management
  fl_chart: ^1.1.1        # Charts
  file_picker: ^10.3.3    # File selection
  path_provider: ^2.1.5   # App directories
  sqflite: ^2.4.2        # SQLite database
  http: ^1.5.0           # HTTP requests
  intl: ^0.20.2          # Date formatting
```

## Next Steps to Build the App

### 1. Create Utils and Theme

**`lib/utils/theme.dart`**:
```dart
import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData lightTheme = ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: Colors.deepPurple,
      brightness: Brightness.light,
    ),
    useMaterial3: true,
  );

  static ThemeData darkTheme = ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: Colors.deepPurple,
      brightness: Brightness.dark,
    ),
    useMaterial3: true,
  );
}
```

### 2. Create ViewModel for Configuration

**`lib/viewmodels/config_viewmodel.dart`**:
```dart
import 'package:flutter/foundation.dart';
import '../models/config_model.dart';
import 'dart:io';

class ConfigViewModel extends ChangeNotifier {
  GeneticConfig _config = GeneticConfig();

  GeneticConfig get config => _config;

  void updatePortfolioSize(int size) {
    _config = _config.copyWith(portfolioSize: size);
    notifyListeners();
  }

  void updateInitialAllocation(double pct) {
    _config = _config.copyWith(initialAllocationPct: pct);
    notifyListeners();
  }

  void updatePopulationSize(int size) {
    _config = _config.copyWith(populationSize: size);
    notifyListeners();
  }

  void updateNumGenerations(int gens) {
    _config = _config.copyWith(numGenerations: gens);
    notifyListeners();
  }

  void updateMutationRate(double rate) {
    _config = _config.copyWith(mutationRate: rate);
    notifyListeners();
  }

  void updateCrossoverRate(double rate) {
    _config = _config.copyWith(crossoverRate: rate);
    notifyListeners();
  }

  void updateFitnessWeight(String key, double value) {
    final weights = Map<String, double>.from(_config.fitnessWeights);
    weights[key] = value;

    // Normalize to 100%
    final total = weights.values.reduce((a, b) => a + b);
    if (total > 0) {
      weights.updateAll((key, value) => value / total);
    }

    _config = _config.copyWith(fitnessWeights: weights);
    notifyListeners();
  }

  Future<void> saveConfig() async {
    // Get parent directory (genetic_trader/)
    final parentDir = Directory.current.parent;
    final configFile = File('${parentDir.path}/config.py');

    await configFile.writeAsString(_config.toPythonConfig());
    print('Config saved to ${configFile.path}');
  }

  Future<void> loadConfig() async {
    // TODO: Parse existing config.py file
    // For now, use defaults
    _config = GeneticConfig();
    notifyListeners();
  }
}
```

### 3. Create Home Screen

**`lib/views/screens/home_screen.dart`**:
```dart
import 'package:flutter/material.dart';
import 'config_screen.dart';

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
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const ConfigScreen()),
              );
            },
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.trending_up, size: 100, color: Colors.deepPurple),
            const SizedBox(height: 20),
            const Text(
              'Genetic Trader',
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 40),
            ElevatedButton.icon(
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start Evolution'),
              onPressed: () {
                // TODO: Navigate to evolution screen
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Evolution coming soon!')),
                );
              },
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              icon: const Icon(Icons.analytics),
              label: const Text('View Results'),
              onPressed: () {
                // TODO: Navigate to results screen
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Results coming soon!')),
                );
              },
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              icon: const Icon(Icons.settings),
              label: const Text('Configuration'),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => const ConfigScreen()),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
```

### 4. Create Configuration Screen

**`lib/views/screens/config_screen.dart`**:
```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../viewmodels/config_viewmodel.dart';

class ConfigScreen extends StatelessWidget {
  const ConfigScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Configuration'),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: () async {
              await context.read<ConfigViewModel>().saveConfig();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Configuration saved!')),
                );
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
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Portfolio Settings',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 16),
                      SwitchListTile(
                        title: const Text('Use Portfolio Mode'),
                        value: config.usePortfolio,
                        onChanged: (value) {
                          // TODO: Update portfolio mode
                        },
                      ),
                      ListTile(
                        title: const Text('Portfolio Size'),
                        subtitle: Slider(
                          value: config.portfolioSize.toDouble(),
                          min: 1,
                          max: 50,
                          divisions: 49,
                          label: config.portfolioSize.toString(),
                          onChanged: (value) {
                            viewModel.updatePortfolioSize(value.toInt());
                          },
                        ),
                        trailing: Text('${config.portfolioSize}'),
                      ),
                      ListTile(
                        title: const Text('Initial Allocation'),
                        subtitle: Slider(
                          value: config.initialAllocationPct,
                          min: 0,
                          max: 100,
                          divisions: 20,
                          label: '${config.initialAllocationPct.toInt()}%',
                          onChanged: (value) {
                            viewModel.updateInitialAllocation(value);
                          },
                        ),
                        trailing: Text('${config.initialAllocationPct.toInt()}%'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Genetic Algorithm
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Genetic Algorithm',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 16),
                      ListTile(
                        title: const Text('Population Size'),
                        subtitle: Slider(
                          value: config.populationSize.toDouble(),
                          min: 10,
                          max: 100,
                          divisions: 18,
                          label: config.populationSize.toString(),
                          onChanged: (value) {
                            viewModel.updatePopulationSize(value.toInt());
                          },
                        ),
                        trailing: Text('${config.populationSize}'),
                      ),
                      ListTile(
                        title: const Text('Generations'),
                        subtitle: Slider(
                          value: config.numGenerations.toDouble(),
                          min: 10,
                          max: 200,
                          divisions: 19,
                          label: config.numGenerations.toString(),
                          onChanged: (value) {
                            viewModel.updateNumGenerations(value.toInt());
                          },
                        ),
                        trailing: Text('${config.numGenerations}'),
                      ),
                      ListTile(
                        title: const Text('Mutation Rate'),
                        subtitle: Slider(
                          value: config.mutationRate,
                          min: 0.0,
                          max: 1.0,
                          divisions: 20,
                          label: config.mutationRate.toStringAsFixed(2),
                          onChanged: (value) {
                            viewModel.updateMutationRate(value);
                          },
                        ),
                        trailing: Text(config.mutationRate.toStringAsFixed(2)),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Fitness Weights
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Fitness Weights',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const Text(
                        'Automatically normalized to 100%',
                        style: TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                      const SizedBox(height: 16),
                      ...config.fitnessWeights.entries.map((entry) {
                        return ListTile(
                          title: Text(entry.key.replaceAll('_', ' ').toUpperCase()),
                          subtitle: Slider(
                            value: entry.value,
                            min: 0.0,
                            max: 1.0,
                            onChanged: (value) {
                              viewModel.updateFitnessWeight(entry.key, value);
                            },
                          ),
                          trailing: Text('${(entry.value * 100).toInt()}%'),
                        );
                      }).toList(),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
```

### 5. Update Main App

**Replace `lib/main.dart` with**:
```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'views/screens/home_screen.dart';
import 'viewmodels/config_viewmodel.dart';
import 'utils/theme.dart';

void main() {
  runApp(const GeneticTraderApp());
}

class GeneticTraderApp extends StatelessWidget {
  const GeneticTraderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ConfigViewModel()),
      ],
      child: MaterialApp(
        title: 'Genetic Trader',
        theme: AppTheme.lightTheme,
        darkTheme: AppTheme.darkTheme,
        themeMode: ThemeMode.system,
        home: const HomeScreen(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
```

## Running the App

```bash
cd genetic_trader_ui
flutter run -d macos
```

Or in VS Code: Press F5 (make sure macOS device is selected)

## Building for Release

```bash
flutter build macos --release
```

Output: `build/macos/Build/Products/Release/genetic_trader_ui.app`

## Next Features to Implement

1. **Python Integration** (`lib/services/python_bridge.dart`):
   - Start/stop Python evolve.py process
   - Parse stdout for progress updates
   - Read result JSON files

2. **Evolution Screen**:
   - Real-time progress display
   - Live fitness chart
   - Start/stop buttons

3. **Results Screen**:
   - Load and display results
   - Charts (fitness evolution, benchmarks)
   - Export functionality

4. **Advanced Config**:
   - Stock selector with search
   - Date pickers for ranges
   - Gene definitions editor

## Python Integration Example

**`lib/services/python_bridge.dart`**:
```dart
import 'dart:io';
import 'dart:convert';

class PythonBridge {
  Process? _process;

  Future<void> startEvolution({
    required Function(String) onOutput,
    required Function(int) onExit,
  }) async {
    // Get parent directory where Python scripts are
    final parentDir = Directory.current.parent;

    _process = await Process.start(
      'python',
      ['evolve.py'],
      workingDirectory: parentDir.path,
    );

    // Listen to stdout
    _process!.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
      onOutput(line);
      print('Python: $line');
    });

    // Listen to stderr
    _process!.stderr
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
      print('Python Error: $line');
    });

    // Wait for exit
    _process!.exitCode.then((exitCode) {
      onExit(exitCode);
    });
  }

  void stopEvolution() {
    _process?.kill();
    _process = null;
  }
}
```

## Resources

- **Full App Design**: See [APP_DESIGN.md](APP_DESIGN.md)
- **Flutter Docs**: https://docs.flutter.dev/
- **Provider State Management**: https://pub.dev/packages/provider
- **FL Chart**: https://pub.dev/packages/fl_chart

## Current Status

✅ Project created
✅ Dependencies installed
✅ Config model created
✅ App design documented
⏳ Screens to implement
⏳ Python integration to build
⏳ Charts and visualization to add

Start with the steps above and you'll have a working macOS app that can configure and run your genetic trading algorithm!
