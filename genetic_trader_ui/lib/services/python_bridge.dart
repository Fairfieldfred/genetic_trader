import 'dart:io';
import 'dart:convert';
import 'package:flutter/foundation.dart';

/// Service for managing Python process execution
class PythonBridge {
  Process? _process;
  final List<String> _outputLines = [];
  bool _isRunning = false;

  bool get isRunning => _isRunning;
  List<String> get outputLines => List.unmodifiable(_outputLines);

  /// Start the evolution process
  Future<void> startEvolution({
    required Function(String line) onOutput,
    required Function(EvolutionProgress progress) onProgress,
    required Function() onComplete,
    required Function(String error) onError,
    String? resumeRunId,
  }) async {
    if (_isRunning) {
      onError('Evolution is already running');
      return;
    }

    try {
      // Use absolute path to the Genetic Trader directory
      // macOS sandboxing means we can't use relative paths
      const workingDir = '/Users/fred/Development/Genetic Trader';

      if (kDebugMode) {
        print('Starting evolution in: $workingDir');
      }

      // Check if evolve.py exists
      final evolveFile = File('$workingDir/evolve.py');
      if (!await evolveFile.exists()) {
        onError('evolve.py not found at: $workingDir');
        _isRunning = false;
        return;
      }

      if (kDebugMode) {
        print('Checking Python availability...');
      }

      // Prefer venv Python (has all dependencies), fall back to system python3
      final venvPython = '$workingDir/.venv/bin/python3';
      final venvFile = File(venvPython);
      final pythonExe =
          await venvFile.exists() ? venvPython : 'python3';

      if (kDebugMode) {
        print('Using Python: $pythonExe');
      }

      // Check if Python is available
      try {
        final pythonCheck = await Process.run(
          pythonExe,
          ['--version'],
        );
        if (kDebugMode) {
          print(
            'Python version: ${pythonCheck.stdout.toString().trim()}',
          );
        }
      } catch (e) {
        onError('Python3 not found. Please install Python 3.');
        _isRunning = false;
        return;
      }

      if (kDebugMode) {
        print('Starting Python process...');
      }

      // Start the Python process with unbuffered output
      final args = ['-u', 'evolve.py'];
      if (resumeRunId != null) {
        args.addAll(['--resume', resumeRunId]);
      }

      _process = await Process.start(
        pythonExe,
        args,
        workingDirectory: workingDir,
      );

      if (kDebugMode) {
        print('Python process started with PID: ${_process!.pid}');
      }

      _isRunning = true;
      _outputLines.clear();

      // Listen to stdout
      _process!.stdout
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(
        (line) {
          _outputLines.add(line);
          onOutput(line);

          // Also print to debugger console
          if (kDebugMode) {
            print('[Python] $line');
          }

          // Parse progress
          final progress = _parseProgress(line);
          if (progress != null) {
            onProgress(progress);
          }
        },
        onDone: () {
          _isRunning = false;
          if (kDebugMode) {
            print('[Python] Process completed');
          }
          onComplete();
        },
        onError: (error) {
          _isRunning = false;
          if (kDebugMode) {
            print('[Python] Stream error: $error');
          }
          onError(error.toString());
        },
      );

      // Listen to stderr
      _process!.stderr
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(
        (line) {
          _outputLines.add('ERROR: $line');
          onOutput('ERROR: $line');

          // Also print to debugger console
          if (kDebugMode) {
            print('[Python ERROR] $line');
          }

          onError(line);
        },
      );

      // Wait for exit
      final exitCode = await _process!.exitCode;
      _isRunning = false;

      if (exitCode == 0) {
        onComplete();
      } else {
        onError('Process exited with code $exitCode');
      }
    } catch (e) {
      _isRunning = false;
      onError('Failed to start evolution: $e');
    }
  }

  /// Stop the evolution process
  void stop() {
    if (_process != null && _isRunning) {
      _process!.kill();
      _process = null;
      _isRunning = false;
    }
  }

