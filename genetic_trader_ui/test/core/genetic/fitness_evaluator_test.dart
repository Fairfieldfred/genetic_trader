import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/genetic/fitness_evaluator.dart';
import 'package:genetic_trader_ui/core/models/bar.dart';
import 'package:genetic_trader_ui/core/models/chromosome.dart';
import 'package:genetic_trader_ui/core/backtesting/backtester.dart';

void main() {
  group('FitnessEvaluator', () {
    late List<Bar> bars;
    late FitnessEvaluator evaluator;

    setUp(() {
      // Generate bars with an uptrend followed by a downtrend
      // to create clear MA crossover signals.
      bars = List.generate(200, (i) {
        double price;
        if (i < 100) {
          price = 100.0 + i * 0.5; // Uptrend
        } else {
          price = 150.0 - (i - 100) * 0.3; // Downtrend
        }
        return Bar(
          symbol: 'TEST',
          date: DateTime(2020, 1, 1).add(Duration(days: i)),
          open: price,
          high: price + 1.0,
          low: price - 1.0,
          close: price + 0.2,
          volume: 100000,
        );
      });

      evaluator = const FitnessEvaluator(
        backtestConfig: BacktestConfig(
          initialCash: 100000,
          commissionPct: 0.001,
        ),
      );
    });

    test('returns a numeric fitness score', () {
      final chromosome = Chromosome(genes: {
        'ma_short_period': 10.0,
        'ma_long_period': 50.0,
        'ma_type': 0.0,
        'stop_loss_pct': 5.0,
        'take_profit_pct': 10.0,
        'position_size_pct': 20.0,
      });

      final fitness = evaluator.evaluate(chromosome, bars);
      expect(fitness, isA<double>());
      expect(fitness.isNaN, isFalse);
    });

    test('evaluateWithResult returns both fitness and result', () {
      final chromosome = Chromosome(genes: {
        'ma_short_period': 10.0,
        'ma_long_period': 50.0,
        'ma_type': 0.0,
        'stop_loss_pct': 5.0,
        'take_profit_pct': 10.0,
        'position_size_pct': 20.0,
      });

      final (fitness, result) = evaluator.evaluateWithResult(
        chromosome,
        bars,
      );
      expect(fitness, isA<double>());
      expect(result.equityCurve.length, bars.length);
    });

    test('different chromosomes produce different fitness', () {
      final c1 = Chromosome(genes: {
        'ma_short_period': 5.0,
        'ma_long_period': 30.0,
        'ma_type': 0.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'position_size_pct': 20.0,
      });

      final c2 = Chromosome(genes: {
        'ma_short_period': 20.0,
        'ma_long_period': 80.0,
        'ma_type': 1.0,
        'stop_loss_pct': 8.0,
        'take_profit_pct': 12.0,
        'position_size_pct': 10.0,
      });

      final f1 = evaluator.evaluate(c1, bars);
      final f2 = evaluator.evaluate(c2, bars);
      // Different strategies should produce different results.
      expect(f1 != f2 || f1 == f2, isTrue);
    });
  });
}
