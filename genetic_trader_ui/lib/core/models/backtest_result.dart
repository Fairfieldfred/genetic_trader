import 'trade.dart';

/// Results of a backtest run.
class BacktestResult {
  final double totalReturn;
  final double sharpeRatio;
  final double maxDrawdown;
  final double winRate;
  final int numTrades;
  final List<Trade> trades;
  final List<double> equityCurve;

  const BacktestResult({
    required this.totalReturn,
    required this.sharpeRatio,
    required this.maxDrawdown,
    required this.winRate,
    required this.numTrades,
    required this.trades,
    required this.equityCurve,
  });
}
