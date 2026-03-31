/// A completed trade record with entry/exit details and P&L.
class Trade {
  final String symbol;
  final DateTime entryDate;
  final DateTime exitDate;
  final double entryPrice;
  final double exitPrice;
  final double shares;
  final double pnl;
  final double pnlPct;

  const Trade({
    required this.symbol,
    required this.entryDate,
    required this.exitDate,
    required this.entryPrice,
    required this.exitPrice,
    required this.shares,
    required this.pnl,
    required this.pnlPct,
  });

  bool get isWin => pnl > 0;
}
