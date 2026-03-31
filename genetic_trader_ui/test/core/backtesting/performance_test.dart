import 'package:genetic_trader_ui/core/backtesting/performance.dart';
import 'package:genetic_trader_ui/core/models/trade.dart';
import 'package:test/test.dart';

void main() {
  group('Performance', () {
    group('sharpeRatio', () {
      test('returns 0 for empty returns', () {
        expect(Performance.sharpeRatio([]), 0.0);
      });

      test('returns 0 for constant returns (zero std dev)', () {
        expect(
          Performance.sharpeRatio([0.01, 0.01, 0.01]),
          0.0,
        );
      });

      test('positive for consistently positive returns', () {
        final returns = List.generate(
          252,
          (i) => 0.001 + (i % 3) * 0.0005,
        );
        expect(Performance.sharpeRatio(returns), greaterThan(0.0));
      });
    });

    group('maxDrawdown', () {
      test('returns 0 for monotonically increasing curve', () {
        expect(
          Performance.maxDrawdown([100, 110, 120, 130]),
          0.0,
        );
      });

      test('calculates correct drawdown', () {
        // Peak at 200, drops to 150 = 25% drawdown.
        final curve = [100.0, 150.0, 200.0, 150.0, 180.0];
        expect(
          Performance.maxDrawdown(curve),
          closeTo(0.25, 0.001),
        );
      });

      test('returns 0 for single value', () {
        expect(Performance.maxDrawdown([100]), 0.0);
      });
    });

    group('cagr', () {
      test('calculates annual growth rate', () {
        // Double in 252 days = 100% CAGR.
        final result = Performance.cagr(100000, 200000, 252);
        expect(result, closeTo(1.0, 0.01));
      });

      test('returns 0 for zero start', () {
        expect(Performance.cagr(0, 100, 252), 0.0);
      });
    });

    group('winRate', () {
      test('returns 0 for empty trades', () {
        expect(Performance.winRate([]), 0.0);
      });

      test('calculates correct win rate', () {
        final trades = [
          Trade(
            symbol: 'A',
            entryDate: DateTime(2023),
            exitDate: DateTime(2023, 2),
            entryPrice: 100,
            exitPrice: 110,
            shares: 1,
            pnl: 10,
            pnlPct: 10,
          ),
          Trade(
            symbol: 'B',
            entryDate: DateTime(2023),
            exitDate: DateTime(2023, 2),
            entryPrice: 100,
            exitPrice: 90,
            shares: 1,
            pnl: -10,
            pnlPct: -10,
          ),
          Trade(
            symbol: 'C',
            entryDate: DateTime(2023),
            exitDate: DateTime(2023, 2),
            entryPrice: 100,
            exitPrice: 105,
            shares: 1,
            pnl: 5,
            pnlPct: 5,
          ),
        ];
        expect(Performance.winRate(trades), closeTo(0.6667, 0.01));
      });
    });
  });
}
