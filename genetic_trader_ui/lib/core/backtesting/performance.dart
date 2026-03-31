import 'dart:math';

import '../models/trade.dart';

/// Performance metric calculations.
class Performance {
  Performance._();

  /// Annualized Sharpe Ratio from daily returns.
  static double sharpeRatio(
    List<double> returns, {
    double riskFreeRate = 0.0,
  }) {
    if (returns.isEmpty) return 0.0;

    final mean = returns.reduce((a, b) => a + b) / returns.length;
    final excessMean = mean - riskFreeRate / 252;

    if (returns.length < 2) return 0.0;

    var sumSq = 0.0;
    for (final r in returns) {
      final diff = r - mean;
      sumSq += diff * diff;
    }
    final stdDev = sqrt(sumSq / (returns.length - 1));

    if (stdDev == 0) return 0.0;
    final sharpe = (excessMean / stdDev) * sqrt(252.0);
    // Clamp to reasonable bounds to prevent blow-up when stdDev ≈ 0.
    return sharpe.clamp(-100.0, 100.0);
  }

  /// Maximum drawdown from an equity curve.
  static double maxDrawdown(List<double> equityCurve) {
    if (equityCurve.length < 2) return 0.0;

    var peak = equityCurve.first;
    var maxDd = 0.0;

    for (final value in equityCurve) {
      if (value > peak) peak = value;
      final dd = (peak - value) / peak;
      if (dd > maxDd) maxDd = dd;
    }

    return maxDd;
  }

  /// Compound Annual Growth Rate.
  static double cagr(
    double startValue,
    double endValue,
    int tradingDays,
  ) {
    if (startValue <= 0 || tradingDays <= 0) return 0.0;
    final years = tradingDays / 252.0;
    return pow(endValue / startValue, 1.0 / years).toDouble() - 1.0;
  }

  /// Win rate from a list of trades.
  static double winRate(List<Trade> trades) {
    if (trades.isEmpty) return 0.0;
    final wins = trades.where((t) => t.isWin).length;
    return wins / trades.length;
  }
}
