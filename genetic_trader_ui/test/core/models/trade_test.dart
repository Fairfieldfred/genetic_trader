import 'package:test/test.dart';
import 'package:genetic_trader_ui/core/models/trade.dart';

void main() {
  group('Trade', () {
    test('winning trade has positive pnl', () {
      final trade = Trade(
        symbol: 'AAPL',
        entryDate: DateTime(2023, 1, 1),
        exitDate: DateTime(2023, 2, 1),
        entryPrice: 100.0,
        exitPrice: 110.0,
        shares: 10.0,
        pnl: 100.0,
        pnlPct: 10.0,
      );
      expect(trade.isWin, isTrue);
      expect(trade.pnl, 100.0);
    });

    test('losing trade has negative pnl', () {
      final trade = Trade(
        symbol: 'AAPL',
        entryDate: DateTime(2023, 1, 1),
        exitDate: DateTime(2023, 2, 1),
        entryPrice: 100.0,
        exitPrice: 90.0,
        shares: 10.0,
        pnl: -100.0,
        pnlPct: -10.0,
      );
      expect(trade.isWin, isFalse);
    });
  });
}
