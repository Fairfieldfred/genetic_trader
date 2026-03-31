import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/models/portfolio_state.dart';

void main() {
  group('PortfolioState', () {
    test('cash only portfolio', () {
      final state = PortfolioState(cash: 100000.0);
      expect(state.totalValue({}), 100000.0);
      expect(state.positions, isEmpty);
    });

    test('totalValue includes position values', () {
      final state = PortfolioState(
        cash: 50000.0,
        positions: {
          'AAPL': PositionInfo(shares: 100.0, avgPrice: 150.0),
          'MSFT': PositionInfo(shares: 50.0, avgPrice: 300.0),
        },
      );
      final prices = {'AAPL': 160.0, 'MSFT': 310.0};
      // 50000 + 100*160 + 50*310 = 50000 + 16000 + 15500 = 81500
      expect(state.totalValue(prices), 81500.0);
    });

    test('copyWith replaces cash', () {
      final state = PortfolioState(cash: 100000.0);
      final updated = state.copyWith(cash: 50000.0);
      expect(updated.cash, 50000.0);
    });
  });
}
