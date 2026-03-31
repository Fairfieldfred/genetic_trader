import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/models/backtest_result.dart';

void main() {
  group('BacktestResult', () {
    test('creates with all fields', () {
      final result = BacktestResult(
        totalReturn: 0.15,
        sharpeRatio: 1.2,
        maxDrawdown: 0.10,
        winRate: 0.55,
        numTrades: 20,
        trades: [],
        equityCurve: [100000.0, 105000.0, 110000.0],
      );
      expect(result.totalReturn, 0.15);
      expect(result.sharpeRatio, 1.2);
      expect(result.numTrades, 20);
    });
  });
}
