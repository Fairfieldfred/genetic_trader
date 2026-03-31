import '../models/bar.dart';
import '../models/chromosome.dart';
import '../models/backtest_result.dart';
import '../backtesting/backtester.dart';
import '../backtesting/ma_strategy.dart';

/// Evaluates a chromosome's fitness by running a backtest.
class FitnessEvaluator {
  /// Fitness weight configuration.
  final double returnWeight;
  final double sharpeWeight;
  final double drawdownWeight;
  final double winRateWeight;
  final BacktestConfig backtestConfig;

  const FitnessEvaluator({
    this.returnWeight = 0.4,
    this.sharpeWeight = 0.24,
    this.drawdownWeight = 0.24,
    this.winRateWeight = 0.12,
    this.backtestConfig = const BacktestConfig(),
  });

  /// Evaluate a chromosome on the given bars.
  ///
  /// Returns the fitness score (higher is better).
  double evaluate(Chromosome chromosome, List<Bar> bars) {
    final strategy =
        MaStrategy.fromChromosome(chromosome, bars);
    final result = Backtester.run(
      bars: bars,
      strategy: strategy,
      config: backtestConfig,
    );

    return _scoreFitness(result);
  }

  /// Evaluate and return both fitness score and full result.
  (double fitness, BacktestResult result) evaluateWithResult(
    Chromosome chromosome,
    List<Bar> bars,
  ) {
    final strategy =
        MaStrategy.fromChromosome(chromosome, bars);
    final result = Backtester.run(
      bars: bars,
      strategy: strategy,
      config: backtestConfig,
    );

    return (_scoreFitness(result), result);
  }

  double _scoreFitness(BacktestResult result) {
    // Convert ratios to percentages to match Python backend scale.
    // Sharpe ratio is already unitless — no conversion needed.
    final score = (result.totalReturn * 100) * returnWeight +
        result.sharpeRatio * sharpeWeight -
        (result.maxDrawdown * 100) * drawdownWeight +
        (result.winRate * 100) * winRateWeight;
    // Guard against NaN/Infinity from degenerate backtests.
    return score.isFinite ? score : -1.0;
  }
}
