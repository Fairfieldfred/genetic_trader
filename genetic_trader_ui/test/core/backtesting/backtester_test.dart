import 'package:genetic_trader_ui/core/backtesting/backtester.dart';
import 'package:genetic_trader_ui/core/models/bar.dart';
import 'package:test/test.dart';

void main() {
  /// Generate deterministic test bars.
  List<Bar> generateBars({
    int count = 100,
    double startPrice = 100.0,
    double dailyChange = 0.5,
  }) {
    return List.generate(count, (i) {
      final price = startPrice + i * dailyChange;
      return Bar(
        symbol: 'TEST',
        date: DateTime(2023, 1, 1).add(Duration(days: i)),
        open: price,
        high: price + 1.0,
        low: price - 1.0,
        close: price + 0.3,
        volume: 100000,
      );
    });
  }

  group('Backtester', () {
    test('returns empty result for empty bars', () {
      final result = Backtester.run(
        bars: [],
        strategy: (i, bar, state, orders) {},
      );
      expect(result.numTrades, 0);
      expect(result.equityCurve, isEmpty);
    });

    test('buy-and-hold strategy', () {
      final bars = generateBars(count: 50);
      final result = Backtester.run(
        bars: bars,
        strategy: (i, bar, state, orders) {
          if (i == 0 && state.positions.isEmpty) {
            orders.add(MarketOrder(
              symbol: 'TEST',
              side: OrderSide.buy,
              shares: 100,
            ));
          }
        },
        config: const BacktestConfig(
          initialCash: 100000.0,
          commissionPct: 0.0,
        ),
      );
      expect(result.equityCurve.length, 50);
      expect(result.equityCurve.last, greaterThan(100000.0));
      expect(result.totalReturn, greaterThan(0.0));
    });

    test('completes a round-trip trade', () {
      final bars = generateBars(count: 20);
      final result = Backtester.run(
        bars: bars,
        strategy: (i, bar, state, orders) {
          if (i == 0 && state.positions.isEmpty) {
            orders.add(MarketOrder(
              symbol: 'TEST',
              side: OrderSide.buy,
              shares: 10,
            ));
          }
          if (i == 10 && state.positions.containsKey('TEST')) {
            orders.add(MarketOrder(
              symbol: 'TEST',
              side: OrderSide.sell,
              shares: 10,
            ));
          }
        },
        config: const BacktestConfig(commissionPct: 0.0),
      );
      expect(result.numTrades, 1);
      expect(result.trades.first.symbol, 'TEST');
      expect(result.trades.first.pnl, greaterThan(0));
    });

    test('commission reduces returns', () {
      final bars = generateBars(count: 20);

      final noCommission = Backtester.run(
        bars: bars,
        strategy: (i, bar, state, orders) {
          if (i == 0) {
            orders.add(MarketOrder(
              symbol: 'TEST',
              side: OrderSide.buy,
              shares: 100,
            ));
          }
          if (i == 15) {
            orders.add(MarketOrder(
              symbol: 'TEST',
              side: OrderSide.sell,
              shares: 100,
            ));
          }
        },
        config: const BacktestConfig(commissionPct: 0.0),
      );

      final withCommission = Backtester.run(
        bars: bars,
        strategy: (i, bar, state, orders) {
          if (i == 0) {
            orders.add(MarketOrder(
              symbol: 'TEST',
              side: OrderSide.buy,
              shares: 100,
            ));
          }
          if (i == 15) {
            orders.add(MarketOrder(
              symbol: 'TEST',
              side: OrderSide.sell,
              shares: 100,
            ));
          }
        },
        config: const BacktestConfig(commissionPct: 0.01),
      );

      expect(
        withCommission.equityCurve.last,
        lessThan(noCommission.equityCurve.last),
      );
    });
  });
}
