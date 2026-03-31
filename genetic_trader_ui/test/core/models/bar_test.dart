import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/models/bar.dart';

void main() {
  group('Bar', () {
    test('creates with required fields', () {
      final bar = Bar(
        symbol: 'AAPL',
        date: DateTime(2023, 1, 1),
        open: 100.0,
        high: 105.0,
        low: 99.0,
        close: 103.0,
        volume: 1000000,
      );
      expect(bar.symbol, 'AAPL');
      expect(bar.close, 103.0);
      expect(bar.adjClose, isNull);
    });

    test('copyWith replaces fields', () {
      final bar = Bar(
        symbol: 'AAPL',
        date: DateTime(2023, 1, 1),
        open: 100.0,
        high: 105.0,
        low: 99.0,
        close: 103.0,
        volume: 1000000,
      );
      final updated = bar.copyWith(close: 110.0, adjClose: 109.5);
      expect(updated.close, 110.0);
      expect(updated.adjClose, 109.5);
      expect(updated.symbol, 'AAPL');
    });

    test('toString contains symbol and prices', () {
      final bar = Bar(
        symbol: 'MSFT',
        date: DateTime(2023, 6, 15),
        open: 300.0,
        high: 310.0,
        low: 295.0,
        close: 305.0,
        volume: 500000,
      );
      expect(bar.toString(), contains('MSFT'));
      expect(bar.toString(), contains('305.0'));
    });
  });
}