  /// Parse progress information from output line
  EvolutionProgress? _parseProgress(String line) {
    // Parse lines like "Generation 15/40 (37%)"
    final genRegex = RegExp(r'Generation\s+(\d+)/(\d+)');
    final genMatch = genRegex.firstMatch(line);

    if (genMatch != null) {
      final current = int.parse(genMatch.group(1)!);
      final total = int.parse(genMatch.group(2)!);
      return EvolutionProgress(
        currentGeneration: current,
        totalGenerations: total,
      );
    }

    // Parse fitness lines like "Best Fitness: 18.43"
    final fitnessRegex = RegExp(r'Best Fitness:\s+([-\d.]+)');
    final fitnessMatch = fitnessRegex.firstMatch(line);

    if (fitnessMatch != null) {
      final fitness = double.parse(fitnessMatch.group(1)!);
      return EvolutionProgress(bestFitness: fitness);
    }

    // Parse average fitness
    final avgFitnessRegex = RegExp(r'Average Fitness:\s+([-\d.]+)');
    final avgMatch = avgFitnessRegex.firstMatch(line);

    if (avgMatch != null) {
      final avgFitness = double.parse(avgMatch.group(1)!);
      return EvolutionProgress(avgFitness: avgFitness);
    }

    // Parse worst fitness
    final worstFitnessRegex = RegExp(r'Worst Fitness:\s+([-\d.]+)');
    final worstMatch = worstFitnessRegex.firstMatch(line);

    if (worstMatch != null) {
      final worstFitness = double.parse(worstMatch.group(1)!);
      return EvolutionProgress(worstFitness: worstFitness);
    }

    // Parse std dev
    final stdDevRegex = RegExp(r'Std Dev:\s+([-\d.]+)');
    final stdMatch = stdDevRegex.firstMatch(line);

    if (stdMatch != null) {
      final stdDev = double.parse(stdMatch.group(1)!);
      return EvolutionProgress(stdDev: stdDev);
    }

    // Parse gene change lines like "GENE_CHANGE: gene_name: old -> new"
    final geneChangeRegex = RegExp(
      r'GENE_CHANGE:\s+(\w+):\s+(.+?)\s+->\s+(.+)',
    );
    final geneChangeMatch = geneChangeRegex.firstMatch(line);

    if (geneChangeMatch != null) {
      return EvolutionProgress(
        geneChanges: [
          GeneChangeInfo(
            gene: geneChangeMatch.group(1)!,
            oldValue: geneChangeMatch.group(2)!.trim(),
            newValue: geneChangeMatch.group(3)!.trim(),
          ),
        ],
      );
    }

    // Parse "GENE_CHANGE: initial" for first generation
    if (line.trim() == 'GENE_CHANGE: initial') {
      return EvolutionProgress(isInitialGenes: true);
    }

    // Parse resume header
    final resumeRegex = RegExp(r'RESUMING from run\s+(\S+)');
    if (resumeRegex.hasMatch(line)) {
      return EvolutionProgress(
        statusMessage: 'Resuming from previous run...',
      );
    }

    // Parse out-of-sample test header
    if (line.trim() == 'OUT-OF-SAMPLE TEST') {
      return EvolutionProgress(
        statusMessage: 'Running out-of-sample test...',
      );
    }

    // Parse out-of-sample total return
    final oosReturnRegex = RegExp(
      r'Out-of-Sample Performance:',
    );
    if (oosReturnRegex.hasMatch(line)) {
      return EvolutionProgress(
        statusMessage: 'Evaluating on test data...',
      );
    }

    // Parse run_id from "Summary saved to results/summary_XXXXXXXX_XXXXXX.json"
    final summaryRegex = RegExp(
      r'Summary saved to .+summary_(\d{8}_\d{6})\.json',
    );
    final summaryMatch = summaryRegex.firstMatch(line);

    if (summaryMatch != null) {
      return EvolutionProgress(runId: summaryMatch.group(1));
    }

    return null;
  }

  /// Clear output history
  void clearOutput() {
    _outputLines.clear();
  }

  /// Get the most recent output lines
  List<String> getRecentOutput({int count = 100}) {
    if (_outputLines.length <= count) {
      return _outputLines;
    }
    return _outputLines.sublist(_outputLines.length - count);
  }
}

/// A single gene change parsed from Python stdout
class GeneChangeInfo {
  final String gene;
  final String oldValue;
  final String newValue;

  const GeneChangeInfo({
    required this.gene,
    required this.oldValue,
    required this.newValue,
  });
}

/// Progress information parsed from evolution output
class EvolutionProgress {
  final int? currentGeneration;
  final int? totalGenerations;
  final double? bestFitness;
  final double? avgFitness;
  final double? worstFitness;
  final double? stdDev;
  final String? runId;
  final List<GeneChangeInfo>? geneChanges;
  final bool? isInitialGenes;
  final String? statusMessage;

  EvolutionProgress({
    this.currentGeneration,
    this.totalGenerations,
    this.bestFitness,
    this.avgFitness,
    this.worstFitness,
    this.stdDev,
    this.runId,
    this.geneChanges,
    this.isInitialGenes,
    this.statusMessage,
  });

  double get progress {
    if (currentGeneration != null && totalGenerations != null) {
      return currentGeneration! / totalGenerations!;
    }
    return 0.0;
  }

  EvolutionProgress copyWith({
    int? currentGeneration,
    int? totalGenerations,
    double? bestFitness,
    double? avgFitness,
    double? worstFitness,
    double? stdDev,
    String? runId,
    List<GeneChangeInfo>? geneChanges,
    bool? isInitialGenes,
    String? statusMessage,
  }) {
    return EvolutionProgress(
      currentGeneration:
          currentGeneration ?? this.currentGeneration,
      totalGenerations:
          totalGenerations ?? this.totalGenerations,
      bestFitness: bestFitness ?? this.bestFitness,
      avgFitness: avgFitness ?? this.avgFitness,
      worstFitness: worstFitness ?? this.worstFitness,
      stdDev: stdDev ?? this.stdDev,
      runId: runId ?? this.runId,
      geneChanges: geneChanges ?? this.geneChanges,
      isInitialGenes:
          isInitialGenes ?? this.isInitialGenes,
      statusMessage:
          statusMessage ?? this.statusMessage,
    );
  }
}
