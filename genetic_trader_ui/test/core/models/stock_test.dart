import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/models/stock.dart';

void main() {
  group('Stock', () {
    test('creates with required symbol', () {
      final stock = Stock(symbol: 'AAPL');
      expect(stock.symbol, 'AAPL');
      expect(stock.name, isNull);
      expect(stock.indexMembership, isEmpty);
    });

    test('creates with all fields', () {
      final stock = Stock(
        symbol: 'AAPL',
        name: 'Apple Inc.',
        sector: 'Technology',
        indexMembership: ['SP500', 'NASDAQ100'],
      );
      expect(stock.name, 'Apple Inc.');
      expect(stock.indexMembership, hasLength(2));
    });

    test('copyWith replaces fields', () {
      final stock = Stock(symbol: 'AAPL', name: 'Apple');
      final updated = stock.copyWith(name: 'Apple Inc.');
      expect(updated.name, 'Apple Inc.');
      expect(updated.symbol, 'AAPL');
    });
  });
}
