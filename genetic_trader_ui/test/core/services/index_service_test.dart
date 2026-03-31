import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/services/index_service.dart';

void main() {
  group('IndexService', () {
    test('DJIA has 30 symbols', () {
      final symbols = IndexService.getSymbols(IndexType.djia);
      expect(symbols.length, 30);
      expect(symbols, contains('AAPL'));
      expect(symbols, contains('MSFT'));
    });

    test('SP500 has 503 symbols', () {
      final symbols = IndexService.getSymbols(IndexType.sp500);
      expect(symbols.length, 503);
      expect(symbols, contains('AAPL'));
    });

    test('Nasdaq100 has 100 symbols', () {
      final symbols = IndexService.getSymbols(IndexType.nasdaq100);
      expect(symbols.length, 100);
      expect(symbols, contains('AAPL'));
      expect(symbols, contains('NVDA'));
    });

    test('symbols are unique within each index', () {
      for (final indexType in IndexType.values) {
        final symbols = IndexService.getSymbols(indexType);
        expect(symbols.toSet().length, symbols.length,
            reason: '${indexType.name} has duplicates');
      }
    });

    test('getDisplayName returns readable names', () {
      expect(IndexService.getDisplayName(IndexType.djia), 'DJIA (30)');
      expect(IndexService.getDisplayName(IndexType.sp500), 'S&P 500 (503)');
      expect(IndexService.getDisplayName(IndexType.nasdaq100),
          'Nasdaq-100 (100)');
    });
  });
}
